from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional
import uuid
import os
import shutil
from pathlib import Path
import asyncio
from datetime import datetime

from app.config import settings
from app.models import (
    GraphData,
    GraphAnalytics,
    ProcessingStatus,
    ProjectMetadata,
    PDFMetadata,
    init_db,
    get_db,
    Project,
    SessionLocal,
)
from app.services.auth_service import get_current_user, get_current_user_optional
from app.models.database import User
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
    LavaService,
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
lava_service = LavaService()

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
    current_user: User = Depends(get_current_user),
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
    
    # Save uploaded files with metadata
    saved_files = []
    for file in files:
        file_path = UPLOAD_DIR / f"{job_id}_{file.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        saved_files.append({
            "path": str(file_path),
            "original_name": file.filename
        })
    
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
        saved_files,
        project_name or f"Project_{job_id[:8]}",
        current_user.id
    )
    
    return processing_jobs[job_id]


async def process_pdfs_background(
    job_id: str,
    pdf_files: List[dict],  # Now receives list of {path, original_name}
    project_name: str,
    user_id: str
):
    """Background task to process PDFs - creates individual graph for each PDF"""
    from app.models.database import Project, Document, PDFGraphNode, PDFGraphEdge
    from sqlalchemy.orm import Session
    
    db = SessionLocal()
    try:
        # Create or get project (check by name and user_id to avoid conflicts)
        project = db.query(Project).filter(
            Project.name == project_name,
            Project.user_id == user_id
        ).first()
        if not project:
            project = Project(
                id=str(uuid.uuid4()),
                name=project_name,
                description=f"Project with {len(pdf_files)} PDFs",
                user_id=user_id
            )
            db.add(project)
            db.commit()
        
        processing_jobs[job_id].status = "processing"
        processing_jobs[job_id].progress = 0.0
        processing_jobs[job_id].message = "Processing PDFs individually..."
        
        pdf_graphs = []
        total_pdfs = len(pdf_files)
        
        # Process each PDF individually
        for idx, pdf_file in enumerate(pdf_files):
            pdf_path = pdf_file["path"]
            original_name = pdf_file["original_name"]
            base_progress = idx / total_pdfs
            progress_step = 1.0 / total_pdfs
            
            processing_jobs[job_id].message = f"Processing PDF {idx + 1}/{total_pdfs}: {original_name}"
            processing_jobs[job_id].progress = base_progress
            
            # Create document record with original filename
            doc_id = str(uuid.uuid4())
            document = Document(
                id=doc_id,
                project_id=project.id,
                filename=original_name,  # Use original filename for display
                file_path=pdf_path,  # Keep full path for file access
                processed=0,
                selected=1
            )
            db.add(document)
            db.commit()
            
            try:
                # Extract text from this PDF
                pdf_result = pdf_processor.process_pdfs([pdf_path])[0]
                
                if "error" in pdf_result:
                    document.processed = -1
                    db.commit()
                    continue
                
                sentences = pdf_result.get("sentences", [])
                
                # Extract entities for this PDF
                sentence_entities = ner_service.extract_entities_from_sentences(sentences)
                filtered_entities = ner_service.filter_entities(sentence_entities)
                unique_entities = ner_service.get_unique_entities(filtered_entities)
                
                # Extract relationships for this PDF
                relationships = relationship_extractor.extract_all_relationships(filtered_entities)
                
                # Build graph for this PDF
                pdf_graph = graph_builder.build_graph(unique_entities, relationships)
                
                # Save nodes to database
                for node in pdf_graph.nodes:
                    pdf_node = PDFGraphNode(
                        document_id=doc_id,
                        entity_id=node.id,
                        entity_type=node.group.value,
                        count=node.metadata.get("count", 1),
                        degree=node.value
                    )
                    db.add(pdf_node)
                
                # Save edges to database
                for edge in pdf_graph.edges:
                    pdf_edge = PDFGraphEdge(
                        document_id=doc_id,
                        source_id=edge.source,
                        target_id=edge.target,
                        weight=edge.value,
                        evidence=edge.metadata.get("all_evidence", []),
                        relationship_type=edge.metadata.get("relationship_type", "CO_OCCURRENCE")
                    )
                    db.add(pdf_edge)
                
                document.processed = 1
                db.commit()
                
                pdf_graphs.append(pdf_graph)
                
                print(f"✓ Processed {original_name}: {len(pdf_graph.nodes)} nodes, {len(pdf_graph.edges)} edges")
                
            except Exception as e:
                print(f"✗ Error processing {original_name}: {e}")
                document.processed = -1
                db.commit()
        
        # Merge all PDF graphs for the initial result
        if pdf_graphs:
            processing_jobs[job_id].message = "Merging graphs..."
            processing_jobs[job_id].progress = 0.95
            
            merged_graph = pdf_graphs[0]
            for pdf_graph in pdf_graphs[1:]:
                # Extract entities and relationships for merging
                base_entities = {n.id: {"original_name": n.id, "type": n.group.value, "count": n.metadata.get("count", 1)} for n in merged_graph.nodes}
                base_rels = [{"source": e.source, "target": e.target, "weight": e.value, "evidence": e.metadata.get("all_evidence", []), "relationship_type": e.metadata.get("relationship_type", "CO_OCCURRENCE")} for e in merged_graph.edges]
                
                new_entities = {n.id: {"original_name": n.id, "type": n.group.value, "count": n.metadata.get("count", 1)} for n in pdf_graph.nodes}
                new_rels = [{"source": e.source, "target": e.target, "weight": e.value, "evidence": e.metadata.get("all_evidence", []), "relationship_type": e.metadata.get("relationship_type", "CO_OCCURRENCE")} for e in pdf_graph.edges]
                
                merged_graph = graph_builder.merge_graphs(base_entities, base_rels, new_entities, new_rels)
            
            processing_jobs[job_id].result = merged_graph
        
        # Complete
        processing_jobs[job_id].status = "completed"
        processing_jobs[job_id].progress = 1.0
        processing_jobs[job_id].message = f"Processed {total_pdfs} PDFs successfully!"
        processing_jobs[job_id].result.metadata["project_id"] = project.id
        
    except Exception as e:
        processing_jobs[job_id].status = "failed"
        processing_jobs[job_id].message = f"Error: {str(e)}"
        print(f"Processing error for job {job_id}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
        # Don't cleanup uploaded files anymore since we keep them
        # for path in pdf_paths:
        #     try:
        #         os.remove(path)
        #     except:
        #         pass


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
async def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all saved projects with PDF metadata"""
    from app.models.database import Document, PDFGraphNode, PDFGraphEdge
    from collections import Counter
    
    projects = db.query(Project).filter(Project.user_id == current_user.id).all()
    
    result = []
    for p in projects:
        pdfs = []
        for doc in p.documents:
            # Count entities by type for this PDF
            entity_counts = Counter()
            for node in doc.pdf_nodes:
                entity_counts[node.entity_type] += 1
            
            pdfs.append(PDFMetadata(
                document_id=doc.id,
                filename=doc.filename,
                uploaded_at=doc.uploaded_at.isoformat(),
                processed=doc.processed == 1,
                selected=doc.selected == 1,
                node_count=len(doc.pdf_nodes),
                edge_count=len(doc.pdf_edges),
                entity_counts=dict(entity_counts)
            ))
        
        result.append(ProjectMetadata(
            project_id=p.id,
            name=p.name,
            description=p.description,
            created_at=p.created_at.isoformat(),
            updated_at=p.updated_at.isoformat(),
            pdf_count=len(p.documents),
            pdfs=pdfs
        ))
    
    return result


@app.get("/api/projects/{project_id}/pdfs", response_model=List[PDFMetadata])
async def get_project_pdfs(
    project_id: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all PDFs for a specific project"""
    from app.models.database import Document
    from collections import Counter
    
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    pdfs = []
    for doc in project.documents:
        entity_counts = Counter()
        for node in doc.pdf_nodes:
            entity_counts[node.entity_type] += 1
        
        pdfs.append(PDFMetadata(
            document_id=doc.id,
            filename=doc.filename,
            uploaded_at=doc.uploaded_at.isoformat(),
            processed=doc.processed == 1,
            selected=doc.selected == 1,
            node_count=len(doc.pdf_nodes),
            edge_count=len(doc.pdf_edges),
            entity_counts=dict(entity_counts)
        ))
    
    return pdfs


@app.post("/api/projects/{project_id}/select-pdfs")
async def update_pdf_selection(
    project_id: str,
    selected_document_ids: List[str],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update which PDFs are selected for graph visualization"""
    from app.models.database import Document
    
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Update all documents - set selected=0 for all, then selected=1 for selected ones
    for doc in project.documents:
        doc.selected = 1 if doc.id in selected_document_ids else 0
    
    db.commit()
    
    return {"status": "success", "selected_count": len(selected_document_ids)}


@app.post("/api/projects/{project_id}/pdfs")
async def add_pdfs_to_project(
    project_id: str,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add more PDFs to an existing project"""
    from app.models.database import Document, PDFGraphNode, PDFGraphEdge
    
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Validate files
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    for file in files:
        if not file.filename.endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {file.filename}. Only PDF files are supported."
            )
    
    # Create job ID for tracking
    job_id = str(uuid.uuid4())
    
    # Save uploaded files with metadata
    saved_files = []
    for file in files:
        file_path = UPLOAD_DIR / f"{job_id}_{file.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        saved_files.append({
            "path": str(file_path),
            "original_name": file.filename
        })
    
    # Initialize job status
    processing_jobs[job_id] = ProcessingStatus(
        job_id=job_id,
        status="pending",
        progress=0.0,
        message="Queued for processing"
    )
    
    # Start background processing for these new PDFs
    background_tasks.add_task(
        add_pdfs_to_project_background,
        job_id,
        project_id,
        saved_files,
        current_user.id
    )
    
    return processing_jobs[job_id]


