#!/usr/bin/env python3
"""
Test script for vector similarity search.
"""
import asyncio
import os
from typing import List, Tuple

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from gitcontext.lib.database.connection import session_context
from gitcontext.lib.database.models import RepositoryFile
from gitcontext.lib.database.repository_file import RepositoryFileRepository
from gitcontext.lib.embeddings.manager import EmbeddingManager
from gitcontext.lib.embeddings.openai import OpenAIEmbeddingConfig
from gitcontext.utils.env import load_env


async def test_similarity_search(query: str, repo_id: int = 1, limit: int = 5):
    """
    Test vector similarity search using a text query.
    
    Args:
        query: Text query to search for
        repo_id: Repository ID to search
        limit: Maximum number of results to return
    """
    print(f"Searching for: {query}")
    
    # Load environment variables
    env_vars = load_env()
    
    # Create embedding manager for generating query embedding
    openai_config = OpenAIEmbeddingConfig(
        api_key=os.environ.get("OPENAI_API_KEY"),
        model="text-embedding-3-small",
        batch_size=1,
        max_parallel_requests=1
    )
    # Initialize embedding manager with correct parameters
    manager = EmbeddingManager(
        primary_provider="openai",
        primary_config=openai_config,
        max_parallel_requests=1,
        batch_size=1,
        rate_limit_per_minute=100
    )
    
    # Get embedding for query
    query_embedding = await manager.embed_text(query)
    embedding_vector = query_embedding.vector
    
    # Perform similarity search
    async with session_context() as session:
        file_repo = RepositoryFileRepository(session)
        results = await file_repo.similarity_search(
            repository_id=repo_id,
            embedding=embedding_vector,
            limit=limit,
            threshold=0.7  # Adjust threshold as needed
        )
        
        print(f"\nFound {len(results)} results:")
        for i, (file, similarity) in enumerate(results, 1):
            print(f"{i}. {file.filename} (Score: {similarity:.4f})")
            print(f"   - Type: {file.file_type}")
            print(f"   - Technical Level: {file.technical_level}")
            print(f"   - Path: {file.filepath}")
            print()


if __name__ == "__main__":
    # Test queries
    queries = [
        "How do I contribute to this project?",
        "What is the licensing of this code?",
        "How do I set up a development environment?",
        "What are the code of conduct rules?",
        "How do I install FloPy?"
    ]
    
    for query in queries:
        asyncio.run(test_similarity_search(query))
        print("-" * 80)