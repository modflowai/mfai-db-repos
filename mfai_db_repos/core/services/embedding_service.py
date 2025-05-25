"""
Embedding service for coordinating embedding generation and storage.
"""
import asyncio
from typing import List, Optional, Tuple

from mfai_db_repos.core.models.repository import RepositoryFile
from mfai_db_repos.lib.database.repository_file import RepositoryFileRepository
from mfai_db_repos.lib.embeddings.base import EmbeddingVector
from mfai_db_repos.lib.embeddings.manager import EmbeddingManager, ProviderType
from mfai_db_repos.utils.config import Config
from mfai_db_repos.utils.logger import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """Service for generating and managing embeddings for repository files."""
    
    def __init__(
        self,
        config: Config,
        repository_file_repo: RepositoryFileRepository,
        embedding_manager: Optional[EmbeddingManager] = None
    ):
        """Initialize the embedding service.
        
        Args:
            config: Application configuration
            repository_file_repo: Repository file database repository
            embedding_manager: Optional pre-configured embedding manager
        """
        self.config = config
        self.repository_file_repo = repository_file_repo
        
        # Create embedding manager if not provided
        if embedding_manager:
            self.embedding_manager = embedding_manager
        else:
            primary_provider = config.get("embeddings.primary_provider", ProviderType.OPENAI)
            secondary_provider = config.get("embeddings.secondary_provider", None)
            max_parallel = config.get("embeddings.max_parallel_requests", 5)
            batch_size = config.get("embeddings.batch_size", 20)
            rate_limit = config.get("embeddings.rate_limit_per_minute", 100)
            
            self.embedding_manager = EmbeddingManager(
                primary_provider=primary_provider,
                secondary_provider=secondary_provider,
                max_parallel_requests=max_parallel,
                batch_size=batch_size,
                rate_limit_per_minute=rate_limit
            )
    
    async def generate_embedding(self, file: RepositoryFile) -> Optional[EmbeddingVector]:
        """Generate an embedding for a repository file.
        
        Args:
            file: RepositoryFile to generate embedding for
            
        Returns:
            Generated EmbeddingVector or None if generation failed
        """
        if not file.content or file.content.strip() == "":
            logger.warning(f"Cannot generate embedding for empty file: {file.filepath}")
            return None
        
        try:
            # Generate embedding
            embedding = await self.embedding_manager.embed_file_content(
                content=file.content,
                metadata={
                    "path": file.path,
                    "language": file.language,
                    "repository_id": file.repository_id,
                    "commit_hash": file.commit_hash
                }
            )
            
            logger.info(f"Generated embedding for file: {file.path} ({embedding.dimensions} dimensions)")
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding for file {file.path}: {str(e)}")
            return None
    
    async def generate_and_store_embedding(self, file: RepositoryFile) -> bool:
        """Generate and store an embedding for a repository file.
        
        Args:
            file: RepositoryFile to generate and store embedding for
            
        Returns:
            True if successful, False otherwise
        """
        embedding = await self.generate_embedding(file)
        if not embedding:
            return False
        
        try:
            # Update file in the database with the embedding
            file.embedding = embedding.vector
            file.embedding_model = embedding.model
            await self.repository_file_repo.update(file)
            
            # Generate structured analysis if secondary provider is Google GenAI
            if self.embedding_manager.secondary_provider_type == ProviderType.GOOGLE_GENAI:
                try:
                    analysis = await self.embedding_manager.analyze_file_content(file.content)
                    if analysis:
                        file.metadata = {
                            **(file.metadata or {}),
                            "analysis": analysis
                        }
                        await self.repository_file_repo.update(file)
                        logger.info(f"Added structured analysis for file: {file.path}")
                except Exception as e:
                    logger.error(f"Error generating structured analysis for file {file.path}: {str(e)}")
            
            return True
        except Exception as e:
            logger.error(f"Error storing embedding for file {file.path}: {str(e)}")
            return False
    
    async def process_files_batch(
        self, 
        files: List[RepositoryFile],
        show_progress: bool = True
    ) -> Tuple[int, int]:
        """Process a batch of files to generate and store embeddings.
        
        Args:
            files: List of RepositoryFiles to process
            show_progress: Whether to log progress
            
        Returns:
            Tuple of (success_count, failure_count)
        """
        if not files:
            return (0, 0)
        
        total = len(files)
        success_count = 0
        failure_count = 0
        
        # Process in parallel with semaphore to control concurrency
        sem = asyncio.Semaphore(self.embedding_manager.max_parallel_requests)
        
        async def process_file(file, index):
            async with sem:
                result = await self.generate_and_store_embedding(file)
                if show_progress and index % 10 == 0:
                    logger.info(f"Processed {index}/{total} files")
                return result
        
        # Create tasks for all files
        tasks = [process_file(file, i) for i, file in enumerate(files)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count successes and failures
        for result in results:
            if isinstance(result, Exception):
                failure_count += 1
            elif result:
                success_count += 1
            else:
                failure_count += 1
        
        if show_progress:
            logger.info(f"Completed batch processing: {success_count} succeeded, {failure_count} failed")
        
        return (success_count, failure_count)
    
    async def process_repository(
        self,
        repository_id: int,
        limit: Optional[int] = None,
        only_new: bool = True,
        show_progress: bool = True
    ) -> Tuple[int, int]:
        """Process all files in a repository to generate and store embeddings.
        
        Args:
            repository_id: ID of repository to process
            limit: Optional limit on number of files to process
            only_new: Only process files without embeddings
            show_progress: Whether to log progress
            
        Returns:
            Tuple of (success_count, failure_count)
        """
        # Query files without embeddings if only_new is True
        if only_new:
            files = await self.repository_file_repo.get_files_without_embeddings(repository_id, limit)
        else:
            files = await self.repository_file_repo.get_by_repository_id(repository_id, limit)
        
        if not files:
            logger.info(f"No files to process for repository ID {repository_id}")
            return (0, 0)
        
        logger.info(f"Processing {len(files)} files from repository ID {repository_id}")
        
        # Process all files in batches
        batch_size = self.embedding_manager.batch_size
        batches = [files[i:i + batch_size] for i in range(0, len(files), batch_size)]
        
        total_success = 0
        total_failure = 0
        
        for i, batch in enumerate(batches):
            if show_progress:
                logger.info(f"Processing batch {i+1}/{len(batches)}")
            
            success, failure = await self.process_files_batch(batch, show_progress=False)
            total_success += success
            total_failure += failure
        
        if show_progress:
            logger.info(
                f"Completed repository processing: {total_success} succeeded, "
                f"{total_failure} failed, {len(files)} total"
            )
        
        return (total_success, total_failure)