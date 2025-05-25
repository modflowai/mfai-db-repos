"""
SQLAlchemy ORM models for the MFAI DB Repos database.

This module defines the SQLAlchemy models that map to the database tables
for repositories and repository files.
"""
import datetime
from pathlib import Path
from typing import List

from sqlalchemy import (
    Column, 
    DateTime, 
    ForeignKey, 
    Index,
    Integer, 
    String, 
    Text, 
    UniqueConstraint,
    Computed
)
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import TSVECTOR, ARRAY
from sqlalchemy.orm import Mapped, relationship
# Use regular Text for tests
# from sqlalchemy_utils import TSVectorType

# Add pgvector extension support
try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    # For type checking and development without pgvector
    class Vector:
        """Placeholder for Vector type when pgvector is not available."""
        
        def __init__(self, dimensions: int):
            self.dimensions = dimensions
            
        def __repr__(self) -> str:
            return f"Vector({self.dimensions})"


from mfai_db_repos.lib.database.base import Base


class Repository(Base):
    """Model representing a Git repository."""
    
    # Override table name to match database schema
    __tablename__ = "repositories"

    # Repository information
    url = Column(Text, nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    default_branch = Column(String(255))
    last_commit_hash = Column(String(64))
    last_indexed_at = Column(DateTime(timezone=True))
    file_count = Column(Integer, default=0)
    status = Column(String(50))  # e.g., "cloning", "indexing", "ready", "error"
    clone_path = Column(Text)
    repo_metadata = Column("metadata", JSON)
    
    # Relationships
    files: Mapped[List["RepositoryFile"]] = relationship(
        "RepositoryFile", 
        back_populates="repository",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        """String representation of the Repository."""
        return f"<Repository(name='{self.name}', url='{self.url}')>"


class RepositoryFile(Base):
    """Model representing a file within a Git repository."""
    
    # Override table name to match database schema
    __tablename__ = "repository_files"

    # Repository relationship
    repo_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    repo_url = Column(Text, nullable=False)
    repo_name = Column(Text, nullable=False)
    repo_branch = Column(String(255))
    repo_commit_hash = Column(String(64))
    repo_metadata = Column(JSON)
    
    # File information
    filepath = Column(Text, nullable=False)
    filename = Column(String(255), nullable=False)
    extension = Column(String(50))
    file_size = Column(Integer)
    git_status = Column(String(50))  # e.g., "added", "modified", "deleted"
    
    # Content and embedding columns
    content = Column(Text)
    # Define content_tsvector as a computed column
    content_tsvector = Column(
        TSVECTOR, 
        Computed("to_tsvector('english', coalesce(content, ''))", persisted=True),
        nullable=False
    )
    embedding_string = Column(Text)
    # Use Vector type for embeddings - 1536 dimensions for OpenAI ada-002
    embedding = Column(Vector(1536))
    
    # Metadata
    analysis = Column(JSON)
    tags = Column(ARRAY(Text))
    file_type = Column(String(50))
    technical_level = Column(String(50))
    last_modified = Column(DateTime(timezone=True))
    indexed_at = Column(DateTime(timezone=True), default=datetime.datetime.now)
    
    # Relationships
    repository: Mapped[Repository] = relationship("Repository", back_populates="files")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("repo_url", "filepath", name="uq_repository_file_path"),
        Index("idx_repo_url", "repo_url"),
        Index("idx_filepath", "filepath"),
        Index("idx_file_type", "file_type"),
        # Enable GIN index for tags array column
        Index("idx_repository_files_tags", "tags", postgresql_using="gin"),
        # Enable GIN index for tsvector column
        Index("idx_content_tsvector", "content_tsvector", postgresql_using="gin"),
        # NOTE: We don't add an index on the embedding column directly
        # because of the size limitation in B-tree indexes
        # Instead, we'll create custom indexes for vector search in a separate migration step
    )
    
    def __repr__(self) -> str:
        """String representation of the RepositoryFile."""
        return f"<RepositoryFile(filename='{self.filename}', filepath='{self.filepath}')>"
    
    @property
    def full_path(self) -> Path:
        """Get the full path to the file."""
        if self.repository and self.repository.clone_path and self.filepath:
            return Path(self.repository.clone_path) / self.filepath
        return Path("")