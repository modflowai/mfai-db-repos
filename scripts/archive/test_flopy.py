#!/usr/bin/env python3
"""
Test script to clone and index the flopy repository.
This script focuses on processing specifically .py and .md files.
"""
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gitcontext.core.services.repository_service import RepositoryService
from gitcontext.lib.database.connection import get_session, session_context
from gitcontext.lib.database.repository import RepositoryRepository
from gitcontext.lib.database.repository_file import RepositoryFileRepository
from gitcontext.lib.file_processor.filter import FileFilter
from gitcontext.utils.config import Config
from gitcontext.utils.logger import get_logger, setup_logging

# Set up logging
logger = get_logger(__name__)
setup_logging(level="DEBUG")

FLOPY_REPO_URL = "https://github.com/modflowpy/flopy.git"
FLOPY_DEFAULT_BRANCH = "develop"  # The default branch for flopy is 'develop', not 'main'


async def test_flopy_repository():
    """
    Clone and process the flopy repository, focusing on .py and .md files.
    """
    async with session_context() as session:
        # Create repositories
        repo_repo = RepositoryRepository(session)
        file_repo = RepositoryFileRepository(session)
        
        # Create repository service
        repo_service = RepositoryService(
            repo_repo=repo_repo,
            file_repo=file_repo
        )
        
        # Check if repository already exists
        existing_repo = await repo_repo.get_by_url(FLOPY_REPO_URL)
        if existing_repo:
            print(f"Repository already exists: {existing_repo.name} (ID: {existing_repo.id})")
            print("Updating repository...")
            
            # Update repository
            success, changed_files = await repo_service.update_repository(existing_repo.id)
            
            if success:
                print(f"Repository updated successfully! {len(changed_files)} files changed")
                
                if changed_files:
                    # Process changed files
                    file_count = await repo_service.process_repository_files(
                        existing_repo.id, files=changed_files
                    )
                    print(f"Processed {file_count} changed files")
            else:
                print("Failed to update repository")
            
            # Return existing repository
            return existing_repo
            
        # Repository doesn't exist, create it
        print(f"Cloning repository: {FLOPY_REPO_URL}")
        repository = await repo_service.add_repository(
            url=FLOPY_REPO_URL,
            default_branch=FLOPY_DEFAULT_BRANCH
        )
        
        if not repository:
            print("Failed to create repository")
            return None
        
        print(f"Repository created: {repository.name} (ID: {repository.id})")
        
        # Process files with custom filter
        print("Processing repository files...")
        # First, make sure we're in the correct state
        await repo_repo.update_status(repository.id, "analyzing")
        
        # Import file processor from the processor module
        from gitcontext.lib.file_processor.processor import FileProcessor
        from gitcontext.lib.file_processor.filter import FileFilter
        from gitcontext.lib.git.repository import GitRepository
        
        # Create Git repository object
        git_repo = GitRepository(
            url=repository.url,
            branch=repository.default_branch,
            clone_path=repository.clone_path,
        )
        
        # Create file processor with custom filter for .py and .md files
        processor = FileProcessor(
            include_patterns=["**/*.py", "**/*.md"],
            exclude_patterns=["**/.*", "**/node_modules/**", "**/venv/**", "**/__pycache__/**"]
        )
        
        # Process all files
        file_count = await processor._process_all_files(repository.id, git_repo)
        print(f"Processed {file_count} files")
        
        # Update repository status
        await repo_repo.update_status(repository.id, "ready")
        
        # Get file counts to verify processing
        file_count = await file_repo.count_by_repository_id(repository.id)
        
        print(f"\nRepository stats:")
        print(f"Total processed files: {file_count}")
        
        return repository


async def check_repository_files(repo_id: int):
    """
    Check files processed in the repository.
    """
    async with session_context() as session:
        file_repo = RepositoryFileRepository(session)
        
        # Get file counts
        total_files = await file_repo.count_by_repository_id(repo_id)
        
        # Count files by extension manually
        files = await file_repo.get_by_repository_id(repo_id)
        py_files = sum(1 for f in files if f.extension == ".py")
        md_files = sum(1 for f in files if f.extension == ".md")
        
        print(f"\nRepository file stats:")
        print(f"Total files: {total_files}")
        print(f"Python files: {py_files}")
        print(f"Markdown files: {md_files}")
        
        # Get some sample files to verify content
        print("\nSample files:")
        sample_files = files[:5] if len(files) > 5 else files
        for file in sample_files:
            print(f"- {file.filepath} ({file.file_type}, {file.file_size} bytes)")


async def main():
    """Run the main test procedure."""
    try:
        # Run the test
        repo = await test_flopy_repository()
        
        if repo and repo.id:
            # Always process files with our improved pattern matching
            print("Processing repository files with improved pattern matching...")
            async with session_context() as session:
                file_repo = RepositoryFileRepository(session)
                repo_repo = RepositoryRepository(session)
                
                # Mark repo as being processed
                await repo_repo.update_status(repo.id, "analyzing")
                
                from gitcontext.lib.file_processor.processor import FileProcessor
                from gitcontext.lib.git.repository import GitRepository
                
                # Create Git repository object
                git_repo = GitRepository(
                    url=repo.url,
                    branch=repo.default_branch,
                    clone_path=repo.clone_path,
                )
                
                # Create file processor with custom filter for .py and .md files
                processor = FileProcessor(
                    include_patterns=["**/*.py", "**/*.md"],
                    # Don't exclude .docs folder which contains important files
                    exclude_patterns=["**/.git/**", "**/node_modules/**", "**/venv/**", "**/__pycache__/**"]
                )
                
                # Process all files (now using improved pattern matching)
                print("Starting file processing...")
                file_count = await processor._process_all_files(repo.id, git_repo)
                print(f"Processed {file_count} files")
                
                # Update repo status
                await repo_repo.update_status(repo.id, "ready")
            
            # Check the repository files
            await check_repository_files(repo.id)
            
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