from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional
import uuid
import os
import shutil
from pathlib import Path
import asyncio

from app.config import settings
from app.models import (
    GraphData,
    GraphAnalytics,
    ProcessingStatus,
    ProjectMetadata,
    init_db,
    get_db,
    Project,
)
from app.services import (
    PDFProcessor,
    NERService,
    RelationshipExtractor,
    GraphBuilder,
    LLMService,
    GraphConversationalAgent,
    HypothesisAgent,
)
from sqlalchemy.orm import Session
from app.models import (
    ChatRequest,
    ChatResponse,
    HypothesesRequest,
    HypothesesResponse,
    NerPreviewRequest,
    NerPreviewResponse,
)

# Initialize FastAPI app
app = FastAPI(
    title="Synapse Mapper API",
    description="Transform biomedical PDFs into interactive knowledge graphs",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
pdf_processor = PDFProcessor()
from app.config import settings as _settings
ner_service = NERService(model_name=_settings.scispacy_model)
relationship_extractor = RelationshipExtractor()
graph_builder = GraphBuilder()
llm_service = LLMService()

# Storage for processing jobs
processing_jobs = {}

# Create upload directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()
    print("✅ Database initialized")
    print(f"✅ Synapse Mapper API running on http://{settings.api_host}:{settings.api_port}")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "Synapse Mapper API",
        "version": "1.0.0",
        "llm_enabled": settings.enable_llm_extraction,
    }


@app.post("/api/process", response_model=ProcessingStatus)
async def process_pdfs(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    project_name: Optional[str] = None,
    enable_llm: bool = False,
):
    """
    Process uploaded PDF files and generate knowledge graph
    
    This endpoint:
    1. Accepts multiple PDF files
    2. Extracts text and entities
    3. Identifies relationships
    4. Builds an interactive graph
    5. Returns graph data for visualization
    """
    # Validate files
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    for file in files:
        if not file.filename.endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {file.filename}. Only PDF files are supported."
            )
    
    # Create job ID
    job_id = str(uuid.uuid4())
    
    # Save uploaded files
    saved_paths = []
    for file in files:
        file_path = UPLOAD_DIR / f"{job_id}_{file.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        saved_paths.append(str(file_path))
    
    # Initialize job status
    processing_jobs[job_id] = ProcessingStatus(
        job_id=job_id,
        status="pending",
        progress=0.0,
        message="Queued for processing"
    )
    
    # Start background processing
    background_tasks.add_task(
        process_pdfs_background,
        job_id,
        saved_paths,
        project_name or f"Project_{job_id[:8]}",
        enable_llm
    )
    
    return processing_jobs[job_id]


