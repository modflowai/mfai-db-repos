"""
Embedding manager for coordinating embedding generation across providers.
Handles batching, parallel processing, and rate limiting.
"""
import asyncio
import time
from typing import Any, Dict, List, Optional

from mfai_db_repos.lib.embeddings.base import EmbeddingConfig, EmbeddingProvider, EmbeddingVector
from mfai_db_repos.lib.embeddings.google_genai import GoogleGenAIEmbeddingConfig, GoogleGenAIEmbeddingProvider
from mfai_db_repos.lib.embeddings.openai import OpenAIEmbeddingConfig, OpenAIEmbeddingProvider
from mfai_db_repos.utils.logger import get_logger

logger = get_logger(__name__)


class ProviderType:
    """Enum-like constants for embedding provider types."""
    
    OPENAI = "openai"
    GOOGLE_GENAI = "google_genai"


class EmbeddingManager:
    """Manages embedding generation across different providers."""
    
    def __init__(
        self,
        primary_provider: str = ProviderType.OPENAI,
        secondary_provider: Optional[str] = None,
        primary_config: Optional[EmbeddingConfig] = None,
        secondary_config: Optional[EmbeddingConfig] = None,
        max_parallel_requests: int = 5,
        batch_size: int = 20,
        rate_limit_per_minute: int = 100,
    ):
        """Initialize the embedding manager.
        
        Args:
            primary_provider: Type of primary embedding provider
            secondary_provider: Optional type of secondary embedding provider
            primary_config: Configuration for primary provider
            secondary_config: Configuration for secondary provider
            max_parallel_requests: Maximum number of parallel API requests
            batch_size: Number of texts to batch into a single API request
            rate_limit_per_minute: Maximum number of API requests per minute
        """
        self.max_parallel_requests = max_parallel_requests
        self.batch_size = batch_size
        self.rate_limit_per_minute = rate_limit_per_minute
        self.request_count = 0
        self.last_reset = time.time()
        
        # Set up the primary provider
        self.primary_provider_type = primary_provider
        self.primary_provider = self._create_provider(primary_provider, primary_config)
        
        # Set up the secondary provider if specified
        self.secondary_provider_type = secondary_provider
        self.secondary_provider = None
        if secondary_provider:
            self.secondary_provider = self._create_provider(secondary_provider, secondary_config)
        
        logger.info(f"Initialized embedding manager with primary provider: {primary_provider}")
        if secondary_provider:
            logger.info(f"Secondary embedding provider: {secondary_provider}")
    
    def _create_provider(self, provider_type: str, config: Optional[EmbeddingConfig] = None) -> EmbeddingProvider:
        """Create an embedding provider instance based on type.
        
        Args:
            provider_type: Type of provider to create
            config: Optional configuration for provider
            
        Returns:
            Configured EmbeddingProvider instance
            
        Raises:
            ValueError: If provider type is unsupported
        """
        if provider_type == ProviderType.OPENAI:
            if config is None or not isinstance(config, OpenAIEmbeddingConfig):
                config = OpenAIEmbeddingConfig(
                    batch_size=self.batch_size,
                    max_parallel_requests=self.max_parallel_requests
                )
            return OpenAIEmbeddingProvider(config)
        
        elif provider_type == ProviderType.GOOGLE_GENAI:
            if config is None or not isinstance(config, GoogleGenAIEmbeddingConfig):
                config = GoogleGenAIEmbeddingConfig(
                    batch_size=self.batch_size,
                    max_parallel_requests=self.max_parallel_requests
                )
            return GoogleGenAIEmbeddingProvider(config)
        
        else:
            raise ValueError(f"Unsupported embedding provider type: {provider_type}")
    
    async def _check_rate_limit(self):
        """Check and enforce rate limiting.
        
        Implements a simple token bucket rate limiter.
        """
        current_time = time.time()
        time_passed = current_time - self.last_reset
        
        # Reset counter if a minute has passed
        if time_passed > 60:
            self.request_count = 0
            self.last_reset = current_time
            return
        
        # Check if we've hit the rate limit
        if self.request_count >= self.rate_limit_per_minute:
            # Calculate sleep time needed to respect rate limit
            sleep_time = 60 - time_passed
            logger.warning(f"Rate limit reached, sleeping for {sleep_time:.2f} seconds")
            await asyncio.sleep(sleep_time)
            self.request_count = 0
            self.last_reset = time.time()
    
    async def embed_text(self, text: str, use_secondary: bool = False) -> EmbeddingVector:
        """Generate an embedding for a single text input.
        
        Args:
            text: Text to embed
            use_secondary: Whether to use the secondary provider
            
        Returns:
            EmbeddingVector with the generated embedding
        """
        await self._check_rate_limit()
        self.request_count += 1
        
        provider = self.secondary_provider if use_secondary and self.secondary_provider else self.primary_provider
        return await provider.embed_text(text)
    
    async def embed_batch(self, texts: List[str], use_secondary: bool = False) -> List[EmbeddingVector]:
        """Generate embeddings for a batch of text inputs.
        
        Args:
            texts: List of texts to embed
            use_secondary: Whether to use the secondary provider
            
        Returns:
            List of EmbeddingVector objects
        """
        if not texts:
            return []
        
        await self._check_rate_limit()
        self.request_count += 1
        
        provider = self.secondary_provider if use_secondary and self.secondary_provider else self.primary_provider
        return await provider.embed_batch(texts)
    
    async def embed_texts_parallel(self, texts: List[str], use_secondary: bool = False) -> List[EmbeddingVector]:
        """Generate embeddings for multiple texts in parallel batches.
        
        Args:
            texts: List of texts to embed
            use_secondary: Whether to use the secondary provider
            
        Returns:
            List of EmbeddingVector objects in the same order as input texts
        """
        if not texts:
            return []
        
        # Prepare batches
        batches = [texts[i:i + self.batch_size] for i in range(0, len(texts), self.batch_size)]
        logger.info(f"Processing {len(texts)} texts in {len(batches)} batches")
        
        # Process batches with concurrency limit
        semaphore = asyncio.Semaphore(self.max_parallel_requests)
        provider = self.secondary_provider if use_secondary and self.secondary_provider else self.primary_provider
        
        async def process_batch(batch):
            async with semaphore:
                await self._check_rate_limit()
                self.request_count += 1
                return await provider.embed_batch(batch)
        
        # Process all batches and gather results
        tasks = [process_batch(batch) for batch in batches]
        batch_results = await asyncio.gather(*tasks)
        
        # Flatten results
        results = []
        for batch_result in batch_results:
            results.extend(batch_result)
        
        return results
    
    async def embed_file_content(
        self, 
        content: str, 
        metadata: Optional[Dict[str, Any]] = None,
        use_secondary: bool = False
    ) -> EmbeddingVector:
        """Generate an embedding for file content.
        
        Args:
            content: File content to embed
            metadata: Optional metadata about the file
            use_secondary: Whether to use the secondary provider
            
        Returns:
            EmbeddingVector with the generated embedding
        """
        await self._check_rate_limit()
        self.request_count += 1
        
        provider = self.secondary_provider if use_secondary and self.secondary_provider else self.primary_provider
        return await provider.embed_file_content(content, metadata)
    
    async def analyze_file_content(self, content: str, readme_content: Optional[str] = None) -> Dict[str, Any]:
        """Generate a structured analysis of file content using Gemini model if available.
        
        Args:
            content: File content to analyze
            readme_content: Optional README content to provide context
            
        Returns:
            Dictionary containing structured analysis of the content
        """
        # Only use Google GenAI provider for structured analysis
        provider = None
        if self.primary_provider_type == ProviderType.GOOGLE_GENAI:
            provider = self.primary_provider
        elif self.secondary_provider_type == ProviderType.GOOGLE_GENAI:
            provider = self.secondary_provider
        
        if provider and isinstance(provider, GoogleGenAIEmbeddingProvider):
            await self._check_rate_limit()
            self.request_count += 1
            
            analysis = await provider.generate_structured_analysis(content, readme_content)
            return analysis.model_dump()
        else:
            logger.warning("Structured analysis requested but no Google GenAI provider available")
            return {
                "title": "No analysis available",
                "summary": "Google GenAI provider not configured for structured analysis",
                "key_concepts": [],
                "keywords": []
            }