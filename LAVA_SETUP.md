# Lava Payments Integration Setup

## Overview

Synapse Mapper now integrates with [Lava Payments](https://www.lavapayments.com) for usage-based billing of LLM API calls. All LLM requests (OpenAI/Anthropic) can be automatically routed through Lava for metering and tracking.

## Features

- ✅ Automatic usage tracking for all LLM calls
- ✅ Usage-based billing through Lava
- ✅ Detailed request analytics and metadata
- ✅ Support for both OpenAI and Anthropic models
- ✅ Fallback to direct API calls when Lava is disabled

## Setup Instructions

### 1. Get Your Lava API Keys

1. Visit [Lava Payments Secrets](https://www.lavapayments.com/secrets)
2. Create a new secret key (starts with `aks_live_`)
3. Create a connection (you'll get a `connection_secret`)
4. (Optional) Create a product secret for specific product tracking

### 2. Configure Environment Variables

Edit your `backend/.env` file and add:

```bash
# Lava Payments Configuration
LAVA_SECRET_KEY=aks_live_m3wV8b44f9_BaljpU1ujJEj3Q5lReJRQBjcuS50ogLPu7OstaqAy1SP
LAVA_CONNECTION_SECRET=your_connection_secret_here
LAVA_PRODUCT_SECRET=your_product_secret_here  # Optional
ENABLE_LAVA=true

# Also enable LLM extraction if you want to use it
ENABLE_LLM_EXTRACTION=true

# And add your LLM API key
OPENAI_API_KEY=your_openai_key_here
# OR
ANTHROPIC_API_KEY=your_anthropic_key_here
```

### 3. Restart Backend

```bash
cd backend
source venv/bin/activate
python -m app.main
```

## API Endpoints

### Check Lava Status
```bash
GET /api/lava/status
```
Returns configuration status and whether Lava is enabled.

### Get Usage Statistics
```bash
GET /api/lava/usage
```
Returns usage statistics from Lava including costs and request counts.

### List Tracked Requests
```bash
GET /api/lava/requests?limit=50&cursor=req_xxx
```
Lists all API requests tracked by Lava with pagination.

## How It Works

1. **Request Flow**: When LLM extraction is enabled, all OpenAI/Anthropic API calls are automatically routed through Lava's forward endpoint
2. **Metadata Tracking**: Each request includes metadata:
   - `service`: "synapse_mapper"
   - `task`: "relationship_extraction" or "relationship_classification"
3. **Billing**: Lava automatically meters and bills based on actual LLM usage
4. **Fallback**: If Lava is disabled, calls go directly to OpenAI/Anthropic

## Tracked Operations

The following operations are metered when Lava is enabled:

### Relationship Extraction
- Model: `gpt-4-turbo-preview` or `claude-3-sonnet-20240229`
- Purpose: Extract semantic relationships from sentences
- Metadata: `{"service": "synapse_mapper", "task": "relationship_extraction"}`

### Relationship Classification
- Model: `gpt-3.5-turbo` or `claude-3-haiku-20240307`
- Purpose: Classify relationship types between entities
- Metadata: `{"service": "synapse_mapper", "task": "relationship_classification"}`

### Graph Chat (NEW! 🤖)
- Model: `gpt-4-turbo-preview`
- Purpose: Intelligent conversational interface for graph exploration
- Metadata: `{"service": "synapse_mapper", "task": "graph_chat"}`
- Features:
  - Natural language understanding of graph queries
  - Automatic entity matching and disambiguation
  - Tool selection (neighbors, paths, connections)
  - Context-aware responses with conversation history

## Testing

1. **Check Configuration**:
```bash
curl http://localhost:8000/api/lava/status
```

2. **Enable LLM Extraction** in your graph processing

3. **Process a PDF** - LLM calls will be routed through Lava

4. **Try the Chat**:
   - Open the chat panel in the UI
   - Ask natural language questions like:
     - "What connects NSCLC and lung cancer?"
     - "Show me neighbors of p53"
     - "Find the shortest path between inflammation and tumor"
   - All LLM calls are automatically tracked and billed through Lava!

5. **View Usage**:
```bash
curl http://localhost:8000/api/lava/usage
```

## Example Chat Queries

The intelligent chatbot understands natural language! Try these:

- **Exploration**: "What is NSCLC connected to?"
- **Path Finding**: "How are inflammation and cancer related?"
- **Common Links**: "What do p53, MDM2, and ATM have in common?"
- **Neighborhood**: "Show me everything around apoptosis"
- **General**: "How many nodes are in the graph?"

The LLM automatically:
- Extracts entity names from your query
- Matches them to graph nodes (fuzzy matching)
- Selects the right tool (neighbors, paths, etc.)
- Formats a natural response with highlights

## Disabling Lava

To use LLMs without Lava:
```bash
ENABLE_LAVA=false
```

Or remove the `LAVA_SECRET_KEY` from your `.env` file.

## Documentation

- [Lava API Reference](https://www.lavapayments.com/docs/api-reference/introduction)
- [Forward Endpoint](https://www.lavapayments.com/docs/api-reference/forward-endpoint)

## Support

For Lava-related issues:
- Email: support@lavapayments.com
- Website: https://www.lavapayments.com/contact

