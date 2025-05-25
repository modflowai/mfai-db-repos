"""
MFAI DB Repos - A repository indexing system with vector embeddings.

This package provides tools to clone Git repositories, extract file content,
generate vector embeddings, and store the data in a PostgreSQL database with
pgvector for efficient semantic search.
"""

from mfai_db_repos.utils import get_logger

__version__ = "0.1.0"

# Configure package-level logger
logger = get_logger(__name__)