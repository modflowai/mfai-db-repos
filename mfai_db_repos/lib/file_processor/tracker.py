"""
File status tracking module for incremental repository processing.

This module provides functionality for tracking file status changes between repository updates,
allowing for efficient incremental processing.
"""
import hashlib
import os
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Union

from mfai_db_repos.lib.git.repository import GitRepository
from mfai_db_repos.utils.config import Config
from mfai_db_repos.utils.logger import get_logger

logger = get_logger(__name__)


class FileStatus(str, Enum):
    """File status enum."""
    
    NEW = "new"  # New file added
    MODIFIED = "modified"  # Existing file modified
    DELETED = "deleted"  # File deleted
    RENAMED = "renamed"  # File renamed
    UNCHANGED = "unchanged"  # File unchanged
    UNKNOWN = "unknown"  # Status unknown


class FileStatusEntry:
    """Entry for file status tracking."""
    
    def __init__(
        self,
        path: str,
        status: FileStatus,
        last_modified: Optional[datetime] = None,
        size: Optional[int] = None,
        content_hash: Optional[str] = None,
        old_path: Optional[str] = None,
    ):
        """Initialize a file status entry.
        
        Args:
            path: File path
            status: File status
            last_modified: Last modification time
            size: File size in bytes
            content_hash: Hash of file content
            old_path: Previous path (for renamed files)
        """
        self.path = path
        self.status = status
        self.last_modified = last_modified
        self.size = size
        self.content_hash = content_hash
        self.old_path = old_path
    
    def __str__(self) -> str:
        """String representation of file status entry.
        
        Returns:
            String representation
        """
        result = f"{self.path} ({self.status.value})"
        if self.old_path and self.status == FileStatus.RENAMED:
            result += f" from {self.old_path}"
        return result


