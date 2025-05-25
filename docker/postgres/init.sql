-- Initialize the PostgreSQL database for GitContext with pgvector extension

-- Create extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create repositories table first (because it's referenced by repository_files)
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
);

-- Create index on repository URL
CREATE INDEX IF NOT EXISTS idx_repositories_url ON repositories (url);

CREATE INDEX IF NOT EXISTS idx_repositories_name ON repositories (name);

-- Create repository_files table
CREATE TABLE IF NOT EXISTS repository_files (
    id SERIAL PRIMARY KEY,
    -- Repository information
    repo_id INTEGER REFERENCES repositories(id) ON DELETE CASCADE,
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
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    -- Constraints
    CONSTRAINT unique_file UNIQUE (repo_url, filepath)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_repo_url ON repository_files (repo_url);
CREATE INDEX IF NOT EXISTS idx_filepath ON repository_files (filepath);
CREATE INDEX IF NOT EXISTS idx_file_type ON repository_files (file_type);
CREATE INDEX IF NOT EXISTS idx_repository_files_tags ON repository_files USING GIN (tags);
CREATE INDEX IF NOT EXISTS idx_content_tsvector ON repository_files USING GIN (content_tsvector);
CREATE INDEX IF NOT EXISTS idx_embedding ON repository_files USING ivfflat (embedding vector_cosine_ops);