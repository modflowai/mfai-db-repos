# PostgreSQL Database Guide

This document provides information about the PostgreSQL database setup for GitContext Python.

## Database Setup

GitContext uses PostgreSQL with the pgvector extension for storing repository data and vector embeddings. The database is configured to run on port 5437 to avoid conflicts with any existing PostgreSQL instances.

### Starting the Database

To start the PostgreSQL database and pgAdmin:

```bash
docker compose up -d
```

This will start:
- PostgreSQL on port 5437
- pgAdmin on port 5050 (accessible at http://localhost:5050)

### Accessing pgAdmin

pgAdmin is a web-based administration tool for PostgreSQL:

1. Open http://localhost:5050 in your browser
2. Login with:
   - Email: admin@gitcontext.local
   - Password: admin

3. Add a new server:
   - In the pgAdmin dashboard, right-click on "Servers" and select "Create" > "Server..."
   - General tab: Name it "GitContext"
   - Connection tab:
     - Host: postgres (the service name in docker-compose)
     - Port: 5432 (the internal port)
     - Maintenance database: gitcontext
     - Username: postgres
     - Password: postgres

### Connecting to PostgreSQL Directly

To connect to the database from the command line:

```bash
# Using psql
psql -h localhost -p 5437 -U postgres -d gitcontext

# Using docker
docker exec -it gitcontext-postgres psql -U postgres -d gitcontext
```

## Database Schema

The database includes the following tables:

### repository_files

Stores information about individual files from repositories:

- **id**: Primary key
- **repo_url**: URL of the repository
- **repo_name**: Name of the repository
- **repo_branch**: Branch name
- **repo_commit_hash**: Latest commit hash
- **repo_metadata**: Additional repository metadata (JSONB)
- **filepath**: Path to the file within the repository
- **filename**: Name of the file
- **extension**: File extension
- **file_size**: Size in bytes
- **last_modified**: Last modification timestamp
- **git_status**: Git status of the file
- **content**: File content
- **content_tsvector**: Text search vector for fast search
- **embedding_string**: String representation of embedding analysis
- **embedding**: Vector embedding (1536 dimensions)
- **analysis**: Additional file analysis (JSONB)
- **tags**: Array of tags
- **file_type**: Type of file
- **technical_level**: Technical complexity level
- **indexed_at**: Timestamp when the file was indexed

### repositories

Tracks repositories that have been indexed:

- **id**: Primary key
- **url**: Repository URL (unique)
- **name**: Repository name
- **default_branch**: Default branch name
- **last_commit_hash**: Latest commit hash
- **last_indexed_at**: Last indexing timestamp
- **file_count**: Number of files indexed
- **status**: Repository status
- **clone_path**: Local path where repository is cloned
- **metadata**: Additional metadata (JSONB)
- **created_at**: Creation timestamp
- **updated_at**: Last update timestamp

## Resetting the Database

If you need to reset the database, you can use the provided script:

```bash
./scripts/reset_db.sh
```

This will:
1. Stop all containers
2. Remove the PostgreSQL and pgAdmin data volumes
3. Start the containers again with a fresh database

## Using pgvector

The database is configured with the pgvector extension which allows for efficient vector similarity searches:

```sql
-- Example: Find similar files based on embeddings
SELECT filepath, filename
FROM repository_files
ORDER BY embedding <-> (SELECT embedding FROM repository_files WHERE id = 123)
LIMIT 10;
```

This example finds the 10 most similar files to the file with ID 123 based on cosine similarity of their vector embeddings.