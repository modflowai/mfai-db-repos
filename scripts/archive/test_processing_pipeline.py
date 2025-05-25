#!/usr/bin/env python3
"""
Test script for the complete processing pipeline.

This script:
1. Cleans the database (optionally)
2. Runs the complete processing pipeline on a test repository
3. Processes files in batches of 5

Usage:
    python scripts/test_processing_pipeline.py --repo-url https://github.com/modflowpy/flopy.git --batch-size 5 --limit 5
"""
import asyncio
import os
import sys
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gitcontext.utils.env import load_env, get_env
from gitcontext.utils.logger import setup_logging, get_logger
from gitcontext.core.services.processing_service import RepositoryProcessingService

# Set up logging
logger = get_logger(__name__)
setup_logging(level="INFO")

# Load environment variables
load_env()

async def clean_database(repo_id=None):
    """
    Clean the database before running the test.
    
    Args:
        repo_id: Optional repository ID to clean a specific repository
    """
    from gitcontext.lib.database.connection import session_context
    from gitcontext.lib.database.repository import RepositoryRepository
    from gitcontext.lib.database.repository_file import RepositoryFileRepository
    from gitcontext.lib.database.models import Repository, RepositoryFile
    
    # Clean repository files first
    async with session_context() as session:
        if repo_id is not None:
            logger.info(f"Cleaning files for repository ID {repo_id}")
            stmt = RepositoryFile.__table__.delete().where(
                RepositoryFile.repo_id == repo_id
            )
        else:
            logger.info("Cleaning all repository files")
            stmt = RepositoryFile.__table__.delete()
            
        result = await session.execute(stmt)
        await session.commit()
        file_count = result.rowcount
        logger.info(f"Cleaned {file_count} repository files")
    
    # Clean repositories if no specific repo_id
    if repo_id is None:
        async with session_context() as session:
            logger.info("Cleaning all repositories")
            stmt = Repository.__table__.delete()
            result = await session.execute(stmt)
            await session.commit()
            repo_count = result.rowcount
            logger.info(f"Cleaned {repo_count} repositories")
    
async def test_processing_pipeline(
    repo_url: str,
    batch_size: int = 5,
    limit: int = 5,
    clean: bool = True,
    repo_id: int = None
):
    """
    Test the complete processing pipeline.
    
    Args:
        repo_url: Repository URL to process
        batch_size: Number of files to process in each batch
        limit: Limit number of files to process
        clean: Whether to clean the database before processing
        repo_id: Optional repository ID (if already exists)
    """
    # Clean the database if requested
    if clean:
        await clean_database(repo_id)
    
    # Create processing service
    service = RepositoryProcessingService(batch_size=batch_size)
    
    # Process repository
    success, failure = await service.process_repository(
        repo_url=repo_url,
        repo_id=repo_id,
        limit=limit
    )
    
    # Print summary
    print("\nProcessing complete!")
    print(f"Successfully processed: {success} files")
    print(f"Failed to process: {failure} files")
    
    # Display database metrics if successful
    if success > 0:
        from gitcontext.lib.database.connection import session_context
        from gitcontext.lib.database.repository import RepositoryRepository
        from gitcontext.lib.database.repository_file import RepositoryFileRepository
        
        async with session_context() as session:
            repo_repo = RepositoryRepository(session)
            file_repo = RepositoryFileRepository(session)
            
            if repo_id is None:
                # Get all repositories and use the first one
                repos = await repo_repo.get_all()
                if repos:
                    repo_id = repos[0].id
            
            if repo_id:
                # Get file statistics
                repository = await repo_repo.get_by_id(repo_id)
                file_count = await file_repo.count_by_repository_id(repo_id)
                empty_count = await file_repo.count_files_without_embeddings(repo_id)
                
                print(f"\nRepository: {repository.name} (ID: {repo_id})")
                print(f"Total files: {file_count}")
                print(f"Files with embeddings: {file_count - empty_count}")
                print(f"Files without embeddings: {empty_count}")
                
                # Get embedding models
                model_counts = await file_repo.get_embedding_model_counts(repo_id)
                if model_counts:
                    print("\nEmbedding models:")
                    for model, count in model_counts.items():
                        print(f"  - {model}: {count} files")

async def main():
    """Parse arguments and run the test."""
    parser = argparse.ArgumentParser(description="Test the complete processing pipeline")
    parser.add_argument(
        "--repo-url",
        type=str,
        default="https://github.com/modflowpy/flopy.git",
        help="Repository URL to process"
    )
    parser.add_argument(
        "--repo-id",
        type=int,
        help="Repository ID (if already exists)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5,
        help="Number of files to process in each batch"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Limit number of files to process"
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Don't clean the database before processing"
    )
    args = parser.parse_args()
    
    try:
        await test_processing_pipeline(
            repo_url=args.repo_url,
            batch_size=args.batch_size,
            limit=args.limit,
            clean=not args.no_clean,
            repo_id=args.repo_id
        )
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        import traceback
        print(f"\nError: {str(e)}")
        print(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())