"""
Ignore pattern management module.

This module provides functionality for managing and applying ignore patterns for 
repository processing, similar to how .gitignore works.
"""
import fnmatch
import os
import re
from pathlib import Path
from typing import List, Optional, Union

from mfai_db_repos.utils.config import Config
from mfai_db_repos.utils.logger import get_logger

logger = get_logger(__name__)


class IgnorePattern:
    """Pattern for ignoring files and directories."""
    
    def __init__(
        self,
        pattern: str,
        negated: bool = False,
        directory_only: bool = False,
        comment: Optional[str] = None,
    ):
        """Initialize an ignore pattern.
        
        Args:
            pattern: Glob pattern
            negated: Whether the pattern is negated (exception)
            directory_only: Whether the pattern applies only to directories
            comment: Optional comment about the pattern
        """
        self.pattern = pattern
        self.negated = negated
        self.directory_only = directory_only
        self.comment = comment
        
        # Prepare regex pattern for matching
        self._prepare_regex()
    
    def _prepare_regex(self) -> None:
        """Prepare the regex pattern for matching."""
        pattern = self.pattern
        
        # Handle directory-only patterns
        if pattern.endswith('/'):
            self.directory_only = True
            pattern = pattern[:-1]
        
        # Convert glob pattern to regex
        regex = fnmatch.translate(pattern)
        
        # Handle anchoring
        if pattern.startswith('/'):
            # Anchored to repo root
            regex = f"^{regex[1:]}"
        elif '/' in pattern:
            # Contains a slash but not anchored, should match anywhere in the path
            regex = f".*{regex}"
        else:
            # Simple filename pattern, should match the end of the path
            regex = f".*{os.path.sep}{regex}"
        
        self._regex = re.compile(regex)
    
    def matches(self, path: Union[str, Path], is_dir: bool = False) -> bool:
        """Check if the pattern matches a path.
        
        Args:
            path: Path to check
            is_dir: Whether the path is a directory
            
        Returns:
            True if the pattern matches the path
        """
        # If pattern is for directories only and path is not a directory
        if self.directory_only and not is_dir:
            return False
        
        # Convert path to string for matching
        path_str = str(path)
        
        # Replace backslashes with forward slashes for consistent matching
        path_str = path_str.replace('\\', '/')
        
        # Check if the pattern matches
        return bool(self._regex.match(path_str))
    
    def __str__(self) -> str:
        """String representation of the pattern.
        
        Returns:
            String representation
        """
        parts = []
        if self.negated:
            parts.append("!")
        
        parts.append(self.pattern)
        
        if self.directory_only:
            parts.append(" (directory only)")
        
        if self.comment:
            parts.append(f" # {self.comment}")
        
        return "".join(parts)


