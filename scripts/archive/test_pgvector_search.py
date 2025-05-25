#!/usr/bin/env python3
"""
Test script for vector similarity search using direct PostgreSQL connection.
"""
import os
import sys
import asyncio
import psycopg2
import numpy as np

from gitcontext.lib.embeddings.manager import EmbeddingManager
from gitcontext.lib.embeddings.openai import OpenAIEmbeddingConfig
from gitcontext.utils.env import load_env


def test_pgvector_search(query_text: str, limit: int = 5):
    """
    Test vector similarity search using direct psycopg2 connection.
    
    Args:
        query_text: Text query to search for
        limit: Maximum number of results to return
    """
    print(f"Searching for: {query_text}")
    
    # Load environment variables
    env_vars = load_env()
    
    # Database connection details
    db_config = {
        "user": "postgres",
        "password": "postgres",
        "host": "localhost",
        "port": "5437",
        "database": "gitcontext"
    }
    
    # Create embedding for the query
    try:
        embedding = generate_embedding(query_text)
        print(f"Generated embedding with {len(embedding)} dimensions")
        
        # Connect to the database
        conn = psycopg2.connect(
            user=db_config["user"],
            password=db_config["password"],
            host=db_config["host"],
            port=db_config["port"],
            database=db_config["database"]
        )
        
        try:
            # Create a cursor
            cursor = conn.cursor()
            
            # Check pgvector extension
            cursor.execute("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')")
            pgvector_available = cursor.fetchone()[0]
            
            if pgvector_available:
                print("pgvector extension is available")
            else:
                print("Warning: pgvector extension is not installed")
                return
            
            # Check for repository files
            cursor.execute("SELECT COUNT(*) FROM repository_files")
            count = cursor.fetchone()[0]
            print(f"Found {count} files in the database")
            
            if count == 0:
                print("No files found in the repository_files table")
                return
            
            # Try a sample query to check the database
            cursor.execute("SELECT id, filename FROM repository_files LIMIT 10")
            samples = cursor.fetchall()
            print(f"Files in database:")
            for sample in samples:
                print(f"ID: {sample[0]}, Filename: {sample[1]}")
            
            # Check embedding column format and content
            cursor.execute("SELECT id, embedding FROM repository_files LIMIT 1")
            sample_id, sample_embedding = cursor.fetchone()
            if sample_embedding is None:
                print(f"Warning: Sample embedding is NULL for file ID {sample_id}")
            else:
                print(f"Sample embedding type: {type(sample_embedding)}")
                
                # Check dimensions
                try:
                    cursor.execute("SELECT array_length(embedding, 1) FROM repository_files WHERE id = %s", (sample_id,))
                    dims = cursor.fetchone()[0]
                    print(f"Embedding dimensions: {dims}")
                except Exception as e:
                    print(f"Couldn't get embedding dimensions: {e}")
                
                # Try examining the vector values
                try:
                    if hasattr(sample_embedding, '__getitem__'):
                        print(f"Sample embedding (start): {sample_embedding[:20]}")
                    else:
                        print(f"Sample embedding value/format: {sample_embedding}")
                except Exception as e:
                    print(f"Couldn't access embedding values: {e}")
                    
            # Check if the vectors are valid and comparable
            try:
                cursor.execute("SELECT 1 - (embedding <=> embedding) as similarity FROM repository_files LIMIT 1")
                self_similarity = cursor.fetchone()[0]
                print(f"Self-similarity test: {self_similarity}")
            except Exception as e:
                print(f"Self-similarity test failed: {e}")
                    
            # Format embedding vector for PostgreSQL
            vector_array = embedding
            
            try:
                # Use direct SQL with the vector literal formatted as per pgvector docs
                # The PostgreSQL vector type requires a specific syntax
                vector_literal = "'" + str(vector_array).replace('[', '[').replace(']', ']') + "'"
                
                query_sql = f"""
                    SELECT 
                        id, 
                        filename, 
                        filepath,
                        file_type,
                        technical_level,
                        1 - (embedding <=> {vector_literal}::vector) as similarity
                    FROM 
                        repository_files
                    ORDER BY 
                        embedding <=> {vector_literal}::vector
                    LIMIT {limit}
                """
                
                print("\nExecuting vector search query...")
                cursor.execute(query_sql)
                
                similar_files = cursor.fetchall()
                
                print(f"\nFound {len(similar_files)} similar files:")
                for i, file in enumerate(similar_files, 1):
                    id, name, path, ftype, tech_level, similarity = file
                    print(f"{i}. {name} (Score: {similarity:.4f})")
                    print(f"   - Type: {ftype if ftype else 'N/A'}")
                    print(f"   - Technical Level: {tech_level if tech_level else 'N/A'}")
                    print(f"   - Path: {path}")
                    print()
                    
                # If no results, we won't need a second attempt since we removed the filter
                    
            except Exception as e:
                print(f"Error executing vector search: {str(e)}")
                conn.rollback()  # Rollback the transaction on error
                    
        finally:
            # Close the cursor and connection
            conn.close()
            
    except Exception as e:
        print(f"Error in vector search: {str(e)}")
        import traceback
        traceback.print_exc()


def generate_embedding(text: str) -> list:
    """
    Generates embedding vector for the given text.
    
    Args:
        text: Text to generate embedding for
        
    Returns:
        List of floating-point values representing the embedding vector
    """
    # Create an async function to use the async EmbeddingManager
    async def get_embedding():
        # Create embedding manager for generating query embedding
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
        
        query_embedding = await manager.embed_text(text)
        embedding_vector = query_embedding.vector
        
        # Convert to list if it's a numpy array
        if isinstance(embedding_vector, np.ndarray):
            embedding_vector = embedding_vector.tolist()
            
        return embedding_vector
    
    # Run the async function in the event loop
    return asyncio.run(get_embedding())


if __name__ == "__main__":
    query = "How do I contribute to this project?"
    if len(sys.argv) > 1:
        query = sys.argv[1]
    
    test_pgvector_search(query)