async def process_pdfs_background(
    job_id: str,
    pdf_paths: List[str],
    project_name: str,
    enable_llm: bool = False
):
    """Background task to process PDFs"""
    try:
        # Update status
        processing_jobs[job_id].status = "processing"
        processing_jobs[job_id].progress = 0.1
        processing_jobs[job_id].message = "Extracting text from PDFs..."
        
        # Step 1: Extract text from PDFs
        pdf_results = pdf_processor.process_pdfs(pdf_paths)
        processing_jobs[job_id].progress = 0.3
        processing_jobs[job_id].message = f"Extracted text from {len(pdf_results)} PDFs"
        
        # Combine all sentences
        all_sentences = []
        for result in pdf_results:
            if "sentences" in result:
                all_sentences.extend(result["sentences"])
        
        # Step 2: Extract entities using NER
        processing_jobs[job_id].progress = 0.4
        processing_jobs[job_id].message = "Extracting biomedical entities..."
        
        print(f"DEBUG: Total sentences to process: {len(all_sentences)}")
        sentence_entities = ner_service.extract_entities_from_sentences(all_sentences)
        print(f"DEBUG: Sentences with entities: {len(sentence_entities)}")
        
        filtered_entities = ner_service.filter_entities(sentence_entities)
        print(f"DEBUG: After filtering: {len(filtered_entities)} sentences")
        
        unique_entities = ner_service.get_unique_entities(filtered_entities)
        print(f"DEBUG: Unique entities found: {len(unique_entities)}")
        print(f"DEBUG: Entity names: {list(unique_entities.keys())[:10]}")
        
        processing_jobs[job_id].progress = 0.6
        processing_jobs[job_id].message = f"Found {len(unique_entities)} unique entities"
        
        # Step 3: Extract relationships
        processing_jobs[job_id].progress = 0.7
        processing_jobs[job_id].message = "Extracting relationships..."
        
        relationships = relationship_extractor.extract_all_relationships(filtered_entities)
        print(f"DEBUG: Relationships found: {len(relationships)}")
        
        processing_jobs[job_id].progress = 0.8
        processing_jobs[job_id].message = f"Found {len(relationships)} relationships"
        
        # Step 4: Build graph
        processing_jobs[job_id].progress = 0.9
        processing_jobs[job_id].message = "Building knowledge graph..."
        
        graph_data = graph_builder.build_graph(unique_entities, relationships)
        
        # Step 5: Compute analytics
        analytics = graph_builder.compute_analytics()
        graph_data.metadata["analytics"] = analytics.dict()
        
        # Complete
        processing_jobs[job_id].status = "completed"
        processing_jobs[job_id].progress = 1.0
        processing_jobs[job_id].message = "Processing complete!"
        processing_jobs[job_id].result = graph_data
        
        # Cleanup uploaded files
        for path in pdf_paths:
            try:
                os.remove(path)
            except:
                pass
        
    except Exception as e:
        processing_jobs[job_id].status = "failed"
        processing_jobs[job_id].message = f"Error: {str(e)}"
        print(f"Processing error for job {job_id}: {e}")


@app.get("/api/status/{job_id}", response_model=ProcessingStatus)
async def get_processing_status(job_id: str):
    """Get the status of a processing job"""
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return processing_jobs[job_id]


@app.post("/api/graph/filter")
async def filter_graph(
    graph_data: GraphData,
    min_degree: int = 1,
    entity_types: Optional[List[str]] = None,
    top_n: Optional[int] = None,
):
    """Filter an existing graph based on criteria"""
    try:
        # Rebuild internal graph from data
        entities = {
            node.id: {
                "original_name": node.id,
                "type": node.group.value,
                "count": node.metadata.get("count", 1)
            }
            for node in graph_data.nodes
        }
        
        relationships = [
            {
                "source": edge.source,
                "target": edge.target,
                "weight": edge.value,
                "evidence": edge.metadata.get("all_evidence", [edge.title]),
                "relationship_type": edge.metadata.get("relationship_type", "CO_OCCURRENCE")
            }
            for edge in graph_data.edges
        ]
        
        graph_builder.build_graph(entities, relationships)
        filtered_graph = graph_builder.filter_graph(min_degree, entity_types, top_n)
        
        return filtered_graph
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analytics", response_model=GraphAnalytics)
async def compute_graph_analytics(graph_data: GraphData):
    """Compute analytics for a graph"""
    try:
        # Rebuild internal graph
        entities = {
            node.id: {
                "original_name": node.id,
                "type": node.group.value,
                "count": node.metadata.get("count", 1)
            }
            for node in graph_data.nodes
        }
        
        relationships = [
            {
                "source": edge.source,
                "target": edge.target,
                "weight": edge.value,
                "evidence": edge.metadata.get("all_evidence", [edge.title]),
                "relationship_type": edge.metadata.get("relationship_type", "CO_OCCURRENCE")
            }
            for edge in graph_data.edges
        ]
        
        graph_builder.build_graph(entities, relationships)
        analytics = graph_builder.compute_analytics()
        
        return analytics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/projects", response_model=List[ProjectMetadata])
async def list_projects(db: Session = Depends(get_db)):
    """List all saved projects"""
    projects = db.query(Project).all()
    
    return [
        ProjectMetadata(
            project_id=p.id,
            name=p.name,
            description=p.description,
            created_at=p.created_at.isoformat(),
            updated_at=p.updated_at.isoformat(),
            pdf_count=len(p.documents),
            node_count=len(p.graph_nodes),
            edge_count=len(p.graph_edges),
        )
        for p in projects
    ]