async def add_pdfs_to_project_background(
    job_id: str,
    project_id: str,
    pdf_files: List[dict],  # Now receives list of {path, original_name}
    user_id: str
):
    """Background task to add PDFs to existing project"""
    from app.models.database import Project, Document, PDFGraphNode, PDFGraphEdge
    
    db = SessionLocal()
    try:
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.user_id == user_id
        ).first()
        if not project:
            processing_jobs[job_id].status = "failed"
            processing_jobs[job_id].message = "Project not found"
            return
        
        processing_jobs[job_id].status = "processing"
        processing_jobs[job_id].progress = 0.0
        processing_jobs[job_id].message = "Processing new PDFs..."
        
        total_pdfs = len(pdf_files)
        
        # Process each PDF individually
        for idx, pdf_file in enumerate(pdf_files):
            pdf_path = pdf_file["path"]
            original_name = pdf_file["original_name"]
            base_progress = idx / total_pdfs
            
            processing_jobs[job_id].message = f"Processing PDF {idx + 1}/{total_pdfs}: {original_name}"
            processing_jobs[job_id].progress = base_progress
            
            # Create document record with original filename
            doc_id = str(uuid.uuid4())
            document = Document(
                id=doc_id,
                project_id=project.id,
                filename=original_name,  # Use original filename for display
                file_path=pdf_path,  # Keep full path for file access
                processed=0,
                selected=1
            )
            db.add(document)
            db.commit()
            
            try:
                # Extract text from this PDF
                pdf_result = pdf_processor.process_pdfs([pdf_path])[0]
                
                if "error" in pdf_result:
                    document.processed = -1
                    db.commit()
                    continue
                
                sentences = pdf_result.get("sentences", [])
                
                # Extract entities for this PDF
                sentence_entities = ner_service.extract_entities_from_sentences(sentences)
                filtered_entities = ner_service.filter_entities(sentence_entities)
                unique_entities = ner_service.get_unique_entities(filtered_entities)
                
                # Extract relationships for this PDF
                relationships = relationship_extractor.extract_all_relationships(filtered_entities)
                
                # Build graph for this PDF
                pdf_graph = graph_builder.build_graph(unique_entities, relationships)
                
                # Save nodes to database
                for node in pdf_graph.nodes:
                    pdf_node = PDFGraphNode(
                        document_id=doc_id,
                        entity_id=node.id,
                        entity_type=node.group.value,
                        count=node.metadata.get("count", 1),
                        degree=node.value
                    )
                    db.add(pdf_node)
                
                # Save edges to database
                for edge in pdf_graph.edges:
                    pdf_edge = PDFGraphEdge(
                        document_id=doc_id,
                        source_id=edge.source,
                        target_id=edge.target,
                        weight=edge.value,
                        evidence=edge.metadata.get("all_evidence", []),
                        relationship_type=edge.metadata.get("relationship_type", "CO_OCCURRENCE")
                    )
                    db.add(pdf_edge)
                
                document.processed = 1
                db.commit()
                
                print(f"✓ Processed {original_name}: {len(pdf_graph.nodes)} nodes, {len(pdf_graph.edges)} edges")
                
            except Exception as e:
                print(f"✗ Error processing {original_name}: {e}")
                document.processed = -1
                db.commit()
        
        # Complete
        processing_jobs[job_id].status = "completed"
        processing_jobs[job_id].progress = 1.0
        processing_jobs[job_id].message = f"Added {total_pdfs} PDFs successfully!"
        
    except Exception as e:
        processing_jobs[job_id].status = "failed"
        processing_jobs[job_id].message = f"Error: {str(e)}"
        print(f"Processing error for job {job_id}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


@app.delete("/api/projects/{project_id}/pdfs/{document_id}")
async def delete_pdf_from_project(
    project_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a PDF and its graph data from a project"""
    from app.models.database import Document
    
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.project_id == project_id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete the document (cascade will delete nodes and edges)
    filename = document.filename
    db.delete(document)
    db.commit()
    
    return {"status": "success", "message": f"Deleted {filename}"}


@app.get("/api/projects/{project_id}/graph", response_model=GraphData)
async def get_project_graph(
    project_id: str,
    selected_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the merged graph from selected PDFs (or all PDFs if selected_only=False)"""
    from app.models.database import Document, PDFGraphNode, PDFGraphEdge
    
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get documents to include
    documents = [doc for doc in project.documents if doc.processed == 1]
    if selected_only:
        documents = [doc for doc in documents if doc.selected == 1]
    
    if not documents:
        return GraphData(nodes=[], edges=[], metadata={"project_id": project_id, "message": "No PDFs selected or processed"})
    
    # Build individual graphs for each PDF
    pdf_graphs = []
    for doc in documents:
        # Reconstruct graph from database
        nodes = []
        for node in doc.pdf_nodes:
            from app.models.schemas import Node, EntityType
            nodes.append(Node(
                id=node.entity_id,
                group=EntityType(node.entity_type),
                value=node.degree,
                metadata={"count": node.count, "degree": node.degree, "source_pdf": doc.filename}
            ))
        
        edges = []
        for edge in doc.pdf_edges:
            from app.models.schemas import Edge
            edges.append(Edge(
                source=edge.source_id,
                target=edge.target_id,
                value=edge.weight,
                title=edge.evidence[0] if edge.evidence else "",
                metadata={
                    "all_evidence": edge.evidence,
                    "relationship_type": edge.relationship_type,
                    "source_pdf": doc.filename
                }
            ))
        
        pdf_graphs.append(GraphData(nodes=nodes, edges=edges, metadata={"source": doc.filename}))
    
    # Merge all graphs
    if len(pdf_graphs) == 1:
        merged = pdf_graphs[0]
    else:
        merged = pdf_graphs[0]
        for pdf_graph in pdf_graphs[1:]:
            # Convert to dict format for merging
            base_entities = {n.id: {"original_name": n.id, "type": n.group.value, "count": n.metadata.get("count", 1)} for n in merged.nodes}
            base_rels = [{"source": e.source, "target": e.target, "weight": e.value, "evidence": e.metadata.get("all_evidence", []), "relationship_type": e.metadata.get("relationship_type", "CO_OCCURRENCE")} for e in merged.edges]
            
            new_entities = {n.id: {"original_name": n.id, "type": n.group.value, "count": n.metadata.get("count", 1)} for n in pdf_graph.nodes}
            new_rels = [{"source": e.source, "target": e.target, "weight": e.value, "evidence": e.metadata.get("all_evidence", []), "relationship_type": e.metadata.get("relationship_type", "CO_OCCURRENCE")} for e in pdf_graph.edges]
            
            merged = graph_builder.merge_graphs(base_entities, base_rels, new_entities, new_rels)
    
    merged.metadata["project_id"] = project_id
    merged.metadata["pdf_count"] = len(documents)
    merged.metadata["selected_pdfs"] = [doc.filename for doc in documents]
    
    return merged


# ==== Conversational Agent Endpoints ====

@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_graph(
    payload: dict,
    current_user: User = Depends(get_current_user)
):
    try:
        # Accept flexible JSON payload to avoid validation errors from clients
        message = (payload or {}).get("message", "")
        graph = (payload or {}).get("graph", {})
        conversation_history = (payload or {}).get("conversation_history", [])
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
            # Handle both string IDs and object references
            source_id = e.get("source")
            target_id = e.get("target")
            
            # If source/target are objects, extract the 'id' field
            if isinstance(source_id, dict):
                source_id = source_id.get("id")
            if isinstance(target_id, dict):
                target_id = target_id.get("id")
            
            relationships.append({
                "source": source_id,
                "target": target_id,
                "weight": e.get("value", 1.0),
                "evidence": (e.get("metadata") or {}).get("all_evidence", [e.get("title", "")]),
                "relationship_type": (e.get("metadata") or {}).get("relationship_type", "CO_OCCURRENCE"),
            })
        
        graph_builder.build_graph(entities, relationships)

        # Create agent with LLM service for intelligent chat
        agent = GraphConversationalAgent(graph_builder.graph, llm_service=llm_service)
        
        # Use LLM-powered chat if available, otherwise fallback to pattern matching
        result = await agent.chat(message, conversation_history)
        
        return ChatResponse(
            answer=result.get("answer", ""),
            citations=result.get("citations", []),
            relevant_nodes=result.get("relevant_nodes", []),
            relevant_edges=result.get("relevant_edges", []),
            tool_calls=result.get("tool_calls", []),
        )
    except Exception as e:
        print(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/hypotheses", response_model=HypothesesResponse)
async def generate_hypotheses(
    payload: dict,
    current_user: User = Depends(get_current_user)
):
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

@app.delete("/api/projects/{project_id}")
async def delete_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a project and all its associated data"""
    from app.models.database import Document, PDFGraphNode, PDFGraphEdge
    import os
    
    # Find project and verify ownership
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    try:
        # Delete associated files
        for document in project.documents:
            if document.file_path and os.path.exists(document.file_path):
                os.remove(document.file_path)
        
        # Delete all associated data (cascade should handle this, but being explicit)
        db.query(PDFGraphNode).filter(
            PDFGraphNode.document_id.in_([doc.id for doc in project.documents])
        ).delete(synchronize_session=False)
        
        db.query(PDFGraphEdge).filter(
            PDFGraphEdge.document_id.in_([doc.id for doc in project.documents])
        ).delete(synchronize_session=False)
        
        # Delete documents
        db.query(Document).filter(Document.project_id == project_id).delete()
        
        # Delete project
        db.delete(project)
        db.commit()
        
        return {"status": "success", "message": f"Project '{project.name}' deleted successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete project: {str(e)}")


@app.put("/api/projects/{project_id}")
async def rename_project(
    project_id: str,
    new_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Rename a project"""
    # Find project and verify ownership
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if not new_name.strip():
        raise HTTPException(status_code=400, detail="Project name cannot be empty")
    
    try:
        # Check if another project with the same name exists for this user
        existing_project = db.query(Project).filter(
            Project.name == new_name.strip(),
            Project.user_id == current_user.id,
            Project.id != project_id
        ).first()
        
        if existing_project:
            raise HTTPException(status_code=400, detail="A project with this name already exists")
        
        # Update project name
        project.name = new_name.strip()
        project.updated_at = datetime.utcnow()
        db.commit()
        
        return {"status": "success", "message": f"Project renamed to '{new_name.strip()}' successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to rename project: {str(e)}")


@app.get("/api/projects/{project_id}/export")
async def export_project(
    project_id: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export a project with all individual PDF graphs as JSON"""
    from app.models.schemas import PDFGraphExport, Node, Edge, EntityType
    
    try:
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.user_id == current_user.id
        ).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        pdf_graphs = []
        for doc in project.documents:
            if doc.processed != 1:
                continue
            
            # Build graph for this PDF
            nodes = []
            for node in doc.pdf_nodes:
                nodes.append(Node(
                    id=node.entity_id,
                    group=EntityType(node.entity_type),
                    value=node.degree,
                    metadata={"count": node.count, "degree": node.degree}
                ))
            
            edges = []
            for edge in doc.pdf_edges:
                edges.append(Edge(
                    source=edge.source_id,
                    target=edge.target_id,
                    value=edge.weight,
                    title=edge.evidence[0] if edge.evidence else "",
                    metadata={
                        "all_evidence": edge.evidence,
                        "relationship_type": edge.relationship_type
                    }
                ))
            
            pdf_graph = GraphData(nodes=nodes, edges=edges, metadata={"source": doc.filename})
            
            pdf_graphs.append(PDFGraphExport(
                document_id=doc.id,
                filename=doc.filename,
                uploaded_at=doc.uploaded_at.isoformat(),
                graph=pdf_graph
            ))
        
        from app.models.schemas import ProjectExport
        return ProjectExport(
            project_name=project.name,
            project_id=project.id,
            created_at=project.created_at.isoformat(),
            updated_at=project.updated_at.isoformat(),
            pdf_graphs=pdf_graphs,
            settings={}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/projects/import")
async def import_project(
    req: dict, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Import a project from JSON with per-PDF graphs"""
    from app.models.database import Project, Document, PDFGraphNode, PDFGraphEdge
    
    try:
        print(f"DEBUG Import: Received keys: {req.keys()}")
        
        project_data = req.get("project_data", req)
        
        # Create new project
        project_id = str(uuid.uuid4())
        project = Project(
            id=project_id,
            name=project_data.get("project_name", f"Imported Project {project_id[:8]}"),
            description="Imported project",
            user_id=current_user.id
        )
        db.add(project)
        db.commit()
        
        # Import each PDF graph
        pdf_graphs = project_data.get("pdf_graphs", [])
        for pdf_graph_data in pdf_graphs:
            doc_id = str(uuid.uuid4())
            document = Document(
                id=doc_id,
                project_id=project.id,
                filename=pdf_graph_data.get("filename", "unknown.pdf"),
                file_path="",  # No actual file for imported projects
                processed=1,
                selected=1
            )
            db.add(document)
            db.commit()
            
            # Import nodes
            graph = pdf_graph_data.get("graph", {})
            for node in graph.get("nodes", []):
                pdf_node = PDFGraphNode(
                    document_id=doc_id,
                    entity_id=node["id"],
                    entity_type=node["group"],
                    count=node.get("metadata", {}).get("count", 1),
                    degree=node.get("value", 1)
                )
                db.add(pdf_node)
            
            # Import edges
            for edge in graph.get("edges", []):
                pdf_edge = PDFGraphEdge(
                    document_id=doc_id,
                    source_id=edge["source"],
                    target_id=edge["target"],
                    weight=edge.get("value", 1.0),
                    evidence=edge.get("metadata", {}).get("all_evidence", []),
                    relationship_type=edge.get("metadata", {}).get("relationship_type", "CO_OCCURRENCE")
                )
                db.add(pdf_edge)
            
            db.commit()
        
        return {
            "status": "success",
            "project_id": project.id,
            "project_name": project.name,
            "pdf_count": len(pdf_graphs)
        }
    except Exception as e:
        print(f"ERROR Import: {str(e)}")
        import traceback
        traceback.print_exc()
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
    merge_with_existing: bool = False,
    current_user: User = Depends(get_current_user)
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
            f"Discovered_Papers_{job_id[:8]}",
            current_user.id
        )
        
        return processing_jobs[job_id]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def process_text_background(job_id: str, text: str, project_name: str, user_id: str):
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


# ==== Lava Payments Endpoints ====

@app.get("/api/lava/usage")
async def get_lava_usage():
    """Get LLM usage statistics from Lava Payments"""
    try:
        if not lava_service.enabled:
            return {"enabled": False, "message": "Lava Payments is not configured"}
        
        usage = await lava_service.get_usage_stats()
        return {"enabled": True, **usage}
    except Exception as e:
        import traceback
        print(f"Lava usage error: {e}")
        print(traceback.format_exc())
        # Return graceful fallback
        return {
            "enabled": True,
            "error": str(e),
            "message": "Usage endpoint unavailable. Use /api/lava/requests to see activity."
        }


@app.get("/api/lava/requests")
async def list_lava_requests(
    limit: int = 50,
    cursor: Optional[str] = None,
    metadata_filter: Optional[str] = None
):
    """List tracked API requests from Lava"""
    try:
        if not lava_service.enabled:
            return {"enabled": False, "message": "Lava Payments is not configured"}
        
        import json
        metadata = json.loads(metadata_filter) if metadata_filter else None
        
        requests = await lava_service.list_requests(
            limit=limit,
            cursor=cursor,
            metadata=metadata
        )
        return {"enabled": True, **requests}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/lava/status")
async def get_lava_status():
    """Check Lava Payments configuration status"""
    return {
        "enabled": lava_service.enabled,
        "configured": bool(settings.lava_secret_key),
        "has_connection_secret": bool(settings.lava_connection_secret),
        "has_product_secret": bool(settings.lava_product_secret),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
    )

