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
    PubMedService,
    ClinicalTrialsService,
)
from sqlalchemy.orm import Session
from app.models import (
    ChatRequest,
    ChatResponse,
    HypothesesRequest,
    HypothesesResponse,
    NerPreviewRequest,
    NerPreviewResponse,
    ProjectExport,
    ProjectImportRequest,
    PaperDiscoveryRequest,
    PaperDiscoveryResponse,
    DiscoveredPaper,
    TrialDiscoveryRequest,
    TrialDiscoveryResponse,
    ClinicalTrial,
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
pubmed_service = PubMedService()
ctgov_service = ClinicalTrialsService()

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
        project_name or f"Project_{job_id[:8]}"
    )
    
    return processing_jobs[job_id]


async def process_pdfs_background(
    job_id: str,
    pdf_paths: List[str],
    project_name: str
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


# ==== Project Export/Import Endpoints ====

@app.get("/api/projects/{project_id}/export", response_model=ProjectExport)
async def export_project(project_id: str, db: Session = Depends(get_db)):
    """Export a project as JSON"""
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Reconstruct graph from database
        nodes = []
        for gn in project.graph_nodes:
            nodes.append({
                "id": gn.entity_id,
                "group": gn.entity_type,
                "value": gn.degree,
                "metadata": {"count": gn.count, "degree": gn.degree}
            })
        
        edges = []
        for ge in project.graph_edges:
            edges.append({
                "source": ge.source_id,
                "target": ge.target_id,
                "value": ge.weight,
                "title": ge.evidence[0] if ge.evidence else "",
                "metadata": {
                    "all_evidence": ge.evidence,
                    "relationship_type": ge.relationship_type
                }
            })
        
        graph = GraphData(nodes=nodes, edges=edges, metadata={})
        
        return ProjectExport(
            project_name=project.name,
            created_at=project.created_at.isoformat(),
            updated_at=project.updated_at.isoformat(),
            graph=graph,
            sources=[{"type": "pdf", "filename": doc.filename} for doc in project.documents],
            settings={}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/projects/import")
async def import_project(req: dict):
    """Import a project from JSON"""
    try:
        print(f"DEBUG Import: Received keys: {req.keys()}")
        
        # Accept flexible JSON structure
        project_data = req.get("project_data", req)
        
        # Extract graph data
        if isinstance(project_data, dict) and "graph" in project_data:
            graph_data = project_data["graph"]
            print(f"DEBUG Import: Found graph with {len(graph_data.get('nodes', []))} nodes")
        else:
            # Assume the payload itself is the graph
            graph_data = project_data
            print(f"DEBUG Import: Using raw data as graph")
        
        # Ensure graph has required structure
        if not isinstance(graph_data, dict):
            raise ValueError("Graph data must be a dictionary")
        
        if "nodes" not in graph_data or "edges" not in graph_data:
            raise ValueError("Graph must have 'nodes' and 'edges' arrays")
        
        print(f"DEBUG Import: Returning {len(graph_data['nodes'])} nodes, {len(graph_data['edges'])} edges")
        return {"status": "success", "graph": graph_data}
    except Exception as e:
        print(f"ERROR Import: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==== Paper Discovery Endpoints ====

@app.post("/api/discover/papers", response_model=PaperDiscoveryResponse)
async def discover_papers(req: PaperDiscoveryRequest):
    """Discover papers from PubMed and optionally process them"""
    try:
        papers = pubmed_service.discover_and_fetch(req.query, req.max_results)
        
        discovered = [
            DiscoveredPaper(**paper) for paper in papers if paper
        ]
        
        return PaperDiscoveryResponse(
            papers=discovered,
            status="completed"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/discover/papers/process")
async def process_discovered_papers(
    background_tasks: BackgroundTasks,
    papers: List[DiscoveredPaper],
    merge_with_existing: bool = False
):
    """Process discovered papers through NER pipeline"""
    try:
        job_id = str(uuid.uuid4())
        
        # Combine all abstracts into sentences
        all_text = "\n\n".join([f"{p.title}. {p.abstract}" for p in papers])
        
        processing_jobs[job_id] = ProcessingStatus(
            job_id=job_id,
            status="pending",
            progress=0.0,
            message="Processing discovered papers"
        )
        
        background_tasks.add_task(
            process_text_background,
            job_id,
            all_text,
            f"Discovered_Papers_{job_id[:8]}"
        )
        
        return processing_jobs[job_id]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def process_text_background(job_id: str, text: str, project_name: str):
    """Background task to process text through NER pipeline"""
    try:
        processing_jobs[job_id].status = "processing"
        processing_jobs[job_id].progress = 0.2
        processing_jobs[job_id].message = "Extracting entities..."
        
        # Split into sentences
        doc = ner_service.nlp(text)
        sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
        
        processing_jobs[job_id].progress = 0.4
        sentence_entities = ner_service.extract_entities_from_sentences(sentences)
        
        processing_jobs[job_id].progress = 0.6
        filtered_entities = ner_service.filter_entities(sentence_entities)
        unique_entities = ner_service.get_unique_entities(filtered_entities)
        
        processing_jobs[job_id].progress = 0.8
        processing_jobs[job_id].message = "Extracting relationships..."
        relationships = relationship_extractor.extract_all_relationships(filtered_entities)
        
        processing_jobs[job_id].progress = 0.9
        processing_jobs[job_id].message = "Building graph..."
        graph_data = graph_builder.build_graph(unique_entities, relationships)
        
        processing_jobs[job_id].status = "completed"
        processing_jobs[job_id].progress = 1.0
        processing_jobs[job_id].message = "Complete!"
        processing_jobs[job_id].result = graph_data
    except Exception as e:
        processing_jobs[job_id].status = "failed"
        processing_jobs[job_id].message = f"Error: {str(e)}"


# ==== Clinical Trials Discovery Endpoints ====

@app.post("/api/discover/trials", response_model=TrialDiscoveryResponse)
async def discover_trials(req: TrialDiscoveryRequest):
    """Discover clinical trials and convert to graph nodes"""
    try:
        trials = ctgov_service.search_trials(
            req.condition,
            req.max_results,
            req.phases,
            req.status
        )
        
        trial_objects = [ClinicalTrial(**t) for t in trials if t.get("nct_id")]
        
        # Convert trials to graph nodes and edges
        nodes = []
        edges = []
        
        for trial in trial_objects:
            # Add trial node
            trial_node_id = f"TRIAL:{trial.nct_id}"
            nodes.append({
                "id": trial_node_id,
                "group": "ENTITY",
                "value": len(trial.interventions) + 1,
                "metadata": {
                    "type": "clinical_trial",
                    "nct_id": trial.nct_id,
                    "phase": trial.phase,
                    "status": trial.status,
                    "url": trial.url
                }
            })
            
            # Add condition node
            if trial.condition:
                nodes.append({
                    "id": trial.condition,
                    "group": "DISEASE",
                    "value": 1,
                    "metadata": {"type": "disease"}
                })
                edges.append({
                    "source": trial_node_id,
                    "target": trial.condition,
                    "value": 1.0,
                    "title": f"{trial.nct_id} studies {trial.condition}",
                    "metadata": {
                        "relationship_type": "CLINICAL_TRIAL_STUDIES",
                        "all_evidence": [trial.brief_summary[:200]]
                    }
                })
            
            # Add intervention nodes
            for intervention in trial.interventions:
                nodes.append({
                    "id": intervention,
                    "group": "CHEMICAL",
                    "value": 1,
                    "metadata": {"type": "intervention"}
                })
                edges.append({
                    "source": trial_node_id,
                    "target": intervention,
                    "value": 1.0,
                    "title": f"{trial.nct_id} tests {intervention}",
                    "metadata": {
                        "relationship_type": "CLINICAL_TRIAL_TESTS",
                        "all_evidence": [trial.brief_summary[:200]]
                    }
                })
        
        # Deduplicate nodes
        unique_nodes = {n["id"]: n for n in nodes}
        graph = GraphData(
            nodes=list(unique_nodes.values()),
            edges=edges,
            metadata={"source": "clinicaltrials.gov"}
        )
        
        return TrialDiscoveryResponse(
            trials=trial_objects,
            graph=graph
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

