"""
Database management module for GitContext.

This module provides operations for database management, including
resetting the database, migrations, and general maintenance tasks.
"""
import os
import subprocess
from pathlib import Path
from typing import Optional, Tuple, Union
import asyncio

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from mfai_db_repos.utils.logger import get_logger
from mfai_db_repos.utils.config import config

logger = get_logger(__name__)

def reset_database(docker_compose_file: Optional[str] = None) -> Tuple[bool, str]:
    """
    Reset the database by stopping containers, removing volumes, and starting fresh.
    This only works with local Docker containers, not with serverless databases.
    
    Args:
        docker_compose_file: Path to the docker-compose.yml file (default: project root)
        
    Returns:
        Tuple of (success, message)
    """
    # Check if using serverless database
    if config.config.database.is_serverless:
        return False, "Cannot reset serverless database using Docker commands. Please manually reset your Neon DB instance."
        
    try:
        # Get project root directory
        project_root = Path(__file__).parents[3]
        
        # Use provided docker-compose file or default
        if docker_compose_file:
            compose_file = Path(docker_compose_file)
        else:
            compose_file = project_root / "docker-compose.yml"
            
        if not compose_file.exists():
            return False, f"Docker compose file not found: {compose_file}"
            
        # Change to the directory containing the compose file
        os.chdir(compose_file.parent)
        
        # Step 1: Stop containers
        logger.info("Stopping Docker containers...")
        subprocess.run(["docker", "compose", "down"], check=True)
        
        # Step 2: Remove volumes
        logger.info("Removing Docker volumes...")
        try:
            subprocess.run(
                ["docker", "volume", "rm", "gitcontext_py_postgres_data", "gitcontext_py_pgadmin_data"], 
                check=False
            )
        except subprocess.CalledProcessError:
            # Ignore errors when removing volumes (they might not exist)
            logger.warning("Some volumes could not be removed (they may not exist)")
        
        # Step 3: Start containers
        logger.info("Starting Docker containers...")
        subprocess.run(["docker", "compose", "up", "-d"], check=True)
        
        # Step 4: Wait for database to start
        logger.info("Waiting for PostgreSQL to start...")
        subprocess.run(["sleep", "5"], check=True)
        
        return True, "Database reset successfully. PostgreSQL is running on port 5437."
        
    except subprocess.CalledProcessError as e:
        error_message = f"Command failed with exit code {e.returncode}: {e.cmd}"
        logger.error(error_message)
        return False, error_message
    except Exception as e:
        error_message = f"Database reset failed: {str(e)}"
        logger.error(error_message)
        return False, error_message

async def init_database_extensions() -> Tuple[bool, str]:
    """
    Initialize required database extensions, especially pgvector.
    
    Returns:
        Tuple of (success, message)
    """
    try:
        # Import here to avoid circular imports
        from mfai_db_repos.lib.database.connection import get_engine
        
        # Create pgvector extension if it doesn't exist
        async with get_engine().begin() as conn:
            # Enable pgvector extension
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            logger.info("Vector extension enabled in the database")
            
            # For Neon DB, use HNSW index type which performs better in serverless environments
            if config.config.database.is_serverless:
                logger.info("Serverless database detected, will use HNSW indexes for vector search")
                
        return True, "Database extensions initialized successfully."
        
    except SQLAlchemyError as e:
        error_message = f"Failed to initialize database extensions: {str(e)}"
        logger.error(error_message)
        return False, error_message
    except Exception as e:
        error_message = f"Unexpected error initializing database extensions: {str(e)}"
        logger.error(error_message)
        return False, error_message


async def init_database_schema() -> Tuple[bool, str]:
    """
    Initialize the database schema by creating all tables.
    
    Returns:
        Tuple of (success, message)
    """
    try:
        # Import here to avoid circular imports
        from mfai_db_repos.lib.database.connection import get_engine
        from mfai_db_repos.lib.database.models import Base
        
        # Create all tables
        async with get_engine().begin() as conn:
            # Create all tables defined in the models
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database schema created successfully")
            
            # Create specialized index for vector operations if using Neon DB
            if config.config.database.is_serverless:
                try:
                    # Add vector L2 index - this works better for Neon DB with pgvector
                    await conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_embedding_l2
                    ON repository_files 
                    USING ivfflat (embedding vector_l2_ops)
                    WITH (lists = 100);
                    """))
                    
                    logger.info("Created L2 vector index for Neon DB")
                except Exception as idx_error:
                    # Log error but don't fail the entire operation
                    logger.warning(f"Failed to create L2 vector index: {str(idx_error)}")
                    
                try:
                    # Add vector cosine index (smaller and more efficient)
                    await conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_embedding_cosine
                    ON repository_files 
                    USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100);
                    """))
                    
                    logger.info("Created cosine vector index for Neon DB")
                except Exception as idx_error:
                    # Log error but don't fail the entire operation
                    logger.warning(f"Failed to create cosine vector index: {str(idx_error)}")
            
        return True, "Database schema initialized successfully."
        
    except SQLAlchemyError as e:
        error_message = f"Failed to initialize database schema: {str(e)}"
        logger.error(error_message)
        return False, error_message
    except Exception as e:
        error_message = f"Unexpected error initializing database schema: {str(e)}"
        logger.error(error_message)
        return False, error_message


async def remove_repository(repository_identifier: Union[int, str]) -> Tuple[bool, str]:
    """
    Remove a repository and all its files from the database.
    
    Args:
        repository_identifier: Repository ID or name/URL to remove
        
    Returns:
        Tuple of (success, message)
    """
    try:
        # Import here to avoid circular imports
        from mfai_db_repos.lib.database.connection import get_session
        from mfai_db_repos.lib.database.repository import RepositoryRepository
        
        async with get_session() as session:
            repo_repo = RepositoryRepository(session)
            
            # Check if identifier is an integer (ID) or string (name/URL)
            repository = None
            if isinstance(repository_identifier, int):
                repository = await repo_repo.get_by_id(repository_identifier)
            else:
                # Try first as URL, then as name
                repository = await repo_repo.get_by_url(repository_identifier)
                if not repository:
                    repository = await repo_repo.get_by_name(repository_identifier)
            
            if not repository:
                return False, f"Repository not found: {repository_identifier}"
            
            # Get repository information for the log message
            repo_id = repository.id
            repo_name = repository.name
            repo_url = repository.url
            
            # Delete the repository (this will cascade to repository_files due to FK constraint)
            success = await repo_repo.delete(repo_id)
            
            if success:
                logger.info(f"Removed repository: {repo_name} (ID: {repo_id}, URL: {repo_url})")
                return True, f"Repository '{repo_name}' removed successfully."
            else:
                return False, f"Failed to remove repository: {repo_name}"
                
    except Exception as e:
        error_message = f"Repository removal failed: {str(e)}"
        logger.error(error_message)
        return False, error_message