#!/usr/bin/env python3
"""
Test script for direct vector similarity search using SQL.
"""
import asyncio
import os
import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from gitcontext.utils.env import load_env


async def test_direct_vector_search():
    """Test vector search using direct SQL queries."""
    # Load environment variables
    env_vars = load_env()
    
    # Create database connection
    db_config = {
        "user": "postgres",
        "password": "postgres",
        "host": "localhost",
        "port": "5437",
        "database": "gitcontext"
    }
    
    connection_url = f"postgresql+asyncpg://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"
    engine = create_async_engine(connection_url, echo=True)
    
    async with AsyncSession(engine) as session:
        # Check if the database has any files
        result = await session.execute(text("SELECT COUNT(*) FROM repository_files"))
        count = result.scalar()
        print(f"Found {count} files in the database")
        
        if count == 0:
            print("No files found, please add some files first")
            return
        
        # Check if pgvector extension is installed
        result = await session.execute(text("SELECT * FROM pg_extension WHERE extname='vector'"))
        pgvector = result.first()
        if not pgvector:
            print("pgvector extension is not installed")
            return
        print("pgvector extension is installed")
        
        # Get a random file embedding as a test query vector
        # In a real search, this would be the embedding of the user's query
        result = await session.execute(text("SELECT id, filename, embedding FROM repository_files LIMIT 1"))
        row = result.first()
        if not row:
            print("No files with embeddings found")
            return
        
        file_id, filename, query_vector = row
        print(f"Using '{filename}' (ID: {file_id}) as query vector")
        
        # Find similar files using cosine_distance from pgvector
        # Lower distance means higher similarity (more similar)
        # Use direct SQL query to verify pgvector functionality
        sql = """
        SELECT 
            id, 
            filename, 
            filepath,
            file_type,
            technical_level,
            1 - (embedding <=> embedding) as similarity
        FROM 
            repository_files
        ORDER BY 
            id
        LIMIT 5
        """
        
        result = await session.execute(text(sql))
        similar_files = result.fetchall()
        
        print(f"\nFound {len(similar_files)} similar files:")
        for i, (id, name, path, ftype, tech_level, similarity) in enumerate(similar_files, 1):
            print(f"{i}. {name} (Score: {similarity:.4f})")
            print(f"   - Type: {ftype}")
            print(f"   - Technical Level: {tech_level}")
            print(f"   - Path: {path}")
            print()


if __name__ == "__main__":
    asyncio.run(test_direct_vector_search())