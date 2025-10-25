from typing import List, Dict, Any, Tuple
import networkx as nx


class GraphConversationalAgent:
    """
    Conversational agent to reason over a biomedical knowledge graph.
    Provides tool-like methods for querying the graph that can be orchestrated
    by an external LLM service.
    """

    def __init__(self, nx_graph: nx.Graph):
        self.graph = nx_graph

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


