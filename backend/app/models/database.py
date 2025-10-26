from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from app.config import settings

Base = declarative_base()
engine = create_engine(settings.database_url, connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)  # Google OAuth user ID
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    picture = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    user_id = Column(String, ForeignKey("users.id"), nullable=False)  # Google OAuth user ID
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="projects")
    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("projects.id"))
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    processed = Column(Integer, default=0)  # 0=pending, 1=completed, -1=failed
    selected = Column(Integer, default=1)  # 0=unselected, 1=selected for graph
    
    project = relationship("Project", back_populates="documents")
    pdf_nodes = relationship("PDFGraphNode", back_populates="document", cascade="all, delete-orphan")
    pdf_edges = relationship("PDFGraphEdge", back_populates="document", cascade="all, delete-orphan")


class PDFGraphNode(Base):
    """Individual graph nodes for each PDF document"""
    __tablename__ = "pdf_graph_nodes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String, ForeignKey("documents.id"))
    entity_id = Column(String, nullable=False)  # Entity name
    entity_type = Column(String, nullable=False)
    count = Column(Integer, default=1)  # Occurrences in this PDF
    degree = Column(Integer, default=0)
    
    document = relationship("Document", back_populates="pdf_nodes")


class PDFGraphEdge(Base):
    """Individual graph edges for each PDF document"""
    __tablename__ = "pdf_graph_edges"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String, ForeignKey("documents.id"))
    source_id = Column(String, nullable=False)
    target_id = Column(String, nullable=False)
    weight = Column(Float, default=1.0)
    evidence = Column(JSON, default=list)  # List of evidence sentences
    relationship_type = Column(String, default="CO_OCCURRENCE")
    
    document = relationship("Document", back_populates="pdf_edges")


class ChatMessage(Base):
    """Chat messages and insights for each project"""
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    role = Column(String, nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    citations = Column(JSON, default=list)  # List of citation objects
    relevant_nodes = Column(JSON, default=list)  # List of node IDs
    is_agentic = Column(Integer, default=0)  # 0=regular chat, 1=agentic research
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Optional metadata (renamed from 'metadata' which is reserved)
    extra_data = Column(JSON, default=dict)  # For storing additional context


class Hypothesis(Base):
    """Generated hypotheses and insights for each project"""
    __tablename__ = "hypotheses"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    title = Column(String, nullable=False)
    explanation = Column(Text, nullable=False)
    entities = Column(JSON, default=list)  # List of entity names
    evidence_sentences = Column(JSON, default=list)  # Supporting evidence
    edge_pairs = Column(JSON, default=list)  # Supporting edges [[a,b], [b,c]]
    confidence = Column(Float, default=0.5)
    focus_entity = Column(String, default="")  # Entity this hypothesis focuses on
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Additional metadata
    extra_data = Column(JSON, default=dict)


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