class IgnoreManager:
    """Manager for ignore patterns."""
    
    # Common ignore patterns by category
    COMMON_IGNORES = {
        "git": [
            ".git/",
            ".gitignore",
            ".gitattributes",
            ".gitmodules",
            ".github/",
        ],
        "ide": [
            ".idea/",
            ".vscode/",
            "*.swp",
            "*.swo",
            ".DS_Store",
            "Thumbs.db",
            "*.sublime*",
        ],
        "python": [
            "__pycache__/",
            "*.py[cod]",
            "*$py.class",
            "*.so",
            ".Python",
            "env/",
            "venv/",
            ".venv/",
            "ENV/",
            ".pytest_cache/",
            ".coverage",
            "htmlcov/",
            "*.egg-info/",
            "dist/",
            "build/",
        ],
        "tests": [
            "test/",
            "tests/",
            "*/test/",
            "*/tests/",
            "*_test.py",
            "*_tests.py",
            "test_*.py",
        ],
        "javascript": [
            "node_modules/",
            "bower_components/",
            "jspm_packages/",
            "package-lock.json",
            "yarn.lock",
            "npm-debug.log*",
            "yarn-debug.log*",
            "yarn-error.log*",
            ".npm",
            "dist/",
            "build/",
            "*.min.js",
        ],
        "java": [
            "*.class",
            "*.jar",
            "*.war",
            "*.ear",
            "*.log",
            "target/",
            ".gradle/",
            "build/",
            "out/",
        ],
        "binary": [
            "*.exe",
            "*.dll",
            "*.so",
            "*.dylib",
            "*.obj",
            "*.o",
            "*.a",
            "*.lib",
            "*.bin",
        ],
        "media": [
            "*.jpg",
            "*.jpeg",
            "*.png",
            "*.gif",
            "*.bmp",
            "*.tiff",
            "*.ico",
            "*.mp3",
            "*.wav",
            "*.mp4",
            "*.avi",
            "*.mov",
            "*.webm",
            "*.flv",
            "*.ogg",
            "*.pdf",
        ],
        "documentation": [
            "LICENSE",
            "LICENSE.txt",
            "LICENSE.md",
            "COPYING",
            "CONTRIBUTING.md",
            "CHANGELOG.md",
            "HISTORY.md",
            "AUTHORS",
            "CODEOWNERS",
        ],
    }
    
    def __init__(
        self,
        config: Optional[Config] = None,
        default_ignores: Optional[List[str]] = None,
        ignore_case: bool = True,
    ):
        """Initialize an ignore manager.
        
        Args:
            config: Optional Config instance
            default_ignores: List of default ignore patterns
            ignore_case: Whether to ignore case when matching
        """
        self.config = config or Config()
        self.patterns: List[IgnorePattern] = []
        self.ignore_case = ignore_case
        
        # Add default ignore patterns
        if default_ignores:
            self.add_patterns(default_ignores)
        else:
            # Add commonly ignored files by default
            self.add_common_ignores(["git", "ide"])
    
    def add_pattern(self, pattern: str, comment: Optional[str] = None) -> None:
        """Add an ignore pattern.
        
        Args:
            pattern: Glob pattern
            comment: Optional comment about the pattern
        """
        # Skip empty lines and comments
        pattern = pattern.strip()
        if not pattern or pattern.startswith('#'):
            return
        
        # Handle negated patterns
        negated = pattern.startswith('!')
        if negated:
            pattern = pattern[1:].strip()
            if not pattern:
                return
        
        # Handle directory-only patterns
        directory_only = pattern.endswith('/')
        
        # Add pattern
        ignore_pattern = IgnorePattern(
            pattern=pattern,
            negated=negated,
            directory_only=directory_only,
            comment=comment,
        )
        
        self.patterns.append(ignore_pattern)
        logger.debug(f"Added ignore pattern: {ignore_pattern}")
    
    def add_patterns(self, patterns: List[str]) -> None:
        """Add multiple ignore patterns.
        
        Args:
            patterns: List of glob patterns
        """
        for pattern in patterns:
            self.add_pattern(pattern)
    
    def add_common_ignores(self, categories: List[str]) -> None:
        """Add common ignore patterns by category.
        
        Args:
            categories: List of categories to add
        """
        for category in categories:
            if category in self.COMMON_IGNORES:
                for pattern in self.COMMON_IGNORES[category]:
                    self.add_pattern(pattern, f"Common {category} ignore")
            else:
                logger.warning(f"Unknown ignore category: {category}")
    
    def parse_gitignore(self, gitignore_path: Union[str, Path]) -> None:
        """Parse patterns from a .gitignore file.
        
        Args:
            gitignore_path: Path to .gitignore file
        """
        gitignore_path = Path(gitignore_path)
        if not gitignore_path.exists() or not gitignore_path.is_file():
            logger.warning(f"Cannot parse .gitignore: {gitignore_path} does not exist")
            return
        
        try:
            with open(gitignore_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Extract comment if present
                    comment = None
                    if '#' in line:
                        line, comment = line.split('#', 1)
                        line = line.strip()
                        comment = comment.strip()
                    
                    # Add pattern
                    self.add_pattern(line, comment)
                    
            logger.info(f"Parsed ignore patterns from {gitignore_path}")
        except Exception as e:
            logger.error(f"Error parsing .gitignore {gitignore_path}: {e}")
    
    def parse_gitignore_in_repo(self, repo_path: Union[str, Path]) -> None:
        """Parse all .gitignore files in a repository.
        
        Args:
            repo_path: Path to repository
        """
        repo_path = Path(repo_path)
        if not repo_path.exists() or not repo_path.is_dir():
            logger.warning(f"Cannot parse .gitignore files: {repo_path} does not exist")
            return
        
        # Parse root .gitignore
        root_gitignore = repo_path / ".gitignore"
        if root_gitignore.exists():
            self.parse_gitignore(root_gitignore)
        
        # Parse subdirectory .gitignore files
        for root, _, files in os.walk(repo_path):
            # Skip .git directory
            if ".git" in Path(root).parts:
                continue
            
            for filename in files:
                if filename == ".gitignore" and root != str(repo_path):
                    gitignore_path = Path(root) / filename
                    self.parse_gitignore(gitignore_path)
    
    def should_ignore(self, path: Union[str, Path], is_dir: bool = False) -> bool:
        """Check if a path should be ignored.
        
        Args:
            path: Path to check
            is_dir: Whether the path is a directory
            
        Returns:
            True if the path should be ignored
        """
        path = Path(path)
        
        # Get parts of the path for accurate matching
        parts = path.parts
        
        # Iterate through patterns in reverse (last one wins)
        should_ignore = False
        
        for pattern in reversed(self.patterns):
            if pattern.matches(path, is_dir):
                if pattern.negated:
                    # Found a negated pattern that matches, don't ignore
                    return False
                else:
                    # Found a pattern that matches, should ignore unless negated later
                    should_ignore = True
        
        return should_ignore
    
    def filter_paths(
        self,
        paths: List[Union[str, Path]],
        repo_path: Optional[Union[str, Path]] = None,
    ) -> List[Path]:
        """Filter a list of paths using ignore patterns.
        
        Args:
            paths: List of paths to filter
            repo_path: Repository root path for relative paths
            
        Returns:
            List of non-ignored paths
        """
        filtered_paths = []
        
        for path in paths:
            path = Path(path)
            
            # Make absolute path if repo_path is provided
            if repo_path:
                if not path.is_absolute():
                    abs_path = Path(repo_path) / path
                else:
                    abs_path = path
            else:
                abs_path = path.absolute()
            
            # Check if path should be ignored
            is_dir = abs_path.is_dir() if abs_path.exists() else False
            if not self.should_ignore(path, is_dir):
                filtered_paths.append(path)
        
        return filtered_paths