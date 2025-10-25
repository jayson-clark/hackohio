# 📁 Project Structure

Complete file tree for Synapse Mapper

```
calhacks/
│
├── 📄 README.md                    # Main documentation
├── 📄 QUICKSTART.md               # 5-minute setup guide
├── 📄 DEMO_GUIDE.md               # Hackathon presentation guide
├── 📄 PROJECT_STRUCTURE.md        # This file
├── 📄 .gitignore                  # Git ignore rules
├── 🔧 setup.sh                    # Automated setup script
└── 🔧 run.sh                      # Run both servers with tmux
│
├── backend/                       # FastAPI Python Backend
│   ├── 📄 README.md              # Backend documentation
│   ├── 📄 requirements.txt        # Python dependencies
│   ├── 📄 .gitignore             # Backend git ignore
│   ├── 📁 uploads/               # Temporary PDF storage (gitignored)
│   │
│   └── app/                       # Main application package
│       ├── 📄 __init__.py
│       ├── 📄 main.py            # FastAPI app & endpoints
│       ├── 📄 config.py          # Configuration management
│       │
│       ├── models/                # Data models
│       │   ├── 📄 __init__.py
│       │   ├── 📄 schemas.py     # Pydantic models (API contracts)
│       │   └── 📄 database.py    # SQLAlchemy models (persistence)
│       │
│       └── services/              # Business logic
│           ├── 📄 __init__.py
│           ├── 📄 pdf_processor.py         # PDF text extraction
│           ├── 📄 ner_service.py           # Named Entity Recognition
│           ├── 📄 relationship_extractor.py # Relationship finding
│           ├── 📄 graph_builder.py         # Graph construction & analytics
│           └── 📄 llm_service.py           # LLM integration (optional)
│
└── frontend/                      # React TypeScript Frontend
    ├── 📄 README.md              # Frontend documentation
    ├── 📄 package.json           # Node dependencies
    ├── 📄 tsconfig.json          # TypeScript config
    ├── 📄 vite.config.ts         # Vite build config
    ├── 📄 tailwind.config.js     # Tailwind CSS config
    ├── 📄 postcss.config.js      # PostCSS config
    ├── 📄 .gitignore            # Frontend git ignore
    ├── 📄 index.html            # HTML entry point
    │
    └── src/                       # Source code
        ├── 📄 main.tsx           # React entry point
        ├── 📄 App.tsx            # Main app component
        ├── 📄 index.css          # Global styles
        │
        ├── components/            # React components
        │   ├── 📄 ForceGraph2DView.tsx    # 2D graph visualization
        │   ├── 📄 ForceGraph3DView.tsx    # 3D graph visualization
        │   ├── 📄 UploadPanel.tsx         # PDF upload interface
        │   ├── 📄 ProcessingOverlay.tsx   # Loading state
        │   ├── 📄 Sidebar.tsx             # Filters & controls
        │   ├── 📄 NodeDetails.tsx         # Selected node info panel
        │   ├── 📄 Analytics.tsx           # Analytics dashboard
        │   └── 📄 ExportMenu.tsx          # Export functionality
        │
        ├── services/              # API & utilities
        │   └── 📄 api.ts         # Backend API client
        │
        ├── store/                 # State management
        │   └── 📄 useStore.ts    # Zustand global store
        │
        └── types/                 # TypeScript definitions
            └── 📄 index.ts       # Type definitions & constants
```

## 🎯 Key Files Explained

### Backend Core Files

| File | Purpose |
|------|---------|
| `main.py` | FastAPI application, API endpoints, request handling |
| `config.py` | Environment variables, app configuration |
| `schemas.py` | API request/response models (Pydantic) |
| `database.py` | Database models for persistence (SQLAlchemy) |

### Backend Services (The Intelligence)

| Service | What It Does |
|---------|--------------|
| `pdf_processor.py` | Extracts text from PDFs using PyMuPDF |
| `ner_service.py` | Identifies biomedical entities (genes, chemicals, diseases) |
| `relationship_extractor.py` | Finds connections between entities |
| `graph_builder.py` | Builds NetworkX graph, runs analytics |
| `llm_service.py` | Optional LLM-powered semantic extraction |

### Frontend Core Files

| File | Purpose |
|------|---------|
| `App.tsx` | Main application component, routing logic |
| `useStore.ts` | Global state management (Zustand) |
| `api.ts` | API client for backend communication |
| `types/index.ts` | TypeScript types, color mappings |

### Frontend Components (The UI)

