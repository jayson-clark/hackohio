from typing import List, Dict, Any, Tuple, Optional
import networkx as nx
import json


class GraphConversationalAgent:
    """
    Conversational agent to reason over a biomedical knowledge graph.
    Provides tool-like methods for querying the graph that can be orchestrated
    by an external LLM service.
    """

    def __init__(self, nx_graph: nx.Graph, llm_service=None):
        self.graph = nx_graph
        self.llm_service = llm_service
        self.conversation_history = []

    def get_neighbors(self, entity: str, depth: int = 1) -> Dict[str, Any]:
        if entity not in self.graph:
            return {"entity": entity, "neighbors": []}
        visited = {entity}
        frontier = {entity}
        layers = []
        for _ in range(max(1, depth)):
            next_frontier = set()
            layer = []
            for node in frontier:
                for neighbor in self.graph.neighbors(node):
                    if neighbor in visited:
                        continue
                    visited.add(neighbor)
                    next_frontier.add(neighbor)
                    edge = self.graph.edges[node, neighbor]
                    layer.append({
                        "source": node,
                        "target": neighbor,
                        "weight": edge.get("weight", 1.0),
                        "relationship_type": edge.get("relationship_type", "CO_OCCURRENCE"),
                        "evidence": edge.get("evidence", [])[:3],
                    })
            layers.append(layer)
            frontier = next_frontier
            if not frontier:
                break
        return {"entity": entity, "layers": layers}

    def shortest_path(self, source: str, target: str, k_paths: int = 1) -> Dict[str, Any]:
        if source not in self.graph or target not in self.graph:
            return {"paths": []}
        try:
            # Use simple shortest paths by hop count
            paths = list(nx.all_shortest_paths(self.graph, source=source, target=target))
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return {"paths": []}
        paths = paths[: max(1, k_paths)]
        detailed = []
        for path in paths:
            edges = []
            for a, b in zip(path, path[1:]):
                data = self.graph.edges[a, b]
                edges.append({
                    "source": a,
                    "target": b,
                    "weight": data.get("weight", 1.0),
                    "relationship_type": data.get("relationship_type", "CO_OCCURRENCE"),
                    "evidence": data.get("evidence", [])[:3],
                })
            detailed.append({"nodes": path, "edges": edges})
        return {"paths": detailed}

    def common_connections(self, entities: List[str], min_degree: int = 1) -> Dict[str, Any]:
        present = [e for e in entities if e in self.graph]
        if len(present) < 2:
            return {"common": []}
        neighbor_sets = [set(self.graph.neighbors(e)) for e in present]
        common = set.intersection(*neighbor_sets) if neighbor_sets else set()
        result = []
        for n in common:
            deg = self.graph.degree(n)
            if deg >= min_degree:
                result.append({"entity": n, "degree": deg})
        result.sort(key=lambda x: x["degree"], reverse=True)
        return {"common": result}

    def subgraph(self, center_entities: List[str], depth: int = 1) -> Dict[str, Any]:
        nodes_to_include = set(center_entities)
        for e in center_entities:
            if e not in self.graph:
                continue
            for _ in range(depth):
                neighbors = set()
                for n in nodes_to_include.copy():
                    if n in self.graph:
                        neighbors.update(self.graph.neighbors(n))
                nodes_to_include.update(neighbors)
        sg = self.graph.subgraph(nodes_to_include).copy()
        nodes = list(sg.nodes())
        edges = [[u, v] for u, v in sg.edges()]
        return {"nodes": nodes, "edges": edges}
    
    async def chat(self, user_message: str, conversation_history: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        LLM-powered conversational interface for graph queries
        Uses tool calling to interact with the graph intelligently
        """
        if not self.llm_service or not self.llm_service.enabled:
            # Fallback to pattern matching if LLM not available
            return self._pattern_match_chat(user_message)
        
        # Prepare graph context
        graph_stats = {
            "num_nodes": self.graph.number_of_nodes(),
            "num_edges": self.graph.number_of_edges(),
            "sample_entities": list(self.graph.nodes())[:20]
        }
        
        # Build system prompt with available tools
        system_prompt = f"""You are a biomedical knowledge graph assistant. You help users explore relationships between biomedical entities.

Available Graph Tools:
1. get_neighbors(entity, depth) - Find neighboring entities
2. shortest_path(source, target) - Find paths between entities
3. common_connections(entities) - Find shared connections
4. subgraph(entities, depth) - Extract a subgraph

Current Graph: {graph_stats['num_nodes']} nodes, {graph_stats['num_edges']} edges

When a user asks about the graph, determine which tool(s) to use and extract the relevant entity names from their question. Match entity names to those in the graph (case-insensitive).

Respond in JSON format:
{{
  "tool": "tool_name",
  "params": {{"param": "value"}},
  "entities": ["entity1", "entity2"],
  "explanation": "Natural language explanation of what you'll do"
}}

If no tool is needed, return:
{{
  "tool": null,
  "response": "Your direct answer"
}}"""

        # Prepare messages
        messages = [
            {"role": "system", "content": system_prompt},
        ]
        
        # Add conversation history if provided
        if conversation_history:
            for msg in conversation_history[-5:]:  # Last 5 messages for context
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })
        
        messages.append({
            "role": "user",
            "content": f"Graph sample entities: {', '.join(graph_stats['sample_entities'][:10])}...\n\nUser question: {user_message}"
        })
        
        try:
            # Call LLM through Lava
            if self.llm_service.use_lava:
                response = await self.llm_service.lava_service.forward_openai_request(
                    messages=messages,
                    model="gpt-4-turbo-preview",
                    temperature=0.3,
                    response_format={"type": "json_object"},
                    metadata={
                        "service": "synapse_mapper",
                        "task": "graph_chat"
                    }
                )
                content = response['data']['choices'][0]['message']['content']
            elif self.llm_service.openai_client:
                import asyncio
                response = await asyncio.to_thread(
                    self.llm_service.openai_client.chat.completions.create,
                    model="gpt-4-turbo-preview",
                    messages=messages,
                    temperature=0.3,
                    response_format={"type": "json_object"}
                )
                content = response.choices[0].message.content
            else:
                return self._pattern_match_chat(user_message)
            
            # Parse LLM response
            llm_result = json.loads(content)
            
            # If LLM wants to use a tool, execute it
            if llm_result.get("tool"):
                tool_name = llm_result["tool"]
                params = llm_result.get("params", {})
                
                # Match entities in the graph
                entities_to_match = llm_result.get("entities", [])
                matched_entities = self._match_entities(entities_to_match)
                
                # Execute the tool
                if tool_name == "get_neighbors":
                    entity = matched_entities[0] if matched_entities else params.get("entity", "")
                    result = self.get_neighbors(entity, depth=params.get("depth", 1))
                elif tool_name == "shortest_path":
                    source = matched_entities[0] if len(matched_entities) > 0 else params.get("source", "")
                    target = matched_entities[1] if len(matched_entities) > 1 else params.get("target", "")
                    result = self.shortest_path(source, target)
                elif tool_name == "common_connections":
                    entities = matched_entities if matched_entities else params.get("entities", [])
                    result = self.common_connections(entities)
                elif tool_name == "subgraph":
                    entities = matched_entities if matched_entities else params.get("entities", [])
                    result = self.subgraph(entities, depth=params.get("depth", 1))
                else:
                    result = {"error": "Unknown tool"}
                
                # Format result for user
                return self._format_tool_result(tool_name, result, llm_result.get("explanation", ""))
            else:
                # Direct response from LLM
                return {
                    "answer": llm_result.get("response", "I'm not sure how to help with that."),
                    "tool_calls": [],
                    "relevant_nodes": [],
                    "relevant_edges": [],
                    "citations": []
                }
                
        except Exception as e:
            print(f"LLM chat error: {e}")
            return self._pattern_match_chat(user_message)
    
    def _match_entities(self, query_entities: List[str]) -> List[str]:
        """Match query entities to actual graph nodes (case-insensitive)"""
        matched = []
        graph_nodes = list(self.graph.nodes())
        
        for query_entity in query_entities:
            query_lower = query_entity.lower().strip()
            
            # Exact match
            for node in graph_nodes:
                if node.lower() == query_lower:
                    matched.append(node)
                    break
            else:
                # Partial match
                for node in graph_nodes:
                    if query_lower in node.lower() or node.lower() in query_lower:
                        matched.append(node)
                        break
        
        return matched
    
    def _format_tool_result(self, tool_name: str, result: Dict, explanation: str) -> Dict[str, Any]:
        """Format tool execution result for chat response"""
        response = {
            "answer": explanation,
            "tool_calls": [tool_name],
            "relevant_nodes": [],
            "relevant_edges": [],
            "citations": []
        }
        
        if tool_name == "get_neighbors":
            layers = result.get("layers", [])
            if layers:
                neighbors = list({item["target"] for item in layers[0]})
                response["answer"] = f"{explanation}\n\nNeighbors: {', '.join(neighbors[:15])}"
                response["relevant_nodes"] = [result["entity"]] + neighbors
                response["relevant_edges"] = [[result["entity"], t] for t in neighbors]
                response["citations"] = [e for item in layers[0] for e in item.get("evidence", [])][:3]
        
        elif tool_name == "shortest_path":
            paths = result.get("paths", [])
            if paths:
                path = paths[0]
                nodes = path["nodes"]
                edges = path["edges"]
                response["answer"] = f"{explanation}\n\nPath: {' → '.join(nodes)}"
                response["relevant_nodes"] = nodes
                response["relevant_edges"] = [[e["source"], e["target"]] for e in edges]
                response["citations"] = [evi for e in edges for evi in e.get("evidence", [])][:3]
            else:
                response["answer"] = f"{explanation}\n\nNo path found."
        
        elif tool_name == "common_connections":
            commons = result.get("common", [])
            if commons:
                response["answer"] = f"{explanation}\n\nCommon: {', '.join([c['entity'] for c in commons[:15]])}"
                response["relevant_nodes"] = [c["entity"] for c in commons]
        
        return response
    
    def _pattern_match_chat(self, message: str) -> Dict[str, Any]:
        """Fallback pattern matching for basic queries"""
        text = message.lower().strip()
        
        # Basic patterns
        if "how many" in text and "nodes" in text:
            return {
                "answer": f"The graph has {self.graph.number_of_nodes()} nodes.",
                "tool_calls": [],
                "relevant_nodes": [],
                "relevant_edges": [],
                "citations": []
            }
        elif "how many" in text and "edges" in text:
            return {
                "answer": f"The graph has {self.graph.number_of_edges()} edges.",
                "tool_calls": [],
                "relevant_nodes": [],
                "relevant_edges": [],
                "citations": []
            }
        else:
            return {
                "answer": "I can help you explore the graph! Try asking:\n- 'What are the neighbors of X?'\n- 'Find path between A and B'\n- 'What connects A, B, and C?'",
                "tool_calls": [],
                "relevant_nodes": [],
                "relevant_edges": [],
                "citations": []
            }