class FileStatusTracker:
    """File status tracking class for incremental updates."""
    
    def __init__(
        self,
        config: Optional[Config] = None,
        use_content_hash: bool = True,
        hash_algorithm: str = "md5",
        max_hash_size_mb: float = 10.0,
    ):
        """Initialize a file status tracker.
        
        Args:
            config: Optional Config instance
            use_content_hash: Whether to use content hashing for change detection
            hash_algorithm: Hash algorithm to use (md5, sha1, sha256)
            max_hash_size_mb: Maximum file size in MB to hash
        """
        self.config = config or Config()
        self.use_content_hash = use_content_hash
        self.hash_algorithm = hash_algorithm
        self.max_hash_size_bytes = int(max_hash_size_mb * 1024 * 1024)
        
        # Map of file paths to their status entries
        self.status_cache: Dict[str, FileStatusEntry] = {}
        
        # Last processed commit hash
        self.last_commit_hash: Optional[str] = None
    
    def track_repository(
        self,
        git_repo: GitRepository,
        previous_commit: Optional[str] = None,
        current_commit: Optional[str] = None,
    ) -> List[FileStatusEntry]:
        """Track changes in a repository between commits.
        
        Args:
            git_repo: Git repository instance
            previous_commit: Previous commit hash (uses last tracked if None)
            current_commit: Current commit hash (uses HEAD if None)
            
        Returns:
            List of FileStatusEntry objects for changed files
        """
        if not git_repo.is_cloned() or not git_repo.repo:
            logger.warning("Cannot track repository: not cloned")
            return []
        
        # If previous_commit is not specified, use last tracked commit
        if not previous_commit:
            previous_commit = self.last_commit_hash
        
        # If still no previous commit, track all files as new
        if not previous_commit:
            return self.track_all_files(git_repo)
        
        # Get current commit if not specified
        if not current_commit:
            current_commit = git_repo.get_last_commit()
            if not current_commit:
                logger.warning("Cannot get current commit hash")
                return []
        
        # Update last commit hash
        self.last_commit_hash = current_commit
        
        try:
            # Get changes between commits
            changes = git_repo.get_changes_between_commits(previous_commit, current_commit)
            if not changes:
                logger.info("No changes detected between commits")
                return []
            
            # Process file changes
            changed_files = []
            for change_type, file_path in changes:
                if change_type == "A":  # Added
                    entry = self._track_new_file(git_repo, file_path)
                elif change_type == "M":  # Modified
                    entry = self._track_modified_file(git_repo, file_path)
                elif change_type == "D":  # Deleted
                    entry = self._track_deleted_file(file_path)
                elif change_type == "R":  # Renamed
                    old_path, new_path = file_path.split(" -> ")
                    entry = self._track_renamed_file(git_repo, old_path, new_path)
                else:
                    logger.warning(f"Unknown change type: {change_type} for {file_path}")
                    continue
                
                if entry:
                    changed_files.append(entry)
                    
                    # Update status cache
                    if entry.status == FileStatus.DELETED:
                        if entry.path in self.status_cache:
                            del self.status_cache[entry.path]
                    elif entry.status == FileStatus.RENAMED:
                        if entry.old_path and entry.old_path in self.status_cache:
                            del self.status_cache[entry.old_path]
                        self.status_cache[entry.path] = entry
                    else:
                        self.status_cache[entry.path] = entry
            
            return changed_files
        except Exception as e:
            logger.error(f"Error tracking repository changes: {e}")
            return []
    
    def track_all_files(self, git_repo: GitRepository) -> List[FileStatusEntry]:
        """Track all files in a repository as new.
        
        Args:
            git_repo: Git repository instance
            
        Returns:
            List of FileStatusEntry objects for all files
        """
        if not git_repo.is_cloned() or not git_repo.repo:
            logger.warning("Cannot track repository: not cloned")
            return []
        
        # Get current commit
        current_commit = git_repo.get_last_commit()
        if current_commit:
            self.last_commit_hash = current_commit
        
        try:
            # Get all files in the repository
            repo_path = Path(git_repo.repo.working_dir)
            all_files = []
            
            for root, _, files in os.walk(repo_path):
                # Skip .git directory
                if ".git" in Path(root).parts:
                    continue
                
                # Process files
                for filename in files:
                    filepath = Path(root) / filename
                    rel_path = str(filepath.relative_to(repo_path))
                    
                    entry = self._track_new_file(git_repo, rel_path)
                    if entry:
                        all_files.append(entry)
                        self.status_cache[entry.path] = entry
            
            return all_files
        except Exception as e:
            logger.error(f"Error tracking all files: {e}")
            return []
    
    def track_directory(
        self,
        directory_path: Union[str, Path],
        baseline: Optional[Dict[str, FileStatusEntry]] = None,
    ) -> List[FileStatusEntry]:
        """Track changes in a directory compared to a baseline.
        
        Args:
            directory_path: Path to directory
            baseline: Baseline status cache (uses current cache if None)
            
        Returns:
            List of FileStatusEntry objects for changed files
        """
        directory_path = Path(directory_path)
        if not directory_path.exists() or not directory_path.is_dir():
            logger.warning(f"Cannot track directory: {directory_path} does not exist")
            return []
        
        # Use current cache as baseline if not specified
        if baseline is None:
            baseline = self.status_cache.copy()
        
        try:
            # Get all files in the directory
            current_files = set()
            changed_files = []
            
            for root, _, files in os.walk(directory_path):
                for filename in files:
                    filepath = Path(root) / filename
                    rel_path = str(filepath.relative_to(directory_path))
                    current_files.add(rel_path)
                    
                    if rel_path in baseline:
                        # Check if file was modified
                        baseline_entry = baseline[rel_path]
                        stat = filepath.stat()
                        
                        # Check modification time and size
                        if (stat.st_mtime != baseline_entry.last_modified.timestamp() or
                            stat.st_size != baseline_entry.size):
                            
                            # Check content hash if enabled
                            if self.use_content_hash and baseline_entry.content_hash:
                                current_hash = self._compute_file_hash(filepath)
                                if current_hash != baseline_entry.content_hash:
                                    entry = self._create_status_entry(
                                        filepath, 
                                        rel_path, 
                                        FileStatus.MODIFIED
                                    )
                                    changed_files.append(entry)
                                    self.status_cache[rel_path] = entry
                            else:
                                entry = self._create_status_entry(
                                    filepath, 
                                    rel_path, 
                                    FileStatus.MODIFIED
                                )
                                changed_files.append(entry)
                                self.status_cache[rel_path] = entry
                    else:
                        # New file
                        entry = self._create_status_entry(
                            filepath, 
                            rel_path, 
                            FileStatus.NEW
                        )
                        changed_files.append(entry)
                        self.status_cache[rel_path] = entry
            
            # Check for deleted files
            for path in set(baseline.keys()) - current_files:
                entry = FileStatusEntry(
                    path=path,
                    status=FileStatus.DELETED,
                )
                changed_files.append(entry)
                if path in self.status_cache:
                    del self.status_cache[path]
            
            return changed_files
        except Exception as e:
            logger.error(f"Error tracking directory changes: {e}")
            return []
    
    def _track_new_file(
        self,
        git_repo: GitRepository,
        file_path: str,
    ) -> Optional[FileStatusEntry]:
        """Track a new file.
        
        Args:
            git_repo: Git repository instance
            file_path: File path relative to repository root
            
        Returns:
            FileStatusEntry for the new file or None if error
        """
        if not git_repo.is_cloned() or not git_repo.repo:
            return None
        
        repo_path = Path(git_repo.repo.working_dir)
        abs_path = repo_path / file_path
        
        if not abs_path.exists() or not abs_path.is_file():
            logger.warning(f"Cannot track new file: {file_path} does not exist")
            return None
        
        return self._create_status_entry(abs_path, file_path, FileStatus.NEW)
    
    def _track_modified_file(
        self,
        git_repo: GitRepository,
        file_path: str,
    ) -> Optional[FileStatusEntry]:
        """Track a modified file.
        
        Args:
            git_repo: Git repository instance
            file_path: File path relative to repository root
            
        Returns:
            FileStatusEntry for the modified file or None if error
        """
        if not git_repo.is_cloned() or not git_repo.repo:
            return None
        
        repo_path = Path(git_repo.repo.working_dir)
        abs_path = repo_path / file_path
        
        if not abs_path.exists() or not abs_path.is_file():
            logger.warning(f"Cannot track modified file: {file_path} does not exist")
            return None
        
        return self._create_status_entry(abs_path, file_path, FileStatus.MODIFIED)
    
    def _track_deleted_file(self, file_path: str) -> FileStatusEntry:
        """Track a deleted file.
        
        Args:
            file_path: File path relative to repository root
            
        Returns:
            FileStatusEntry for the deleted file
        """
        return FileStatusEntry(
            path=file_path,
            status=FileStatus.DELETED,
        )
    
    def _track_renamed_file(
        self,
        git_repo: GitRepository,
        old_path: str,
        new_path: str,
    ) -> Optional[FileStatusEntry]:
        """Track a renamed file.
        
        Args:
            git_repo: Git repository instance
            old_path: Old file path
            new_path: New file path
            
        Returns:
            FileStatusEntry for the renamed file or None if error
        """
        if not git_repo.is_cloned() or not git_repo.repo:
            return None
        
        repo_path = Path(git_repo.repo.working_dir)
        abs_path = repo_path / new_path
        
        if not abs_path.exists() or not abs_path.is_file():
            logger.warning(f"Cannot track renamed file: {new_path} does not exist")
            return None
        
        # Create entry for renamed file
        entry = self._create_status_entry(abs_path, new_path, FileStatus.RENAMED)
        if entry:
            entry.old_path = old_path
        
        return entry
    
    def _create_status_entry(
        self,
        abs_path: Path,
        rel_path: str,
        status: FileStatus,
    ) -> Optional[FileStatusEntry]:
        """Create a file status entry.
        
        Args:
            abs_path: Absolute file path
            rel_path: File path relative to repository root
            status: File status
            
        Returns:
            FileStatusEntry or None if error
        """
        try:
            stat = abs_path.stat()
            
            # Compute content hash if enabled
            content_hash = None
            if self.use_content_hash and stat.st_size <= self.max_hash_size_bytes:
                content_hash = self._compute_file_hash(abs_path)
            
            return FileStatusEntry(
                path=rel_path,
                status=status,
                last_modified=datetime.fromtimestamp(stat.st_mtime),
                size=stat.st_size,
                content_hash=content_hash,
            )
        except Exception as e:
            logger.warning(f"Error creating status entry for {rel_path}: {e}")
            return None
    
    def _compute_file_hash(self, filepath: Path) -> Optional[str]:
        """Compute a hash of file content.
        
        Args:
            filepath: Path to the file
            
        Returns:
            Content hash string or None if error
        """
        try:
            # Choose hash algorithm
            if self.hash_algorithm == "md5":
                hasher = hashlib.md5()
            elif self.hash_algorithm == "sha1":
                hasher = hashlib.sha1()
            elif self.hash_algorithm == "sha256":
                hasher = hashlib.sha256()
            else:
                hasher = hashlib.md5()  # Default to MD5
            
            # Read and hash file in chunks
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            
            return hasher.hexdigest()
        except Exception as e:
            logger.warning(f"Error computing hash for {filepath}: {e}")
            return None
    
    def get_status_entry(self, file_path: str) -> Optional[FileStatusEntry]:
        """Get status entry for a file.
        
        Args:
            file_path: File path
            
        Returns:
            FileStatusEntry or None if not found
        """
        return self.status_cache.get(file_path)
    
    def get_all_status_entries(self) -> Dict[str, FileStatusEntry]:
        """Get all status entries.
        
        Returns:
            Dictionary of file paths to FileStatusEntry objects
        """
        return self.status_cache.copy()
    
    def clear_cache(self) -> None:
        """Clear the status cache."""
        self.status_cache.clear()
        self.last_commit_hash = None
    
    def save_cache(self, cache_file: Union[str, Path]) -> bool:
        """Save the status cache to a file.
        
        Args:
            cache_file: Path to cache file
            
        Returns:
            True if successful, False otherwise
        """
        # TODO: Implement cache serialization
        return False
    
    def load_cache(self, cache_file: Union[str, Path]) -> bool:
        """Load the status cache from a file.
        
        Args:
            cache_file: Path to cache file
            
        Returns:
            True if successful, False otherwise
        """
        # TODO: Implement cache deserialization
        return False