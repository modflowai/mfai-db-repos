#!/usr/bin/env python3
"""
Script to clean database tables in the GitContext database.
This script allows selective cleaning of repository files, repositories, or the entire database.
"""
import asyncio
import os
import sys
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gitcontext.lib.database.connection import get_session, session_context
from gitcontext.lib.database.repository import RepositoryRepository
from gitcontext.lib.database.repository_file import RepositoryFileRepository
from gitcontext.lib.database.models import Repository, RepositoryFile
from gitcontext.utils.config import Config, config
from gitcontext.utils.logger import get_logger, setup_logging

# Set up logging
logger = get_logger(__name__)
setup_logging(level="INFO")

# Load config from file
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "gitcontext-config.json")
config.load_from_file(CONFIG_FILE)

async def clean_repository_files(repo_id=None, embedding_only=False, empty_only=False):
    """
    Clean repository files from the database.
    
    Args:
        repo_id: Optional repository ID to clean files for a specific repository
                 If None, cleans files for all repositories
        embedding_only: If True, only clears embedding data but keeps the files
        empty_only: If True, only removes empty files
    
    Returns:
        Number of records affected
    """
    async with session_context() as session:
        if embedding_only:
            # Only clear embedding data
            from sqlalchemy import update
            
            stmt = update(RepositoryFile).values(
                embedding=None,
                embedding_string=None
            )
            
            if repo_id is not None:
                stmt = stmt.where(RepositoryFile.repo_id == repo_id)
                
            result = await session.execute(stmt)
            await session.commit()
            count = result.rowcount
            action = "cleared embeddings from"
        elif empty_only:
            # Only delete empty files
            if repo_id is not None:
                # Delete empty files for a specific repository
                stmt = RepositoryFile.__table__.delete().where(
                    RepositoryFile.repo_id == repo_id,
                    RepositoryFile.content.is_(None) | (RepositoryFile.content == "")
                )
            else:
                # Delete all empty files
                stmt = RepositoryFile.__table__.delete().where(
                    RepositoryFile.content.is_(None) | (RepositoryFile.content == "")
                )
                
            result = await session.execute(stmt)
            await session.commit()
            count = result.rowcount
            action = "deleted empty files from"
        else:
            # Delete the files
            if repo_id is not None:
                # Delete files for a specific repository
                stmt = RepositoryFile.__table__.delete().where(
                    RepositoryFile.repo_id == repo_id
                )
            else:
                # Delete all files
                stmt = RepositoryFile.__table__.delete()
                
            result = await session.execute(stmt)
            await session.commit()
            count = result.rowcount
            action = "deleted"
        
        repo_text = f"repository {repo_id}" if repo_id is not None else "all repositories"
        logger.info(f"Successfully {action} {count} files from {repo_text}")
        return count

async def clean_repositories(repo_id=None):
    """
    Clean repositories from the database.
    
    Args:
        repo_id: Optional repository ID to clean a specific repository
                If None, cleans all repositories
    
    Returns:
        Number of records affected
    """
    async with session_context() as session:
        if repo_id is not None:
            # Delete a specific repository
            stmt = Repository.__table__.delete().where(
                Repository.id == repo_id
            )
        else:
            # Delete all repositories
            stmt = Repository.__table__.delete()
            
        result = await session.execute(stmt)
        await session.commit()
        count = result.rowcount
        
        repo_text = f"repository {repo_id}" if repo_id is not None else "all repositories"
        logger.info(f"Successfully deleted {count} {repo_text}")
        return count

async def clean_all():
    """
    Clean all data from the database (both repositories and files).
    
    Returns:
        Tuple of (repositories_count, files_count) records affected
    """
    # Clean files first to avoid foreign key constraint issues
    files_count = await clean_repository_files()
    repos_count = await clean_repositories()
    
    logger.info(f"Database cleaned: {repos_count} repositories and {files_count} files deleted")
    return (repos_count, files_count)

async def main():
    """Parse arguments and run the appropriate cleaning command."""
    parser = argparse.ArgumentParser(description="Clean GitContext database tables")
    
    # Create a mutually exclusive group for specifying what to clean
    clean_group = parser.add_mutually_exclusive_group(required=True)
    clean_group.add_argument("--all", action="store_true", help="Clean all tables (repositories and files)")
    clean_group.add_argument("--repositories", action="store_true", help="Clean only repositories table")
    clean_group.add_argument("--files", action="store_true", help="Clean only repository files table")
    clean_group.add_argument("--embeddings", action="store_true", help="Clean only embedding data from files")
    clean_group.add_argument("--empty-files", action="store_true", help="Clean only empty files from database")
    
    # Optional repository ID to target specific repository
    parser.add_argument("--repo-id", type=int, help="Repository ID to clean (if not specified, cleans all)")
    
    # Add a confirmation flag to bypass the confirmation prompt
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt")
    
    args = parser.parse_args()
    
    # Build confirmation message
    if args.all:
        action = "DELETE ALL DATA from all tables"
    elif args.repositories:
        repo_text = f"repository {args.repo_id}" if args.repo_id else "all repositories"
        action = f"DELETE {repo_text} (this will also delete associated files due to CASCADE)"
    elif args.files:
        repo_text = f"repository {args.repo_id}" if args.repo_id else "all repositories"
        action = f"DELETE files from {repo_text}"
    elif args.embeddings:
        repo_text = f"repository {args.repo_id}" if args.repo_id else "all repositories"
        action = f"CLEAR embedding data from files in {repo_text}"
    elif args.empty_files:
        repo_text = f"repository {args.repo_id}" if args.repo_id else "all repositories"
        action = f"DELETE empty files from {repo_text}"
    
    # If not confirmed with --yes, ask for confirmation
    if not args.yes:
        confirm = input(f"Are you sure you want to {action}? [y/N] ")
        if confirm.lower() not in ["y", "yes"]:
            print("Operation cancelled.")
            return
    
    try:
        # Execute the appropriate cleaning operation
        if args.all:
            await clean_all()
        elif args.repositories:
            await clean_repositories(args.repo_id)
        elif args.files:
            await clean_repository_files(args.repo_id)
        elif args.embeddings:
            await clean_repository_files(args.repo_id, embedding_only=True)
        elif args.empty_files:
            await clean_repository_files(args.repo_id, empty_only=True)
            
        print("Database cleaning completed successfully.")
    except Exception as e:
        print(f"Error cleaning database: {str(e)}")
        import traceback
        print(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())