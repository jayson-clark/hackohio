from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from enum import Enum


class EntityType(str, Enum):
    """Biomedical entity types from scispaCy"""
    ENTITY = "ENTITY"  # Generic biomedical entity
    GENE_OR_GENE_PRODUCT = "GENE_OR_GENE_PRODUCT"
    CHEMICAL = "CHEMICAL"
    DISEASE = "DISEASE"
    ORGANISM = "ORGANISM"
    CELL_TYPE = "CELL_TYPE"
    TISSUE = "TISSUE"
    ORGAN = "ORGAN"
    UNKNOWN = "UNKNOWN"


class Node(BaseModel):
    """Graph node representing a biomedical entity"""
    id: str = Field(..., description="Unique identifier (entity name)")
    group: EntityType = Field(..., description="Entity type/category")
    value: int = Field(default=1, description="Node size (degree/importance)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional node metadata")


class Edge(BaseModel):
    """Graph edge representing a relationship between entities"""
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    value: float = Field(default=1.0, description="Relationship strength/weight")
    title: str = Field(default="", description="Evidence sentence")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional edge metadata")


class GraphData(BaseModel):
    """Complete graph structure for visualization"""
    nodes: List[Node]
    edges: List[Edge]
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Graph-level metadata")


class GraphAnalytics(BaseModel):
    """Graph analytics and statistics"""
    total_nodes: int
    total_edges: int
    density: float
    avg_degree: float
    communities: List[List[str]]
    centrality_scores: Dict[str, float]
    entity_counts: Dict[str, int]


class ProcessingStatus(BaseModel):
    """Status of PDF processing job"""
    job_id: str
    status: str  # "pending", "processing", "completed", "failed"
    progress: float  # 0.0 to 1.0
    message: str = ""
    result: Optional[GraphData] = None


class ProjectMetadata(BaseModel):
    """Project information"""
    project_id: str
    name: str
    description: str = ""
    created_at: str
    updated_at: str
    pdf_count: int
    node_count: int
    edge_count: int

