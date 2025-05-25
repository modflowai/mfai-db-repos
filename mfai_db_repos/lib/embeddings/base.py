"""
Base embedding classes and interfaces for GitContext.
Provides abstract base classes for different embedding providers.
"""
import abc
from typing import Any, Dict, List, Optional

import numpy as np
from pydantic import BaseModel


class EmbeddingVector(BaseModel):
    """Representation of an embedding vector with metadata."""
    
    vector: List[float]
    dimensions: int
    model: str
    
    def __init__(self, vector: List[float], model: str):
        """Initialize an embedding vector.
        
        Args:
            vector: The embedding vector as a list of floats
            model: The model used to generate the embedding
        """
        super().__init__(
            vector=vector,
            dimensions=len(vector),
            model=model
        )
    
    def to_numpy(self) -> np.ndarray:
        """Convert the vector to a numpy array."""
        return np.array(self.vector, dtype=np.float32)


class EmbeddingConfig(BaseModel):
    """Configuration for embedding generation."""
    
    model: str
    dimensions: int
    batch_size: int = 20
    max_parallel_requests: int = 5
    retry_attempts: int = 3
    timeout_seconds: int = 30


class EmbeddingProvider(abc.ABC):
    """Abstract base class for embedding providers."""
    
    def __init__(self, config: EmbeddingConfig):
        """Initialize embedding provider with configuration.
        
        Args:
            config: EmbeddingConfig instance with provider settings
        """
        self.config = config
    
    @abc.abstractmethod
    async def embed_text(self, text: str) -> EmbeddingVector:
        """Generate an embedding for a single text input.
        
        Args:
            text: Text to embed
            
        Returns:
            EmbeddingVector with the generated embedding
        """
    
    @abc.abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[EmbeddingVector]:
        """Generate embeddings for a batch of text inputs.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of EmbeddingVector objects
        """
    
    @abc.abstractmethod
    async def embed_file_content(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> EmbeddingVector:
        """Generate an embedding for file content.
        
        Args:
            content: File content to embed
            metadata: Optional metadata about the file
            
        Returns:
            EmbeddingVector with the generated embedding
        """
