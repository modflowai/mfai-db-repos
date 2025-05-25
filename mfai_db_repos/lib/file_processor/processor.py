"""
File processor module for incremental repository processing.

This module provides functionality for processing repository files incrementally,
tracking changes, and updating the database accordingly.
"""
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Union

from mfai_db_repos.lib.database import RepositoryDB, RepositoryFileDB
from mfai_db_repos.lib.database.connection import session_context
from mfai_db_repos.lib.file_processor.extractor import FileExtractor
from mfai_db_repos.lib.git.repository import GitRepository, RepoStatus
from mfai_db_repos.utils.config import config
from mfai_db_repos.utils.logger import get_logger

logger = get_logger(__name__)


class FileProcessor:
    """File processor for incremental repository processing."""

    def __init__(
        self,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        max_file_size_mb: Optional[float] = None,
    ):
        """Initialize a file processor.

        Args:
            include_patterns: List of glob patterns to include
            exclude_patterns: List of glob patterns to exclude
            max_file_size_mb: Maximum file size to process in MB
        """
        file_filter_config = config.config.file_filter
        self.include_patterns = include_patterns or file_filter_config.include_patterns
        self.exclude_patterns = exclude_patterns or file_filter_config.exclude_patterns
        self.max_file_size_mb = max_file_size_mb or file_filter_config.max_file_size_mb
        
        # Initialize file extractor
        self.extractor = FileExtractor(
            max_file_size_mb=self.max_file_size_mb,
        )

    async def process_repository(
        self,
        repo_url: str,
        clone_path: Optional[Union[str, Path]] = None,
        branch: Optional[str] = None,
        force_reprocess: bool = False,
    ) -> Optional[int]:
        """Process a repository and store its files in the database.

        Args:
            repo_url: Repository URL
            clone_path: Path where the repository should be cloned (defaults to config)
            branch: Branch to process (defaults to config)
            force_reprocess: Force reprocessing of all files

        Returns:
            Number of processed files or None if processing failed
        """
        # Check if repository exists in the database
        async with session_context() as session:
            repo_repo = RepositoryDB(session)
            db_repo = await repo_repo.get_by_url(repo_url)
            
            if db_repo:
                logger.info(f"Repository {repo_url} already exists in the database")
                file_count = db_repo.file_count or 0
            else:
                # Create repository record
                db_repo = await repo_repo.create(
                    url=repo_url,
                    name=Path(repo_url).stem if "/" in repo_url else repo_url,
                    default_branch=branch,
                    clone_path=str(clone_path) if clone_path else None,
                )
                
                if not db_repo:
                    logger.error(f"Failed to create repository record for {repo_url}")
                    return None
                
                file_count = 0
            
            # Update repository status
            await repo_repo.update_status(db_repo.id, RepoStatus.CLONING.value)
        
        # Initialize Git repository
        git_repo = GitRepository(repo_url, clone_path, branch)
        
        # Clone repository if not already cloned
        if not git_repo.is_cloned() and not git_repo.clone():
            logger.error(f"Failed to clone repository {repo_url}")
            async with session_context() as session:
                repo_repo = RepositoryDB(session)
                await repo_repo.update_status(db_repo.id, RepoStatus.ERROR.value)
            return None
        
        # Update repository
        if not force_reprocess:
            success, changed_files = git_repo.update()
            if not success:
                logger.error(f"Failed to update repository {repo_url}")
                async with session_context() as session:
                    repo_repo = RepositoryDB(session)
                    await repo_repo.update_status(db_repo.id, RepoStatus.ERROR.value)
                return None
            
            if changed_files is not None and not changed_files:
                logger.info(f"Repository {repo_url} is already up to date")
                async with session_context() as session:
                    repo_repo = RepositoryDB(session)
                    await repo_repo.update_status(db_repo.id, RepoStatus.READY.value)
                return file_count
        
        # Process files
        async with session_context() as session:
            repo_repo = RepositoryDB(session)
            await repo_repo.update_status(db_repo.id, RepoStatus.INDEXING.value)
        
        try:
            processed_count = 0
            
            if force_reprocess:
                # Process all files
                processed_count = await self._process_all_files(db_repo.id, git_repo)
            else:
                # Process changed files only
                if changed_files is not None:
                    processed_count = await self._process_changed_files(db_repo.id, git_repo, changed_files)
            
            # Update repository status and last indexed time
            async with session_context() as session:
                repo_repo = RepositoryDB(session)
                await repo_repo.update(
                    db_repo.id,
                    status=RepoStatus.READY.value,
                    last_indexed_at=datetime.utcnow(),
                    last_commit_hash=git_repo.get_last_commit(),
                )
            
            return processed_count
        except Exception as e:
            logger.error(f"Failed to process repository {repo_url}: {e}")
            async with session_context() as session:
                repo_repo = RepositoryDB(session)
                await repo_repo.update_status(db_repo.id, RepoStatus.ERROR.value)
            return None

    async def _process_all_files(self, repo_id: int, git_repo: GitRepository) -> int:
        """Process all files in a repository.

        Args:
            repo_id: Repository ID in the database
            git_repo: Git repository instance

        Returns:
            Number of processed files
        """
        if not git_repo.is_cloned() or not git_repo.repo:
            return 0
        
        # Get all files recursively
        repo_path = Path(git_repo.repo.working_dir)
        all_files = []
        
        for root, _, files in os.walk(repo_path):
            # Skip .git directory
            if ".git" in Path(root).parts:
                continue
            
            # Process files
            for filename in files:
                filepath = Path(root) / filename
                rel_path = filepath.relative_to(repo_path)
                
                # Check if the file should be processed
                if self.extractor.should_process_file(
                    filepath,
                    self.include_patterns,
                    self.exclude_patterns,
                ):
                    all_files.append(str(rel_path))
        
        return await self._process_files(repo_id, git_repo, all_files)

    async def _process_changed_files(
        self,
        repo_id: int,
        git_repo: GitRepository,
        changed_files: List[str],
    ) -> int:
        """Process changed files in a repository.

        Args:
            repo_id: Repository ID in the database
            git_repo: Git repository instance
            changed_files: List of changed file paths

        Returns:
            Number of processed files
        """
        if not git_repo.is_cloned() or not git_repo.repo:
            return 0
        
        # Filter files based on patterns
        repo_path = Path(git_repo.repo.working_dir)
        filtered_files = []
        
        for rel_path in changed_files:
            filepath = repo_path / rel_path
            
            # Check if the file should be processed
            if self.extractor.should_process_file(
                filepath,
                self.include_patterns,
                self.exclude_patterns,
            ):
                filtered_files.append(rel_path)
        
        return await self._process_files(repo_id, git_repo, filtered_files)

    async def _process_files(
        self,
        repo_id: int,
        git_repo: GitRepository,
        file_paths: List[str],
    ) -> int:
        """Process a list of files and store them in the database.

        Args:
            repo_id: Repository ID in the database
            git_repo: Git repository instance
            file_paths: List of file paths relative to repository root

        Returns:
            Number of processed files
        """
        if not git_repo.is_cloned() or not git_repo.repo:
            return 0
        
        repo_path = Path(git_repo.repo.working_dir)
        processed_count = 0
        
        # Process each file
        for i, rel_path in enumerate(file_paths):
            filepath = repo_path / rel_path
            
            try:
                # Get file metadata
                metadata = self.extractor.get_file_metadata(filepath)
                
                # Extract content
                content = self.extractor.extract_content(filepath)
                
                # Skip files with no content or empty content
                if content is None or content.strip() == "":
                    logger.debug(f"Skipping empty file: {filepath}")
                    continue
                
                async with session_context() as session:
                    file_repo = RepositoryFileDB(session)
                    
                    # Check if file already exists in database
                    existing_file = await file_repo.get_by_path(repo_id, str(rel_path))
                    
                    if existing_file:
                        # Update existing file
                        # Create a copy of existing file and update fields
                        existing_file.content = content
                        existing_file.file_size = metadata["file_size"]
                        existing_file.last_modified = metadata["last_modified"]
                        
                        # Add metadata if it doesn't exist
                        if not existing_file.repo_metadata:
                            existing_file.repo_metadata = {}
                        
                        # Update metadata
                        if isinstance(existing_file.repo_metadata, dict):
                            existing_file.repo_metadata["git_status"] = "modified"
                            existing_file.repo_metadata["file_type"] = metadata["file_type"]
                        
                        # Update file
                        await file_repo.update(existing_file)
                    else:
                        # Create new file
                        rel_path_str = str(rel_path)
                        new_file = await file_repo.create(
                            repo_id=repo_id,
                            filepath=rel_path_str,
                            filename=Path(rel_path_str).name,
                            extension=Path(rel_path_str).suffix.lower(),
                            content=content,
                            file_size=metadata["file_size"],
                            last_modified=metadata["last_modified"],
                            # Convert git_status to metadata
                            metadata={"git_status": "added", "file_type": metadata["file_type"]}
                        )
                        
                        if new_file:
                            processed_count += 1
                
                # Log progress every 100 files
                if (i + 1) % 100 == 0:
                    logger.info(f"Processed {i + 1}/{len(file_paths)} files")
            
            except Exception as e:
                logger.warning(f"Failed to process file {rel_path}: {e}")
        
        return processed_count

    async def remove_deleted_files(self, repo_id: int, git_repo: GitRepository) -> int:
        """Remove files from the database that no longer exist in the repository.

        Args:
            repo_id: Repository ID in the database
            git_repo: Git repository instance

        Returns:
            Number of removed files
        """
        if not git_repo.is_cloned() or not git_repo.repo:
            return 0
        
        # Get all files from the repository
        repo_path = Path(git_repo.repo.working_dir)
        repo_files = set()
        
        for root, _, files in os.walk(repo_path):
            # Skip .git directory
            if ".git" in Path(root).parts:
                continue
            
            for filename in files:
                filepath = Path(root) / filename
                rel_path = str(filepath.relative_to(repo_path))
                repo_files.add(rel_path)
        
        # Get all files from the database
        async with session_context() as session:
            file_repo = RepositoryFileDB(session)
            db_files = await file_repo.get_by_repository_id(repo_id)
            
            removed_count = 0
            for db_file in db_files:
                if db_file.filepath not in repo_files:
                    # File no longer exists, remove it
                    if await file_repo.delete(db_file.id):
                        removed_count += 1
            
            return removed_count