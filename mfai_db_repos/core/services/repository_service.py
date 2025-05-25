"""
Repository service module.

This module provides high-level services for managing Git repositories.
"""
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from mfai_db_repos.lib.database.repository import RepositoryRepository
from mfai_db_repos.lib.database.repository_file import RepositoryFileRepository
from mfai_db_repos.lib.git.repository import GitRepository, RepoStatus
from mfai_db_repos.utils.config import Config
from mfai_db_repos.utils.logger import get_logger

logger = get_logger(__name__)


class RepositoryService:
    """Service for managing Git repositories."""
    
    def __init__(
        self,
        repo_repo: RepositoryRepository,
        file_repo: Optional[RepositoryFileRepository] = None,
        config: Optional[Config] = None,
    ):
        """Initialize the repository service.
        
        Args:
            repo_repo: Repository repository
            file_repo: Optional repository file repository
            config: Optional configuration
        """
        self.repo_repo = repo_repo
        self.file_repo = file_repo
        self.config = config or Config()
    
    async def add_repository(
        self,
        url: str,
        name: Optional[str] = None,
        default_branch: Optional[str] = None,
        clone_path: Optional[Union[str, Path]] = None,
    ) -> Optional[Dict]:
        """Add a new repository.
        
        Args:
            url: Repository URL
            name: Optional repository name (derived from URL if not provided)
            default_branch: Optional default branch
            clone_path: Optional custom clone path
            
        Returns:
            Repository object if successful, None otherwise
        """
        # Create Git repository object
        git_repo = GitRepository(
            url=url,
            branch=default_branch,
            clone_path=clone_path,
        )
        
        # Use derived name if not provided
        if not name:
            name = git_repo.name
        
        logger.info(f"Adding repository: {name} ({url})")
        
        # Clone repository
        if not git_repo.clone():
            logger.error(f"Failed to clone repository: {url}")
            return None
        
        # Create repository record
        repository = await self.repo_repo.create(
            url=url,
            name=name,
            default_branch=git_repo.branch,
            clone_path=str(git_repo.clone_path),
        )
        
        if not repository:
            logger.error(f"Failed to create repository record: {url}")
            # Clean up cloned files if repository record creation failed
            git_repo.cleanup()
            return None
        
        # Update repository status
        await self.repo_repo.update_status(repository.id, RepoStatus.READY)
        
        # Get last commit
        last_commit = git_repo.get_last_commit()
        if last_commit:
            await self.repo_repo.update_last_commit(repository.id, last_commit)
        
        return repository
    
    async def update_repository(
        self,
        repository_id: int,
    ) -> Tuple[bool, List[str]]:
        """Update a repository to the latest commit.
        
        Args:
            repository_id: Repository ID
            
        Returns:
            Tuple of (success, list of changed files)
        """
        # Get repository
        repository = await self.repo_repo.get_by_id(repository_id)
        if not repository:
            logger.error(f"Repository with ID {repository_id} not found")
            return False, []
        
        logger.info(f"Updating repository: {repository.name} (ID: {repository_id})")
        
        # Update repository status
        await self.repo_repo.update_status(repository.id, RepoStatus.UPDATING)
        
        # Create Git repository object
        git_repo = GitRepository(
            url=repository.url,
            branch=repository.default_branch,
            clone_path=repository.clone_path,
        )
        
        # Update repository
        success, changed_files = git_repo.update()
        
        if not success:
            logger.error(f"Failed to update repository: {repository.name}")
            await self.repo_repo.update_status(repository.id, RepoStatus.ERROR)
            return False, []
        
        # Update status
        await self.repo_repo.update_status(repository.id, RepoStatus.READY)
        
        # Update last commit
        last_commit = git_repo.get_last_commit()
        if last_commit:
            await self.repo_repo.update_last_commit(repository.id, last_commit)
        
        logger.info(f"Repository updated: {repository.name} ({len(changed_files or [])} files changed)")
        
        return True, changed_files or []
    
    async def delete_repository(
        self,
        repository_id: int,
        keep_files: bool = False,
    ) -> bool:
        """Delete a repository.
        
        Args:
            repository_id: Repository ID
            keep_files: Whether to keep repository files on disk
            
        Returns:
            True if successful, False otherwise
        """
        # Get repository
        repository = await self.repo_repo.get_by_id(repository_id)
        if not repository:
            logger.error(f"Repository with ID {repository_id} not found")
            return False
        
        logger.info(f"Deleting repository: {repository.name} (ID: {repository_id})")
        
        # Delete repository files if requested
        if not keep_files and repository.clone_path:
            # Create Git repository object
            git_repo = GitRepository(
                url=repository.url,
                clone_path=repository.clone_path,
            )
            
            # Clean up repository files
            git_repo.cleanup()
        
        # Delete repository record
        success = await self.repo_repo.delete(repository_id)
        
        if not success:
            logger.error(f"Failed to delete repository: {repository.name}")
            return False
        
        logger.info(f"Repository deleted: {repository.name}")
        
        return True
    
    async def process_repository_files(
        self,
        repository_id: int,
        files: Optional[List[str]] = None,
    ) -> int:
        """Process repository files.
        
        Args:
            repository_id: Repository ID
            files: Optional list of files to process (all files if None)
            
        Returns:
            Number of files processed
        """
        # Ensure file repository is available
        if not self.file_repo:
            logger.error("Repository file repository not provided")
            return 0
        
        # Get repository
        repository = await self.repo_repo.get_by_id(repository_id)
        if not repository:
            logger.error(f"Repository with ID {repository_id} not found")
            return 0
        
        logger.info(f"Processing files for repository: {repository.name}")
        
        # Update repository status
        await self.repo_repo.update_status(repository.id, RepoStatus.ANALYZING)
        
        # Create Git repository object
        git_repo = GitRepository(
            url=repository.url,
            branch=repository.default_branch,
            clone_path=repository.clone_path,
        )
        
        # Ensure repository is cloned
        if not git_repo.is_cloned():
            logger.error(f"Repository not cloned: {repository.name}")
            await self.repo_repo.update_status(repository.id, RepoStatus.ERROR)
            return 0
        
        # Use file processor to process files
        from gitcontext.lib.file_processor.processor import FileProcessor
        
        processor = FileProcessor()
        
        if files:
            # Process specific files
            file_count = await processor.process_changed_files(repository_id, git_repo, files)
        else:
            # Process all files in the repository
            file_count = await processor._process_all_files(repository_id, git_repo)
        
        # Update repository status
        await self.repo_repo.update_status(repository.id, RepoStatus.READY)
        
        # Return number of files processed
        return file_count
    
    async def get_repository_stats(
        self,
        repository_id: int,
    ) -> Dict:
        """Get repository statistics.
        
        Args:
            repository_id: Repository ID
            
        Returns:
            Dictionary with repository statistics
        """
        # Get repository
        repository = await self.repo_repo.get_by_id(repository_id)
        if not repository:
            logger.error(f"Repository with ID {repository_id} not found")
            return {}
        
        # Create Git repository object
        git_repo = GitRepository(
            url=repository.url,
            branch=repository.default_branch,
            clone_path=repository.clone_path,
        )
        
        # Get Git stats
        stats = git_repo.get_repo_stats()
        
        # Get file stats
        if self.file_repo:
            file_count = await self.file_repo.count_by_repository_id(repository_id)
            stats["file_count"] = file_count
            
            # Get embedding stats
            files_without_embeddings = await self.file_repo.count_files_without_embeddings(repository_id)
            stats["files_with_embeddings"] = file_count - files_without_embeddings
            stats["embedding_coverage"] = (
                (file_count - files_without_embeddings) / file_count * 100
                if file_count > 0 else 0
            )
        
        return stats