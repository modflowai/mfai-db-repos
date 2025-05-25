#!/usr/bin/env python3
"""
Simple direct test of vector search using psycopg2.
"""
import psycopg2
import sys

def test_direct_vector():
    """Simplified test for vector search."""
    
    # Database connection details
    db_config = {
        "user": "postgres",
        "password": "postgres",
        "host": "localhost",
        "port": "5437",
        "database": "gitcontext"
    }
    
    # Connect to the database
    conn = psycopg2.connect(
        user=db_config["user"],
        password=db_config["password"],
        host=db_config["host"],
        port=db_config["port"],
        database=db_config["database"]
    )
    
    # Create a cursor and enable autocommit to avoid transaction issues
    conn.autocommit = True
    cursor = conn.cursor()
    
    try:
        # Check pgvector extension
        cursor.execute("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')")
        pgvector_available = cursor.fetchone()[0]
        print(f"pgvector extension available: {pgvector_available}")
        
        # Check vector operators
        cursor.execute("SELECT proname FROM pg_proc WHERE proname = '<==>'")
        ops = cursor.fetchall()
        print(f"Vector operators: {ops}")
        
        # Get file info from database
        cursor.execute("SELECT id, filename FROM repository_files")
        files = cursor.fetchall()
        print("Files in database:")
        for file_id, filename in files:
            print(f"ID: {file_id}, Filename: {filename}")
            
        # Check the database structure
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'repository_files'
        """)
        columns = cursor.fetchall()
        print("\nTable structure:")
        for col, dtype in columns:
            print(f"{col}: {dtype}")
        
        # Try a self-similarity test with one vector
        try:
            cursor.execute("""
                SELECT id, filename, 
                       1 - (embedding <=> embedding) as similarity
                FROM repository_files
                LIMIT 1
            """)
            result = cursor.fetchone()
            print(f"\nSelf-similarity test: {result}")
        except Exception as e:
            print(f"Self-similarity test failed: {e}")
            
        # Try a simple search with a constant vector
        try:
            # Use a simple vector (all zeros with 1536 dimensions)
            # This is just to test if the search works at all
            test_vector = "[" + ",".join(["0"] * 1536) + "]"
            
            cursor.execute(f"""
                SELECT id, filename, 
                       1 - (embedding <=> '{test_vector}'::vector) as similarity
                FROM repository_files
                ORDER BY embedding <=> '{test_vector}'::vector
                LIMIT 5
            """)
            
            results = cursor.fetchall()
            print(f"\nTest vector search results:")
            for file_id, filename, similarity in results:
                print(f"ID: {file_id}, Filename: {filename}, Similarity: {similarity:.4f}")
        except Exception as e:
            print(f"Test vector search failed: {e}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cursor.close()
        conn.close()
        
if __name__ == "__main__":
    test_direct_vector()