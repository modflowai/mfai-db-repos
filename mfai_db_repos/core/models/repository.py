"""
Repository core models.

These models represent the core business logic models for repositories and files,
abstracted from the database implementation details.
"""
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RepositoryFile(BaseModel):
    """Core model representing a file in a repository."""
    
    id: Optional[int] = None
    repository_id: int = Field(alias="repo_id")
    path: str = Field(alias="filepath")
    name: str = Field(alias="filename")
    extension: Optional[str] = None
    size: Optional[int] = Field(default=None, alias="file_size")
    language: Optional[str] = Field(default=None, alias="file_type")
    content: Optional[str] = None
    embedding: Optional[List[float]] = None
    embedding_model: Optional[str] = None
    commit_hash: Optional[str] = Field(default=None, alias="repo_commit_hash")
    last_modified: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = Field(default=None, alias="repo_metadata")
    
    class Config:
        """Pydantic model configuration."""
        arbitrary_types_allowed = True


class Repository(BaseModel):
    """Core model representing a Git repository."""
    
    id: Optional[int] = None
    url: str
    name: str
    clone_path: Optional[Path] = None
    default_branch: str = "main"
    last_commit_hash: Optional[str] = None
    last_indexed_at: Optional[datetime] = None
    file_count: int = 0
    status: str = "created"
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        """Pydantic model configuration."""
        arbitrary_types_allowed = True