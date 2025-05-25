#!/usr/bin/env python3
"""
Test the vector similarity search functionality of the RepositoryFileRepository.
"""
import asyncio
import os
import sys
from typing import List, Optional

from gitcontext.lib.database.connection import session_context
from gitcontext.lib.database.repository_file import RepositoryFileRepository
from gitcontext.lib.embeddings.manager import EmbeddingManager
from gitcontext.lib.embeddings.openai import OpenAIEmbeddingConfig
from gitcontext.utils.env import load_env
from gitcontext.utils.logger import get_logger

logger = get_logger(__name__)

async def test_similarity_search(
    query_text: str, 
    repository_id: int = 1,
    limit: int = 5,
    threshold: float = 0.1,
    filter_extension: Optional[str] = None,
    filter_file_type: Optional[str] = None
):
    """
    Test the similarity search functionality.
    
    Args:
        query_text: Text to search for
        repository_id: Repository ID to search in
        limit: Maximum number of results to return
        threshold: Minimum similarity threshold (0-1, higher is more similar)
        filter_extension: Optional filter by file extension
        filter_file_type: Optional filter by file type
    """
    # Load environment variables
    env_vars = load_env()
    
    # Create embedding manager
    openai_config = OpenAIEmbeddingConfig(
        api_key=os.environ.get("OPENAI_API_KEY"),
        model="text-embedding-3-small",
        batch_size=1,
        max_parallel_requests=1
    )
    
    manager = EmbeddingManager(
        primary_provider="openai",
        primary_config=openai_config,
        max_parallel_requests=1,
        batch_size=1,
        rate_limit_per_minute=100
    )
    
    # Generate embedding for query
    logger.info(f"Generating embedding for query: {query_text}")
    query_embedding = await manager.embed_text(query_text)
    
    # Get a session context for database operations
    async with session_context() as session:
        # Create repository file repository
        repo_file_repo = RepositoryFileRepository(session)
        
        # First, get a count of files in the repository
        file_count = await repo_file_repo.count_by_repository_id(repository_id)
        logger.info(f"Repository {repository_id} has {file_count} files")
        
        # Get files without embeddings
        files_without_embeddings = await repo_file_repo.count_files_without_embeddings(repository_id)
        logger.info(f"Repository {repository_id} has {files_without_embeddings} files without embeddings")
        
        # Get embedding model counts
        embedding_models = await repo_file_repo.get_embedding_model_counts(repository_id)
        logger.info(f"Embedding models in repository {repository_id}: {embedding_models}")
        
        # Perform similarity search
        logger.info(f"Performing similarity search for query: {query_text}")
        logger.info(f"Repository ID: {repository_id}, Limit: {limit}, Threshold: {threshold}")
        if filter_extension:
            logger.info(f"Filter by extension: {filter_extension}")
        if filter_file_type:
            logger.info(f"Filter by file type: {filter_file_type}")
            
        # Check if vectors are in the right format
        logger.info(f"Vector type: {type(query_embedding.vector)}")
        logger.info(f"Vector sample: {str(query_embedding.vector[:5])}")
            
        similar_files = await repo_file_repo.similarity_search(
            repository_id=repository_id,
            embedding=query_embedding.vector,
            limit=limit,
            threshold=threshold,
            filter_extension=filter_extension,
            filter_file_type=filter_file_type
        )
        
        # Print results
        logger.info(f"Found {len(similar_files)} similar files:")
        for i, (file, similarity) in enumerate(similar_files, 1):
            logger.info(f"{i}. {file.filename} (Score: {similarity:.4f})")
            logger.info(f"   - Type: {file.file_type or 'N/A'}")
            logger.info(f"   - Technical Level: {file.technical_level or 'N/A'}")
            logger.info(f"   - Path: {file.filepath}")
            logger.info("")

if __name__ == "__main__":
    # Set up command line arguments
    query = "How do I contribute to this project?"
    repo_id = 1
    limit = 5
    threshold = 0.01  # Use a much lower threshold to match more documents
    extension = None
    file_type = None
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        query = sys.argv[1]
    if len(sys.argv) > 2:
        repo_id = int(sys.argv[2])
    if len(sys.argv) > 3:
        limit = int(sys.argv[3])
    if len(sys.argv) > 4:
        threshold = float(sys.argv[4])
    if len(sys.argv) > 5:
        extension = sys.argv[5]
    if len(sys.argv) > 6:
        file_type = sys.argv[6]
        
    # Run the test
    asyncio.run(test_similarity_search(
        query_text=query,
        repository_id=repo_id,
        limit=limit,
        threshold=threshold,
        filter_extension=extension,
        filter_file_type=file_type
    ))