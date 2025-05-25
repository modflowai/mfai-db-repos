#!/bin/bash
# Script to reinitialize the database schema

echo "Dropping existing tables..."
docker exec gitcontext-postgres psql -U postgres -d gitcontext -c "DROP TABLE IF EXISTS test;"
docker exec gitcontext-postgres psql -U postgres -d gitcontext -c "DROP TABLE IF EXISTS repository_files CASCADE;"
docker exec gitcontext-postgres psql -U postgres -d gitcontext -c "DROP TABLE IF EXISTS repositories CASCADE;"

echo "Creating vector extension..."
docker exec gitcontext-postgres psql -U postgres -d gitcontext -c "CREATE EXTENSION IF NOT EXISTS vector;"

echo "Creating repository_files table..."
docker exec gitcontext-postgres psql -U postgres -d gitcontext -c "
CREATE TABLE IF NOT EXISTS repository_files (
    id SERIAL PRIMARY KEY,
    -- Repository information
    repo_url TEXT NOT NULL,
    repo_name TEXT NOT NULL,
    repo_branch TEXT,
    repo_commit_hash TEXT,
    repo_metadata JSONB,
    -- File information
    filepath TEXT NOT NULL,
    filename TEXT NOT NULL,
    extension TEXT,
    file_size INTEGER,
    git_status TEXT,
    -- Content and embedding columns
    content TEXT,
    content_tsvector TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', coalesce(content, ''))) STORED,
    embedding_string TEXT,
    embedding VECTOR(1536),
    -- Metadata
    analysis JSONB,
    tags TEXT[],
    file_type TEXT,
    technical_level TEXT,
    last_modified TIMESTAMP WITH TIME ZONE,
    indexed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    -- Constraints
    CONSTRAINT unique_file UNIQUE (repo_url, filepath)
);"

echo "Creating indexes for repository_files..."
docker exec gitcontext-postgres psql -U postgres -d gitcontext -c "CREATE INDEX IF NOT EXISTS idx_repo_url ON repository_files (repo_url);"
docker exec gitcontext-postgres psql -U postgres -d gitcontext -c "CREATE INDEX IF NOT EXISTS idx_filepath ON repository_files (filepath);"
docker exec gitcontext-postgres psql -U postgres -d gitcontext -c "CREATE INDEX IF NOT EXISTS idx_file_type ON repository_files (file_type);"
docker exec gitcontext-postgres psql -U postgres -d gitcontext -c "CREATE INDEX IF NOT EXISTS idx_repository_files_tags ON repository_files USING GIN (tags);"
docker exec gitcontext-postgres psql -U postgres -d gitcontext -c "CREATE INDEX IF NOT EXISTS idx_content_tsvector ON repository_files USING GIN (content_tsvector);"
docker exec gitcontext-postgres psql -U postgres -d gitcontext -c "CREATE INDEX IF NOT EXISTS idx_embedding ON repository_files USING ivfflat (embedding vector_cosine_ops);"

echo "Creating repositories table..."
docker exec gitcontext-postgres psql -U postgres -d gitcontext -c "
CREATE TABLE IF NOT EXISTS repositories (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    default_branch TEXT,
    last_commit_hash TEXT,
    last_indexed_at TIMESTAMP WITH TIME ZONE,
    file_count INTEGER DEFAULT 0,
    status TEXT,
    clone_path TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);"

echo "Creating indexes for repositories..."
docker exec gitcontext-postgres psql -U postgres -d gitcontext -c "CREATE INDEX IF NOT EXISTS idx_repositories_url ON repositories (url);"
docker exec gitcontext-postgres psql -U postgres -d gitcontext -c "CREATE INDEX IF NOT EXISTS idx_repositories_name ON repositories (name);"

echo "Verifying tables..."
docker exec gitcontext-postgres psql -U postgres -d gitcontext -c "\dt"

echo "Done."