| Component | What It Does |
|-----------|--------------|
| `ForceGraph2DView.tsx` | 2D force-directed graph with WebGL |
| `ForceGraph3DView.tsx` | 3D graph visualization |
| `UploadPanel.tsx` | Drag-and-drop PDF upload |
| `Sidebar.tsx` | Filters, search, view controls |
| `NodeDetails.tsx` | Selected node information panel |
| `Analytics.tsx` | Statistics, charts, communities |
| `ExportMenu.tsx` | JSON/CSV/PNG export |
| `ProcessingOverlay.tsx` | Loading state with progress |

## 🔄 Data Flow

```
1. PDF Upload (Frontend)
   ↓
2. FastAPI Endpoint (main.py)
   ↓
3. Background Job Created
   ↓
4. PDF Processing Pipeline:
   ├─ pdf_processor.py     → Extract text
   ├─ ner_service.py       → Find entities
   ├─ relationship_extractor.py → Find connections
   └─ graph_builder.py     → Build graph + analytics
   ↓
5. Return Graph JSON
   ↓
6. Frontend Visualization (ForceGraph2DView/3DView)
   ↓
7. User Interaction (Sidebar filters, node clicks)
```

## 📊 Technology Mapping

### Backend Technologies
```
FastAPI          → main.py (API framework)
PyMuPDF          → pdf_processor.py (PDF reading)
scispaCy         → ner_service.py (NER)
NetworkX         → graph_builder.py (graph algorithms)
python-louvain   → graph_builder.py (community detection)
SQLAlchemy       → database.py (persistence)
OpenAI/Anthropic → llm_service.py (optional LLM)
```

### Frontend Technologies
```
React            → All .tsx components
TypeScript       → Type safety across project
Vite             → vite.config.ts (build tool)
Tailwind CSS     → index.css + inline classes
react-force-graph → ForceGraph2DView, ForceGraph3DView
Zustand          → useStore.ts (state management)
Recharts         → Analytics.tsx (charts)
Axios            → api.ts (HTTP client)
```

## 🚀 Execution Flow

### Starting the Application

1. **Setup Script** (`setup.sh`)
   - Creates Python venv
   - Installs dependencies
   - Downloads scispaCy model
   - Creates `.env` files

2. **Backend Startup** (`python -m app.main`)
   - Loads config from `.env`
   - Initializes database
   - Loads scispaCy model
   - Starts FastAPI server (port 8000)

3. **Frontend Startup** (`npm run dev`)
   - Compiles TypeScript
   - Builds with Vite
   - Starts dev server (port 5173)
   - Proxies `/api` to backend

### Processing a PDF

1. **User uploads PDF** → `UploadPanel.tsx`
2. **API call** → `api.ts` → `POST /api/process`
3. **Backend receives** → `main.py:process_pdfs()`
4. **Background job starts** → `process_pdfs_background()`
5. **Pipeline execution**:
   - PDFProcessor extracts text
   - NERService finds entities
   - RelationshipExtractor finds connections
   - GraphBuilder creates graph structure
6. **Frontend polls** → `GET /api/status/{job_id}`
7. **Graph loaded** → `useStore.setGraphData()`
8. **Visualization renders** → `ForceGraph2DView`

## 📝 Configuration Files

| File | Purpose |
|------|---------|
| `backend/.env` | API keys, database URL, CORS settings |
| `frontend/.env` | API base URL |
| `requirements.txt` | Python package versions |
| `package.json` | Node package versions |
| `tsconfig.json` | TypeScript compiler options |
| `tailwind.config.js` | Custom theme, colors |
| `vite.config.ts` | Build settings, proxy config |

## 🎨 Styling Architecture

```
Global Styles (index.css)
├─ Tailwind base/components/utilities
├─ Dark theme defaults
├─ Custom scrollbar
└─ Graph-specific classes

Component Styles
├─ Tailwind utility classes (inline)
├─ Gradient backgrounds
└─ Responsive breakpoints
```

## 💾 State Management

```
Zustand Store (useStore.ts)
├─ graphData (original graph)
├─ filteredGraphData (after filters)
├─ selectedNode (clicked node)
├─ highlightedNodes/Links (focus mode)
├─ filterOptions (user preferences)
├─ viewMode (2D/3D, labels)
├─ processingStatus (job tracking)
└─ UI state (sidebars, panels)
```

## 🔌 API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/` | Health check |
| POST | `/api/process` | Upload PDFs, start processing |
| GET | `/api/status/{job_id}` | Check job status |
| POST | `/api/graph/filter` | Filter graph data |
| POST | `/api/analytics` | Compute analytics |
| GET | `/api/projects` | List saved projects |

---

**Understanding this structure will help you:**
- 🔍 Find files quickly
- 🐛 Debug issues effectively
- ✨ Add new features
- 📚 Explain the architecture to judges

**For hackathon judges, focus on:**
- Clean separation of concerns (services, components)
- Full-stack integration (FastAPI ↔ React)
- Advanced NLP pipeline (backend/services/)
- Interactive visualization (components/)