# ==== Conversational Agent Endpoints ====

@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_graph(payload: dict):
    try:
        # Accept flexible JSON payload to avoid validation errors from clients
        message = (payload or {}).get("message", "")
        graph = (payload or {}).get("graph", {})
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])

        # Rebuild graph
        entities = {
            n.get("id"): {
                "original_name": n.get("id"),
                "type": (n.get("group") or "UNKNOWN"),
                "count": (n.get("metadata") or {}).get("count", 1),
            }
            for n in nodes
            if n.get("id")
        }
        relationships = []
        for e in edges:
            relationships.append({
                "source": e.get("source"),
                "target": e.get("target"),
                "weight": e.get("value", 1.0),
                "evidence": (e.get("metadata") or {}).get("all_evidence", [e.get("title", "")]),
                "relationship_type": (e.get("metadata") or {}).get("relationship_type", "CO_OCCURRENCE"),
            })
        graph_builder.build_graph(entities, relationships)

        agent = GraphConversationalAgent(graph_builder.graph)
        text = str(message).strip()
        answer = ""
        citations: List[str] = []
        relevant_nodes: List[str] = []
        relevant_edges: List[List[str]] = []
        tool_calls: List[str] = []

        if "shortest path" in text.lower() and " between " in text.lower():
            try:
                lower = text.lower()
                seg = lower.split(" between ", 1)[1]
                parts = seg.split(" and ")
                a = parts[0].strip()
                b = parts[1].strip()
                def best_match(name: str) -> str:
                    names = [n for n in graph_builder.graph.nodes()]
                    for n in names:
                        if n.lower() == name:
                            return n
                    for n in names:
                        if name in n.lower():
                            return n
                    return name
                a_real = best_match(a)
                b_real = best_match(b)
                res = agent.shortest_path(a_real, b_real)
                tool_calls.append("shortest_path")
                if res["paths"]:
                    path = res["paths"][0]
                    nodes = path["nodes"]
                    edges = path["edges"]
                    answer = f"Shortest path: {' → '.join(nodes)}"
                    relevant_nodes = nodes
                    relevant_edges = [[e["source"], e["target"]] for e in edges]
                    citations = [evi for e in edges for evi in e.get("evidence", [])][:3]
                else:
                    answer = "No path found between the specified entities."
            except Exception:
                answer = "Could not parse entities for shortest path. Use 'shortest path between A and B'."
        elif text.lower().startswith("neighbors of "):
            name = text[len("neighbors of "):].strip()
            target = None
            for n in graph_builder.graph.nodes():
                if n.lower() == name.lower():
                    target = n
                    break
            res = agent.get_neighbors(target or name, depth=1)
            tool_calls.append("get_neighbors")
            layers = res.get("layers", [])
            if layers:
                neighbors = list({item["target"] for item in layers[0]})
                answer = f"Neighbors of {res['entity']}: {', '.join(neighbors[:20])}"
                relevant_nodes = [res["entity"], *neighbors]
                relevant_edges = [[res["entity"], t] for t in neighbors]
                citations = [e for item in layers[0] for e in item.get("evidence", [])][:3]
            else:
                answer = f"No neighbors found for {res['entity']}."
        elif text.lower().startswith("common connections "):
            try:
                names = [s.strip() for s in text.split(" ", 2)[2].split(",")]
                real = []
                node_names = [n for n in graph_builder.graph.nodes()]
                for q in names:
                    m = None
                    for n in node_names:
                        if n.lower() == q.lower():
                            m = n
                            break
                    real.append(m or q)
                res = agent.common_connections(real)
                tool_calls.append("common_connections")
                commons = res.get("common", [])
                if commons:
                    answer = "Common connections: " + ", ".join([c["entity"] for c in commons[:20]])
                    relevant_nodes = real + [c["entity"] for c in commons]
                else:
                    answer = "No common connections found."
            except Exception:
                answer = "Use 'common connections A, B, C'"
        else:
            stats = payload.graph.metadata or {}
            answer = (
                f"Graph has {stats.get('total_nodes', len(payload.graph.nodes))} nodes and "
                f"{stats.get('total_edges', len(payload.graph.edges))} edges. "
                "Ask: 'shortest path between A and B', 'neighbors of X', or 'common connections A, B'."
            )

        return ChatResponse(
            answer=answer,
            citations=citations,
            relevant_nodes=relevant_nodes,
            relevant_edges=relevant_edges,
            tool_calls=tool_calls,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/hypotheses", response_model=HypothesesResponse)
async def generate_hypotheses(payload: dict):
    try:
        graph = (payload or {}).get("graph", {})
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])
        focus_entity = (payload or {}).get("focus_entity")
        max_results = int((payload or {}).get("max_results", 10))

        entities = {
            n.get("id"): {
                "original_name": n.get("id"),
                "type": (n.get("group") or "UNKNOWN"),
                "count": (n.get("metadata") or {}).get("count", 1),
            }
            for n in nodes
            if n.get("id")
        }
        relationships = []
        for e in edges:
            relationships.append({
                "source": e.get("source"),
                "target": e.get("target"),
                "weight": e.get("value", 1.0),
                "evidence": (e.get("metadata") or {}).get("all_evidence", [e.get("title", "")]),
                "relationship_type": (e.get("metadata") or {}).get("relationship_type", "CO_OCCURRENCE"),
            })
        graph_builder.build_graph(entities, relationships)

        agent = HypothesisAgent(graph_builder.graph)
        hyps = agent.generate(focus=focus_entity, max_results=max_results)
        normalized = [
            {
                "title": h["title"],
                "explanation": h["explanation"],
                "entities": h.get("entities", []),
                "evidence_sentences": h.get("evidence_sentences", []),
                "edge_pairs": h.get("edge_pairs", []),
                "confidence": float(h.get("confidence", 0.5)),
            }
            for h in hyps
        ]

        return HypothesesResponse(hypotheses=normalized)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ner/preview", response_model=NerPreviewResponse)
