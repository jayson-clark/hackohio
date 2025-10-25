# LLM Chat Intelligence

## How Smart is the Chat?

The chatbot uses **GPT-4 through Lava** for complex queries, with a sophisticated understanding of your graph structure.

### What the LLM Sees

```python
System Prompt:
"You are a biomedical knowledge graph assistant. 
You help users explore relationships between biomedical entities.

Available Graph Tools:
1. get_neighbors(entity, depth) - Find neighboring entities
2. shortest_path(source, target) - Find paths between entities (Dijkstra's algorithm)
3. common_connections(entities) - Find shared connections
4. subgraph(entities, depth) - Extract a subgraph

Current Graph: 82 nodes, 216 edges"

Sample Entities: ['NSCLC', 'Macrophage', 'Lung cancer', 'tobacco', 'patients', ...]

Conversation History: [last 5 messages for context]

User Question: "How are NSCLC and lung cancer related?"
```

### LLM Response Format

The LLM decides which tool to use and returns JSON:

```json
{
  "tool": "shortest_path",
  "params": {"source": "NSCLC", "target": "lung cancer"},
  "entities": ["NSCLC", "lung cancer"],
  "explanation": "I'll find the shortest path between NSCLC and lung cancer."
}
```

Or for general questions:

```json
{
  "tool": null,
  "response": "NSCLC stands for Non-Small Cell Lung Cancer, which is a type of lung cancer..."
}
```

## Query Handling Strategy

### ✅ Pattern Matching (Fast, Free)
These queries are handled **instantly without LLM**:
- "What are the neighbors of X?"
- "Find path between A and B"
- "What connects X, Y, Z?"
- "How many nodes are there?"

### 🤖 LLM (Smart, Costs $)
Only used for complex queries like:
- "How are these related?"
- "What can you tell me about cancer?"
- "Explain the relationship between..."
- Ambiguous or conversational questions

## Example Queries

### Simple (Pattern Matching)
```
User: "neighbors of NSCLC"
→ Pattern match → Instant response
```

### Complex (LLM)
```
User: "How does tobacco relate to cancer?"
→ LLM extracts entities → Uses shortest_path tool → Response
```

### General Knowledge
```
User: "What is NSCLC?"
→ LLM provides general explanation (no tool needed)
```

## Conversation Memory

The LLM remembers the **last 5 messages** for context:
```
User: "What are neighbors of NSCLC?"
Bot: "NSCLC neighbors: lung cancer, tobacco, ..."

User: "How is it related to the second one?"
→ LLM knows "second one" = "tobacco" from history
```

## Cost Optimization

- ✅ **90% of queries use pattern matching** (free)
- 🤖 **10% complex queries use GPT-4** (~$0.01 per query)
- All LLM calls are tracked through Lava for billing

## Making it Smarter

To improve the LLM:
1. Add more sample entities in the prompt (currently 10-20)
2. Include entity types/metadata
3. Add graph statistics (centrality, communities)
4. Fine-tune prompts for specific biomedical queries

Current prompt is **general purpose** and works well for most graph exploration tasks!

