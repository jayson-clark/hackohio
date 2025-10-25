# ⚡ Quickstart Guide

Get Synapse Mapper running in 5 minutes!

## One-Command Setup

```bash
./setup.sh
```

This will:
- ✅ Create Python virtual environment
- ✅ Install all backend dependencies
- ✅ Download scispaCy biomedical model
- ✅ Install frontend dependencies
- ✅ Create configuration files

## Start the Application

### Option 1: Automated (with tmux)
```bash
./run.sh
```

### Option 2: Manual (two terminals)

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
python -m app.main
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

## Open Your Browser

Navigate to: **http://localhost:5173**

## First Upload

1. Drag & drop 2-3 biomedical PDF files
2. Click "Generate Knowledge Graph"
3. Wait ~30-60 seconds for processing
4. Explore your graph!

## Sample Data Sources

Need PDFs to test with? Try:

- **PubMed Central**: https://www.ncbi.nlm.nih.gov/pmc/
  - Search for: "cancer immunotherapy" or "CRISPR gene editing"
  - Filter by: "Free full text"
  - Download 2-5 papers

- **bioRxiv**: https://www.biorxiv.org/
  - Preprint papers in biology

## Quick Tour

### 1. Upload Interface
- Drag & drop PDFs
- Optional: Add project name
- Optional: Enable LLM extraction (requires API key)

### 2. Processing
Watch real-time progress:
- Text extraction
- Entity recognition
- Relationship extraction
- Graph building

### 3. Graph Visualization
- **Pan**: Click and drag
- **Zoom**: Scroll wheel
- **Select Node**: Click any node
- **View Evidence**: Hover over edges

### 4. Sidebar Controls
- **Search**: Find entities by name
- **2D/3D**: Toggle view mode
- **Filters**: Show/hide entity types
- **Min Degree**: Filter by connections

### 5. Analytics
Click "View Analytics" to see:
- Entity distribution
- Most central nodes
- Community detection
- Graph statistics

### 6. Export
Bottom-right button:
- JSON (full data)
- CSV (nodes & edges)
- PNG (graph image)

## Common Issues

### Backend won't start
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

### Frontend won't start
```bash
cd frontend
rm -rf node_modules
npm install
```

### scispaCy model not found
```bash
cd backend
source venv/bin/activate
pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_lg-0.5.4.tar.gz
```

### CORS errors
Check backend `.env` file:
```
CORS_ORIGINS=["http://localhost:5173", "http://localhost:3000"]
```

## Performance Tips

### For Demo/Hackathon:
- Start with 2-3 PDFs (< 20 pages each)
- Use 2D view for smooth performance
- Filter by minimum degree = 2

### For Research:
- Process up to 10-20 PDFs at once
- Use entity type filters to focus
- Export results for external analysis

## Next Steps

1. **Customize Colors**: Edit `frontend/src/types/index.ts`
2. **Add LLM**: Set API keys in `backend/.env`
3. **Advanced Filters**: Explore sidebar options
4. **Export Data**: Try all export formats

## Resources

- **Full README**: See `README.md`
- **Demo Guide**: See `DEMO_GUIDE.md` (for hackathon presentations)
- **API Docs**: http://localhost:8000/docs (when backend is running)

## Getting Help

Check these in order:
1. README.md - Full documentation
2. Backend logs - Terminal running backend
3. Frontend console - Browser dev tools (F12)
4. API documentation - http://localhost:8000/docs

---

**You're ready to go! Start uploading PDFs and exploring! 🧬**