async def ner_preview(req: NerPreviewRequest):
    try:
        doc = ner_service.nlp.make_doc(req.text)
        if not ner_service.nlp.has_pipe("sentencizer"):
            try:
                ner_service.nlp.add_pipe("sentencizer")
            except Exception:
                pass
        doc = ner_service.nlp(req.text)
        sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
        sent_ents = ner_service.extract_entities_from_sentences(sentences)

        original = ner_service.min_entity_occurrences
        ner_service.min_entity_occurrences = max(1, req.min_occurrences)
        filtered = ner_service.filter_entities(sent_ents)
        unique = ner_service.get_unique_entities(filtered)
        ner_service.min_entity_occurrences = original

        def to_schema(items: List[dict]) -> List[dict]:
            return [
                {
                    "sentence_id": i["sentence_id"],
                    "sentence": i["sentence"],
                    "entities": i["entities"],
                }
                for i in items
            ]

        # Build debug info
        from collections import Counter
        label_counter = Counter()
        for s in sentences[: min(50, len(sentences))]:
            d = ner_service.nlp(s)
            for ent in d.ents:
                label_counter[ent.label_] += 1

        sample_by_label = {}
        for s in sentences[: min(50, len(sentences))]:
            d = ner_service.nlp(s)
            for ent in d.ents:
                lbl = ent.label_
                sample_by_label.setdefault(lbl, [])
                if len(sample_by_label[lbl]) < 5:
                    sample_by_label[lbl].append(ent.text)

        return NerPreviewResponse(
            sentences=to_schema(filtered),
            unique_entities=unique,
            raw_sentences=to_schema(sent_ents) if req.return_raw else None,
            debug={
                "label_counts": dict(label_counter),
                "samples": sample_by_label,
                "model": _settings.scispacy_model,
                "min_entity_occurrences": original,
                "used_min_occurrences": max(1, req.min_occurrences),
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
    )

