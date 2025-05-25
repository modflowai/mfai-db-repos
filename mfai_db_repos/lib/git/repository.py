"""
Git repository management module.

This module provides functionality for cloning, updating, and managing Git repositories.
"""
import shutil
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import git
from git import GitCommandError, Repo
from git.objects import Commit

from mfai_db_repos.utils.config import config
from mfai_db_repos.utils.logger import get_logger

logger = get_logger(__name__)


class RepoStatus(str, Enum):
    """Repository status enumeration."""

    CREATED = "created"
    CLONING = "cloning"
    UPDATING = "updating"
    ANALYZING = "analyzing"
    INDEXING = "indexing"
    READY = "ready"
    ERROR = "error"


class GitRepository:
    """Git repository management class."""

    def __init__(
        self,
        url: str,
        clone_path: Optional[Union[str, Path]] = None,
        branch: Optional[str] = None,
        depth: Optional[int] = None,
    ):
        """Initialize a Git repository manager.

        Args:
            url: Repository URL
            clone_path: Path where the repository should be cloned (defaults to config)
            branch: Branch to clone (defaults to config)
            depth: Depth limit for clone (defaults to config)
        """
        self.url = url
        self.name = self._extract_repo_name(url)
        
        # Use config defaults if not specified
        git_config = config.config.git
        self.clone_path = Path(clone_path) if clone_path else git_config.default_clone_path / self.name
        self.branch = branch or git_config.default_branch
        self.depth = depth if depth is not None else git_config.depth
        
        # Repository instance (initialized after clone)
        self._repo: Optional[Repo] = None
        self._status = RepoStatus.CREATED

    @property
    def repo(self) -> Optional[Repo]:
        """Get the Git repository instance if available."""
        if self._repo is None and self.clone_path.exists():
            try:
                self._repo = Repo(self.clone_path)
            except (git.InvalidGitRepositoryError, git.NoSuchPathError):
                logger.warning(f"No valid Git repository at {self.clone_path}")
        return self._repo

    @property
    def status(self) -> RepoStatus:
        """Get the current status of the repository."""
        return self._status

    @status.setter
    def status(self, value: RepoStatus) -> None:
        """Set the repository status."""
        self._status = value
        logger.info(f"Repository {self.name} status: {self._status}")

    def is_cloned(self) -> bool:
        """Check if the repository has been cloned."""
        return self.repo is not None

    def _extract_repo_name(self, url: str) -> str:
        """Extract the repository name from the URL.
        
        Args:
            url: Repository URL
            
        Returns:
            Repository name
        """
        # Handle different URL formats
        if url.endswith(".git"):
            url = url[:-4]
        
        # Extract the last part of the URL as the name
        parts = url.rstrip("/").split("/")
        return parts[-1]

    def clone(self) -> bool:
        """Clone the repository.
        
        Returns:
            True if clone succeeded, False otherwise
        """
        if self.is_cloned():
            logger.info(f"Repository {self.name} is already cloned at {self.clone_path}")
            # Update the branch info if it's already cloned
            if self._repo:
                self.branch = self._repo.active_branch.name
            return True
        
        logger.info(f"Cloning repository {self.url} to {self.clone_path}")
        self.status = RepoStatus.CLONING
        
        try:
            # Create parent directory if it doesn't exist
            self.clone_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Remove directory if it exists but is not a valid git repo
            if self.clone_path.exists() and not (self.clone_path / ".git").exists():
                shutil.rmtree(self.clone_path)
            
            # Get the URL with GitHub token if applicable
            url_to_use = self._get_authenticated_url(self.url)
            
            # Try to clone with the specified branch first
            if self.branch:
                try:
                    # Clone options with branch specified
                    clone_kwargs = {
                        "to_path": str(self.clone_path),
                        "branch": self.branch,
                    }
                    
                    # Add depth if specified
                    if self.depth is not None:
                        clone_kwargs["depth"] = self.depth
                    
                    # Clone the repository with specified branch
                    self._repo = git.Repo.clone_from(url_to_use, **clone_kwargs)
                    
                    # Update the branch with the actual checked out branch
                    if self._repo:
                        self.branch = self._repo.active_branch.name
                        logger.info(f"Repository {self.name} cloned on branch: {self.branch}")
                    
                    self.status = RepoStatus.READY
                    logger.info(f"Successfully cloned repository {self.name}")
                    return True
                except GitCommandError as branch_error:
                    logger.warning(f"Failed to clone with branch '{self.branch}', falling back to default clone: {branch_error}")
                    # If directory was partially created, remove it
                    if self.clone_path.exists():
                        shutil.rmtree(self.clone_path)
            
            # If we're here, either no branch was specified or the specified branch failed
            # Clone without specifying a branch (let Git decide)
            clone_kwargs = {
                "to_path": str(self.clone_path),
            }
            
            # Add depth if specified
            if self.depth is not None:
                clone_kwargs["depth"] = self.depth
            
            # Clone the repository without specifying branch
            self._repo = git.Repo.clone_from(url_to_use, **clone_kwargs)
            
            # Update the branch with the actual checked out branch
            if self._repo:
                self.branch = self._repo.active_branch.name
                logger.info(f"Repository {self.name} cloned on default branch: {self.branch}")
            
            self.status = RepoStatus.READY
            logger.info(f"Successfully cloned repository {self.name}")
            return True
            
        except GitCommandError as e:
            self.status = RepoStatus.ERROR
            logger.error(f"Failed to clone repository {self.url}: {e}")
            return False
            
    def _get_authenticated_url(self, url: str) -> str:
        """Get an authenticated URL if GitHub token is available.
        
        This adds the GitHub token to the URL for GitHub repositories if a token
        is configured. For non-GitHub repositories, the original URL is returned.
        
        Args:
            url: Original repository URL
            
        Returns:
            URL with authentication token if applicable, otherwise the original URL
        """
        # Only modify GitHub URLs
        if "github.com" not in url:
            return url
            
        # Check if token is available
        git_config = config.config.git
        if not git_config.github_token:
            return url
            
        # Parse the URL to insert the token
        if url.startswith("https://"):
            # For HTTPS URLs: https://github.com/user/repo.git -> https://token@github.com/user/repo.git
            return url.replace("https://", f"https://{git_config.github_token}@")
        
        # For other URL formats or SSH URLs, return as is
        return url

    def update(self) -> Tuple[bool, Optional[List[str]]]:
        """Update the repository to the latest commit.
        
        Returns:
            Tuple of (success, list of changed files or None)
        """
        if not self.is_cloned():
            logger.warning(f"Repository {self.name} is not cloned yet")
            return False, None
        
        logger.info(f"Updating repository {self.name}")
        self.status = RepoStatus.UPDATING
        
        try:
            repo = self.repo
            if not repo:
                return False, None
            
            # Store current commit hash
            old_commit = repo.head.commit
            
            # Get authenticated remote URL if needed
            if repo.remotes.origin.url.startswith("https://github.com"):
                auth_url = self._get_authenticated_url(repo.remotes.origin.url)
                # Update the remote URL if it's different (token was added)
                if auth_url != repo.remotes.origin.url:
                    repo.remotes.origin.set_url(auth_url)
            
            # Fetch and pull
            origin = repo.remotes.origin
            origin.fetch()
            origin.pull()
            
            # Get new commit hash
            new_commit = repo.head.commit
            
            # Check if there were any changes
            if old_commit == new_commit:
                logger.info(f"Repository {self.name} is already up to date")
                self.status = RepoStatus.READY
                return True, []
            
            # Get changed files
            changed_files = self._get_changed_files(old_commit, new_commit)
            
            logger.info(f"Updated repository {self.name} ({len(changed_files)} files changed)")
            self.status = RepoStatus.READY
            return True, changed_files
            
        except GitCommandError as e:
            self.status = RepoStatus.ERROR
            logger.error(f"Failed to update repository {self.name}: {e}")
            return False, None

    def _get_changed_files(self, old_commit: Commit, new_commit: Commit) -> List[str]:
        """Get a list of files that changed between two commits.
        
        Args:
            old_commit: The old commit
            new_commit: The new commit
            
        Returns:
            List of changed file paths
        """
        if not self.repo:
            return []
        
        # Get the diff between the two commits
        diff_index = old_commit.diff(new_commit)
        
        # Collect changed files
        changed_files = []
        for diff_item in diff_index:
            if diff_item.a_path:
                changed_files.append(diff_item.a_path)
            if diff_item.b_path and diff_item.b_path != diff_item.a_path:
                changed_files.append(diff_item.b_path)
        
        return list(set(changed_files))  # Remove duplicates

    def get_last_commit(self) -> Optional[str]:
        """Get the hash of the last commit.
        
        Returns:
            Commit hash or None if repository is not cloned
        """
        if not self.is_cloned() or not self.repo:
            return None
        
        return self.repo.head.commit.hexsha

    def get_commit_time(self, commit_hash: Optional[str] = None) -> Optional[datetime]:
        """Get the timestamp of a commit.
        
        Args:
            commit_hash: Commit hash (defaults to HEAD)
            
        Returns:
            Commit timestamp or None if repository is not cloned
        """
        if not self.is_cloned() or not self.repo:
            return None
        
        try:
            if commit_hash:
                commit = self.repo.commit(commit_hash)
            else:
                commit = self.repo.head.commit
                
            return datetime.fromtimestamp(commit.committed_date)
        except (ValueError, GitCommandError):
            return None
            
    def get_file_commit_hash(self, filepath: str) -> Optional[str]:
        """Get the commit hash for the latest commit that modified a file.
        
        Args:
            filepath: Path to the file within the repository
            
        Returns:
            Commit hash or None if file doesn't exist or repository is not cloned
        """
        if not self.is_cloned() or not self.repo:
            return None
        
        try:
            # Get the latest commit that modified the file
            commits = list(self.repo.iter_commits(paths=filepath, max_count=1))
            if not commits:
                # If no commits found, return the repository's last commit
                return self.get_last_commit()
                
            return commits[0].hexsha
        except (GitCommandError, ValueError):
            # If anything goes wrong, return the repository's last commit
            return self.get_last_commit()

    def get_file_content(self, filepath: str, revision: str = "HEAD") -> Optional[str]:
        """Get the content of a file at a specific revision.
        
        Args:
            filepath: Path to the file within the repository
            revision: Git revision to get the file from (default: HEAD)
            
        Returns:
            File content as string or None if file doesn't exist
        """
        if not self.is_cloned() or not self.repo:
            return None
        
        try:
            # Get the file blob from the specified revision
            blob = self.repo.git.show(f"{revision}:{filepath}")
            return blob
        except GitCommandError:
            return None

    def get_file_history(
        self, filepath: str, max_count: int = 10
    ) -> List[Dict[str, Union[str, datetime]]]:
        """Get the commit history for a specific file.
        
        Args:
            filepath: Path to the file within the repository
            max_count: Maximum number of commits to return
            
        Returns:
            List of commit information dictionaries
        """
        if not self.is_cloned() or not self.repo:
            return []
        
        try:
            # Get commits that modified the file
            commits = list(self.repo.iter_commits(paths=filepath, max_count=max_count))
            
            # Format the result
            history = []
            for commit in commits:
                history.append({
                    "hash": commit.hexsha,
                    "short_hash": commit.hexsha[:7],
                    "message": commit.message.strip(),
                    "author": f"{commit.author.name} <{commit.author.email}>",
                    "date": datetime.fromtimestamp(commit.committed_date),
                })
            
            return history
        except GitCommandError:
            return []

    def get_current_branch(self) -> Optional[str]:
        """Get the current branch name of the repository.
        
        Returns:
            Current branch name or None if repository is not cloned
        """
        if not self.is_cloned() or not self.repo:
            return None
        
        try:
            return self.repo.active_branch.name
        except (TypeError, ValueError, GitCommandError):
            # Handle detached HEAD state or other issues
            return None
    
    def get_repo_stats(self) -> Dict[str, Union[int, str, datetime]]:
        """Get repository statistics.
        
        Returns:
            Dictionary with repository statistics
        """
        if not self.is_cloned() or not self.repo:
            return {
                "status": str(self.status),
                "commit_count": 0,
                "branch_count": 0,
                "contributor_count": 0,
                "size_mb": 0,
            }
        
        repo = self.repo
        
        try:
            # Get commit count
            commit_count = sum(1 for _ in repo.iter_commits())
            
            # Get branch count
            branch_count = len(repo.branches)
            
            # Get contributors
            authors = set()
            for commit in repo.iter_commits(max_count=100):  # Limit to avoid slow operation
                authors.add(f"{commit.author.name} <{commit.author.email}>")
            
            # Get repository size
            repo_size = sum(p.stat().st_size for p in Path(repo.working_dir).glob("**/*") if p.is_file())
            repo_size_mb = repo_size / (1024 * 1024)
            
            return {
                "status": str(self.status),
                "commit_count": commit_count,
                "branch_count": branch_count,
                "contributor_count": len(authors),
                "size_mb": round(repo_size_mb, 2),
                "current_branch": repo.active_branch.name,
                "last_commit": repo.head.commit.hexsha,
                "last_commit_date": datetime.fromtimestamp(repo.head.commit.committed_date),
            }
        except (GitCommandError, ValueError):
            return {
                "status": str(self.status),
                "error": "Failed to get repository statistics",
            }

    def cleanup(self) -> bool:
        """Remove the cloned repository.
        
        Returns:
            True if cleanup succeeded, False otherwise
        """
        if not self.clone_path.exists():
            return True
        
        try:
            # Close the repository to avoid file handle issues
            if self._repo:
                self._repo.close()
                self._repo = None
            
            # Remove the directory
            shutil.rmtree(self.clone_path)
            logger.info(f"Removed repository directory {self.clone_path}")
            return True
        except (OSError, PermissionError) as e:
            logger.error(f"Failed to remove repository directory {self.clone_path}: {e}")
            return False