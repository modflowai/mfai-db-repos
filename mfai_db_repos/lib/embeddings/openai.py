"""
OpenAI embedding provider implementation.
Uses the OpenAI API to generate text embeddings.
"""
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI

from mfai_db_repos.lib.embeddings.base import EmbeddingConfig, EmbeddingProvider, EmbeddingVector
from mfai_db_repos.utils.logger import get_logger

logger = get_logger(__name__)


class OpenAIEmbeddingConfig(EmbeddingConfig):
    """Configuration for OpenAI embedding API."""
    
    model: str = "text-embedding-ada-002"
    dimensions: int = 1536
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    organization: Optional[str] = None
    max_retries: int = 3
    request_timeout: float = 30.0


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI API implementation of embedding provider."""
    
    def __init__(self, config: OpenAIEmbeddingConfig):
        """Initialize OpenAI embedding provider with configuration.
        
        Args:
            config: OpenAIEmbeddingConfig instance with provider settings
        """
        super().__init__(config)
        self.config = config
        self.client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.api_base,
            organization=config.organization,
            timeout=config.request_timeout,
            max_retries=config.max_retries
        )
        logger.info(f"Initialized OpenAI embedding provider with model: {config.model}")
    
    async def embed_text(self, text: str) -> EmbeddingVector:
        """Generate an embedding for a single text input.
        
        Args:
            text: Text to embed
            
        Returns:
            EmbeddingVector with the generated embedding
        """
        try:
            response = await self.client.embeddings.create(
                model=self.config.model,
                input=text
            )
            return EmbeddingVector(
                vector=response.data[0].embedding,
                model=self.config.model
            )
        except Exception as e:
            logger.error(f"Error generating OpenAI embedding: {str(e)}")
            raise
    
    async def embed_batch(self, texts: List[str]) -> List[EmbeddingVector]:
        """Generate embeddings for a batch of text inputs.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of EmbeddingVector objects
        """
        if not texts:
            return []
        
        try:
            response = await self.client.embeddings.create(
                model=self.config.model,
                input=texts
            )
            
            # Sort embeddings by their index to maintain original order
            sorted_data = sorted(response.data, key=lambda x: x.index)
            
            return [
                EmbeddingVector(
                    vector=item.embedding,
                    model=self.config.model
                )
                for item in sorted_data
            ]
        except Exception as e:
            logger.error(f"Error generating batch OpenAI embeddings: {str(e)}")
            raise
    
    async def embed_file_content(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> EmbeddingVector:
        """Generate an embedding for file content.
        
        Args:
            content: File content to embed
            metadata: Optional metadata about the file
            
        Returns:
            EmbeddingVector with the generated embedding
        """
        # For OpenAI, we simply embed the content directly
        # Truncate content if it's too long (OpenAI has token limits)
        max_chars = 60000  # Approximate limit to stay within token limits
        if len(content) > max_chars:
            logger.warning(f"File content truncated from {len(content)} to {max_chars} characters for embedding")
            content = content[:max_chars]
            
        return await self.embed_text(content)