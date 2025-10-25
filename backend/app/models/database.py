from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from app.config import settings

Base = declarative_base()
engine = create_engine(settings.database_url, connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Project(Base):
    __tablename__ = "projects"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")
    graph_nodes = relationship("GraphNode", back_populates="project", cascade="all, delete-orphan")
    graph_edges = relationship("GraphEdge", back_populates="project", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("projects.id"))
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    processed = Column(Integer, default=0)  # 0=pending, 1=completed, -1=failed
    
    project = relationship("Project", back_populates="documents")


class GraphNode(Base):
    __tablename__ = "graph_nodes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String, ForeignKey("projects.id"))
    node_id = Column(String, nullable=False)  # Entity name
    entity_type = Column(String, nullable=False)
    degree = Column(Integer, default=0)
    node_metadata = Column(JSON, default={})
    
    project = relationship("Project", back_populates="graph_nodes")


class GraphEdge(Base):
    __tablename__ = "graph_edges"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String, ForeignKey("projects.id"))
    source = Column(String, nullable=False)
    target = Column(String, nullable=False)
    weight = Column(Float, default=1.0)
    evidence = Column(Text, default="")
    edge_metadata = Column(JSON, default={})
    
    project = relationship("Project", back_populates="graph_edges")


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency for database sessions"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

