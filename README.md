# 🧬 Synapse Mapper

**Transform biomedical PDFs into interactive knowledge graphs**

Synapse Mapper is a sophisticated research intelligence tool designed for hackathons and real-world research. It ingests biomedical PDF documents and automatically generates an interactive, force-directed knowledge graph that reveals hidden connections between genes, chemicals, diseases, and more.

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.9+-green.svg)
![React](https://img.shields.io/badge/react-18.2-blue.svg)

## ✨ Features

### 🎯 Core Capabilities
- **Automated PDF Processing** - Extract and analyze text from multiple biomedical PDFs
- **Named Entity Recognition** - scispaCy-powered identification of biomedical entities
- **Relationship Extraction** - Pattern-based and co-occurrence analysis
- **Interactive Visualization** - 2D/3D force-directed graphs with smooth physics
- **Advanced Analytics** - Community detection, centrality analysis, graph statistics

### 🚀 Advanced Features
- **LLM Enhancement** (Optional) - Semantic relationship understanding via OpenAI/Anthropic
- **Smart Filtering** - Filter by entity type, connection count, or search
- **Focus Mode** - Click nodes to highlight neighborhoods and explore connections
- **Real-time Processing** - Live progress tracking with background job processing
- **Export System** - Export as JSON, CSV, or PNG image
- **Persistent Storage** - Save and load projects with SQLite/PostgreSQL

### 🎨 Beautiful UI
- Modern gradient design with dark theme
- Responsive layout for all screen sizes
- Smooth animations and transitions
- Interactive tooltips with evidence sentences
- Entity color-coding by type

## 🏗️ Architecture

```
┌─────────────────┐         ┌──────────────────┐
│   React + Vite  │  HTTP   │   FastAPI       │
│   TypeScript    │ ────▶   │   Python 3.9+   │
│   Tailwind CSS  │         │                  │
└─────────────────┘         └──────────────────┘
        │                            │
        │                            ▼
        │                   ┌──────────────────┐
        │                   │   NLP Pipeline   │
        │                   │  - PyMuPDF       │
        │                   │  - scispaCy      │
        │                   │  - NetworkX      │
        │                   └──────────────────┘
        │                            │
        ▼                            ▼
┌─────────────────┐         ┌──────────────────┐
│  Force Graph    │         │   Graph Builder  │
│  - 2D/3D Views  │ ◀────   │  - Communities   │
│  - Interactions │  JSON   │  - Centrality    │
└─────────────────┘         └──────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- **Python 3.9+**
- **Node.js 18+**
- **npm or yarn**

### 1. Clone Repository
```bash
git clone <your-repo-url>
cd calhacks
```

### 2. Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download scispaCy model (this may take a few minutes)
pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_lg-0.5.4.tar.gz

# Optional: Configure environment variables
cp .env.example .env
# Edit .env to add LLM API keys if desired

# Run backend server
python -m app.main
```

Backend runs on `http://localhost:8000`

### 3. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

Frontend runs on `http://localhost:5173`

### 4. Open Browser
Navigate to `http://localhost:5173` and start uploading PDFs!

## 📖 Usage

### Basic Workflow
1. **Upload PDFs** - Drag & drop biomedical PDF files
2. **Wait for Processing** - Monitor real-time progress (NER, relationship extraction, graph building)
3. **Explore Graph** - Pan, zoom, click nodes to investigate
4. **Apply Filters** - Use sidebar to focus on specific entities or search
5. **View Analytics** - Get insights with community detection and centrality analysis
6. **Export Results** - Download as JSON, CSV, or image

### Advanced Features

#### LLM-Powered Extraction
Enable semantic relationship classification by:
1. Add OpenAI or Anthropic API key to backend `.env`
2. Set `ENABLE_LLM_EXTRACTION=true` in `.env`
3. Check "Enable AI-Powered Extraction" when uploading

#### Graph Filtering
- **Entity Types**: Toggle specific biomedical entities
- **Min Degree**: Show only highly connected nodes
- **Search**: Find entities by name
- **Top-N**: Display most important nodes

#### View Modes
- **2D View**: High performance, ideal for large graphs
- **3D View**: Impressive visualization, better for presentations
- **Labels Toggle**: Show/hide node labels

## 🛠️ Tech Stack

### Backend
- **FastAPI** - Modern async API framework
- **PyMuPDF** - High-performance PDF processing
- **scispaCy** - Biomedical NER (en_core_sci_lg model)
- **NetworkX** - Graph algorithms and analysis
- **python-louvain** - Community detection
- **SQLAlchemy** - Database ORM
- **OpenAI/Anthropic** (Optional) - LLM enhancement

### Frontend
- **React 18** - UI library with hooks
- **TypeScript** - Type safety
- **Vite** - Lightning-fast build tool
- **Tailwind CSS** - Utility-first styling
- **react-force-graph** - WebGL-powered graph rendering
- **Recharts** - Analytics visualizations
- **Zustand** - Lightweight state management
- **Axios** - HTTP client

## 📊 API Endpoints

### `POST /api/process`
Upload PDFs and generate knowledge graph

**Request:**
- `files`: PDF files (multipart/form-data)
- `project_name`: Optional project name
- `enable_llm`: Enable LLM extraction (boolean)

**Response:**
```json
{
  "job_id": "uuid",
  "status": "processing",
  "progress": 0.5,
  "message": "Extracting entities...",
  "result": null
}
```

### `GET /api/status/{job_id}`
Check processing status and retrieve results

### `POST /api/graph/filter`
Filter graph by degree, entity types, or top-N

### `POST /api/analytics`
Compute graph analytics (centrality, communities, etc.)

### `GET /api/projects`
List all saved projects

## 🎯 Use Cases

### Research Applications
- **Literature Review** - Discover connections across multiple papers
- **Hypothesis Generation** - Find unexpected relationships
- **Drug Discovery** - Identify drug-disease-gene interactions
- **Biomarker Discovery** - Explore disease-protein associations

### Hackathon Tips
- **Demo Impact** - 3D visualization is visually impressive for judges
- **Sample Data** - Prepare biomedical PDFs beforehand
- **Performance** - Start with 2-5 PDFs for demos
- **Analytics** - Showcase community detection and centrality
- **Export** - Show data portability with exports

## 🧪 Development

### Backend Development
```bash
cd backend
source venv/bin/activate

# Run with auto-reload
python -m app.main

# Or use uvicorn directly
uvicorn app.main:app --reload
```

### Frontend Development
```bash
cd frontend

# Dev server with hot reload
npm run dev

# Type checking
npm run build

# Linting
npm run lint
```

### Project Structure
```
calhacks/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── config.py            # Configuration
│   │   ├── models/              # Data models
│   │   │   ├── schemas.py       # Pydantic models
│   │   │   └── database.py      # SQLAlchemy models
│   │   └── services/            # Business logic
│   │       ├── pdf_processor.py
│   │       ├── ner_service.py
│   │       ├── relationship_extractor.py
│   │       ├── graph_builder.py
│   │       └── llm_service.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/          # React components
│   │   ├── services/            # API client
│   │   ├── store/               # State management
│   │   ├── types/               # TypeScript types
│   │   └── App.tsx
│   └── package.json
└── README.md
```

## 🐛 Troubleshooting

### Backend Issues

**scispaCy model not found:**
```bash
pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_lg-0.5.4.tar.gz
```

**CORS errors:**
- Check `CORS_ORIGINS` in backend `.env`
- Ensure frontend URL is in allowed origins

**Slow processing:**
- Start with smaller PDFs
- Disable LLM extraction for faster processing
- Check system resources

### Frontend Issues

**Blank graph:**
- Check browser console for errors
- Verify backend is running and accessible
- Check API URL in frontend `.env`

**Performance issues:**
- Use 2D view for large graphs
- Apply filters to reduce node count
- Disable node labels when zoomed out

## 🚀 Deployment

### Backend (Docker)
```dockerfile
FROM python:3.9
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt
COPY backend/ .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Frontend (Vercel/Netlify)
```bash
cd frontend
npm run build
# Deploy dist/ folder
```

## 🤝 Contributing

This is a hackathon project, but contributions are welcome!

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License - feel free to use this project for your hackathon or research!

## 🙏 Acknowledgments

- **scispaCy** - Biomedical NLP models
- **NetworkX** - Graph algorithms
- **react-force-graph** - Graph visualization
- **FastAPI** - API framework

## 📧 Contact

Built for CalHacks 2025 🐻

---

**Happy Mapping! 🧬**

