# Vector Similarity Search Implementation

This document outlines the implementation of vector similarity search in GitContext, using PostgreSQL's pgvector extension.

## Overview

Vector similarity search is a key feature for GitContext, allowing users to find code by semantic meaning rather than just keywords. By using vector embeddings generated from code and queries, we can find files that are conceptually similar to a user's query, even if they don't share the exact terminology.

## Implementation Details

### Database Schema

The core of our implementation is the PostgreSQL `pgvector` extension, which adds the `vector` data type and operators for vector similarity. Files are stored in the `repository_files` table, with their vector embeddings in the `embedding` column.

```sql
-- Example schema (simplified)
CREATE TABLE repository_files (
    id SERIAL PRIMARY KEY,
    repo_id INTEGER NOT NULL,
    filepath TEXT NOT NULL,
    filename TEXT NOT NULL,
    content TEXT,
    embedding VECTOR(1536),  -- For OpenAI embeddings
    -- ... other fields
);
```

### Vector Search Query

The basic query for vector similarity search uses the `<=>` operator, which calculates the cosine distance between vectors:

```sql
SELECT 
    id, 
    filename, 
    filepath,
    file_type,
    1 - (embedding <=> '[vector_values]'::vector) as similarity
FROM 
    repository_files
ORDER BY 
    (embedding <=> '[vector_values]'::vector)  -- Parentheses are important!
LIMIT 5
```

Here, `1 - (embedding <=> vector)` gives us the cosine similarity, where 1 is identical and 0 is completely dissimilar.

### Implementation Approaches

GitContext offers both ORM-based and direct SQL implementations:

#### 1. ORM-Based Implementation (RepositoryFileRepository)

The `similarity_search` method in `RepositoryFileRepository` implements vector search using SQLAlchemy:

```python
async def similarity_search(
    self,
    repository_id: int,
    embedding: Union[List[float], np.ndarray],
    limit: int = 10,
    threshold: float = 0.7
):
    # Convert embedding to list
    embedding_list = list(embedding) if not isinstance(embedding, np.ndarray) else embedding.tolist()
    
    # Format as PostgreSQL vector literal
    vector_str = '[' + ','.join(str(x) for x in embedding_list) + ']'
    
    # Build SQL query with direct embedding string
    query_parts = [
        "SELECT rf.*, 1 - (rf.embedding::vector <=> '{vector_str}'::vector) AS similarity",
        "FROM repository_files rf",
        f"WHERE rf.repo_id = {repository_id}",
        "AND rf.embedding IS NOT NULL"
    ]
    
    # Add ordering and limit
    query_parts.append(f"ORDER BY (rf.embedding::vector <=> '{vector_str}'::vector)")  # Order by distance (lower is better)
    query_parts.append(f"LIMIT {limit}")
    
    # Execute the query
    result = await self.session.execute(text(" ".join(query_parts)))
    # Process results...
```

#### 2. Direct SQL Implementation

For more reliable results, GitContext also offers a direct SQL implementation:

```python
def vector_search(repository_id: int, query_embedding: List[float], limit: int = 10):
    # Connect directly to PostgreSQL
    conn = psycopg2.connect(**conn_params)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Format embedding as vector string
    embedding_str = '[' + ','.join(str(x) for x in query_embedding) + ']'
    
    # Build and execute the query
    query = """
        SELECT 
            id, repo_id, filepath, filename,
            1 - (embedding::vector <=> %s::vector) as similarity
        FROM 
            repository_files
        WHERE
            repo_id = %s
            AND embedding IS NOT NULL
        ORDER BY 
            (embedding::vector <=> %s::vector)
        LIMIT %s
    """
    
    cursor.execute(query, (embedding_str, repository_id, embedding_str, limit))
    results = cursor.fetchall()
    
    return results
```

### Best Practices and Lessons Learned

1. **Proper Vector Formatting**: When working with pgvector, vector literals must be formatted as PostgreSQL arrays: `'[0.1, 0.2, 0.3, ...]'::vector`.

2. **Parameter Binding Issues**: SQLAlchemy's parameter binding with asyncpg doesn't directly support vector types. The solution is to:
   - Format the vector as a proper PostgreSQL array string before binding
   - Use explicit type casts in the SQL query (`::vector`)
   - Add parentheses in ORDER BY clauses: `ORDER BY (embedding <=> vector)`, not `ORDER BY embedding <=> vector`

3. **Transaction Management**: Proper transaction handling is essential, especially when queries fail:
   - Always roll back transactions on error
   - Use autocommit mode when feasible
   - Be cautious with multiple operations in a single transaction

4. **Performance Optimization**:
   - Consider using IVFFLAT indexes for large collections: `CREATE INDEX ON repository_files USING ivfflat (embedding vector_cosine_ops);`
   - Filter queries to a specific repository before applying vector search
   - Use appropriate thresholds to balance recall and precision

### Multiple Search Methods

GitContext now supports three search methods:

1. **Vector Search**: Pure semantic search using vector embeddings
2. **Text Search**: Traditional text-based search with ILIKE
3. **Hybrid Search**: Combines vector and text search results with configurable weights

## CLI Integration

GitContext offers CLI commands for vector searching:

```bash
# Vector search (default method)
gitcontext search vector -r 2 -q "How do I install this library?"

# Text search
gitcontext search vector --method text -r 2 -q "installation guide"

# Hybrid search with custom weights
gitcontext search vector --method hybrid -r 2 -q "configure database" --vector-weight 0.8
```

## Example Usage

```python
# Example of using the vector search functionality
async def search_by_concept(repo_id: int, query: str):
    # Generate embedding for the query
    embedding = await generate_embedding(query)
    
    # Search for similar files
    similar_files = vector_search(
        repository_id=repo_id,
        query_embedding=embedding,
        limit=10,
        threshold=0.6,
        filter_extension="py"  # Optional: filter by extension
    )
    
    # Process results
    for result in similar_files:
        print(f"{result['filename']}: {result['similarity']:.2f}")
```

## Future Improvements

1. **Vector Quantization**: Optimize storage and query performance for large repositories
2. **Batch Processing**: Improve embedding generation for large codebases
3. **Custom Embeddings**: Fine-tune embeddings specifically for code/programming languages
4. **Improved Error Handling**: More graceful fallbacks when vector search fails
5. **Relevance Feedback**: Allow users to provide feedback on search results