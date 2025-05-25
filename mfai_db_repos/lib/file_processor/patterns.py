"""
Configurable inclusion/exclusion patterns module.

This module provides functionality for managing and applying file inclusion/exclusion patterns
for repository processing.
"""
import fnmatch
import re
from pathlib import Path
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field

from mfai_db_repos.utils.config import config
from mfai_db_repos.utils.logger import get_logger

logger = get_logger(__name__)


class PatternConfig(BaseModel):
    """Configurable pattern set for repository processing."""

    name: str = Field(..., description="Pattern config name")
    description: Optional[str] = Field(None, description="Pattern config description")
    include_patterns: List[str] = Field(default_factory=list, description="Glob patterns to include")
    exclude_patterns: List[str] = Field(default_factory=list, description="Glob patterns to exclude")
    include_extensions: List[str] = Field(default_factory=list, description="File extensions to include")
    exclude_extensions: List[str] = Field(default_factory=list, description="File extensions to exclude")
    include_types: List[str] = Field(default_factory=list, description="File types to include")
    exclude_types: List[str] = Field(default_factory=list, description="File types to exclude")


class PatternManager:
    """Pattern manager for configurable inclusion/exclusion patterns."""

    # Common preset patterns
    PRESET_PATTERNS: Dict[str, PatternConfig] = {
        "all_code": PatternConfig(
            name="all_code",
            description="All source code files",
            include_types=["source_code"],
            exclude_patterns=["**/.git/**", "**/node_modules/**", "**/__pycache__/**"],
        ),
        "python_only": PatternConfig(
            name="python_only",
            description="Python source files only",
            include_extensions=[".py", ".pyi", ".pyx"],
            exclude_patterns=["**/.git/**", "**/__pycache__/**", "**/.venv/**", "**/venv/**"],
        ),
        "javascript_only": PatternConfig(
            name="javascript_only",
            description="JavaScript/TypeScript source files only",
            include_extensions=[".js", ".jsx", ".ts", ".tsx"],
            exclude_patterns=["**/.git/**", "**/node_modules/**", "**/dist/**", "**/build/**"],
        ),
        "documentation": PatternConfig(
            name="documentation",
            description="Documentation files only",
            include_types=["documentation"],
            include_patterns=["**/README*", "**/docs/**"],
            exclude_patterns=["**/.git/**", "**/node_modules/**"],
        ),
        "config_files": PatternConfig(
            name="config_files",
            description="Configuration files only",
            include_types=["configuration"],
            include_patterns=["**/*.json", "**/*.yml", "**/*.yaml", "**/*.toml", "**/*.ini", "**/*.conf"],
            exclude_patterns=["**/.git/**", "**/node_modules/**"],
        ),
    }

    def __init__(self):
        """Initialize a pattern manager."""
        # Load default patterns from config
        file_filter_config = config.config.file_filter
        self.default_include_patterns = file_filter_config.include_patterns
        self.default_exclude_patterns = file_filter_config.exclude_patterns
        
        # Copy preset patterns
        self.patterns = self.PRESET_PATTERNS.copy()

    def add_pattern_config(self, pattern_config: PatternConfig) -> None:
        """Add a new pattern configuration.

        Args:
            pattern_config: Pattern configuration to add
        """
        self.patterns[pattern_config.name] = pattern_config
        logger.info(f"Added pattern configuration: {pattern_config.name}")

    def get_pattern_config(self, name: str) -> Optional[PatternConfig]:
        """Get a pattern configuration by name.

        Args:
            name: Pattern configuration name

        Returns:
            Pattern configuration or None if not found
        """
        return self.patterns.get(name)

    def list_pattern_configs(self) -> List[PatternConfig]:
        """List all available pattern configurations.

        Returns:
            List of pattern configurations
        """
        return list(self.patterns.values())

    def remove_pattern_config(self, name: str) -> bool:
        """Remove a pattern configuration.

        Args:
            name: Pattern configuration name

        Returns:
            True if removed, False if not found
        """
        if name in self.patterns:
            del self.patterns[name]
            logger.info(f"Removed pattern configuration: {name}")
            return True
        return False

    def filter_files(
        self,
        files: List[Union[str, Path]],
        pattern_config_name: Optional[str] = None,
    ) -> List[Path]:
        """Filter files based on a pattern configuration.

        Args:
            files: List of file paths to filter
            pattern_config_name: Pattern configuration name (uses default if None)

        Returns:
            List of filtered file paths
        """
        # Use specified pattern config or default
        if pattern_config_name and pattern_config_name in self.patterns:
            pattern_config = self.patterns[pattern_config_name]
            logger.info(f"Using pattern configuration: {pattern_config_name}")
        else:
            # Use default patterns from config
            pattern_config = PatternConfig(
                name="default",
                description="Default patterns from config",
                include_patterns=self.default_include_patterns,
                exclude_patterns=self.default_exclude_patterns,
            )
            logger.info("Using default pattern configuration")
        
        # Convert all paths to Path objects
        paths = [Path(f) for f in files]
        filtered_paths = []
        
        for path in paths:
            # Check extensions
            if pattern_config.include_extensions:
                ext = path.suffix.lower()
                if ext not in pattern_config.include_extensions:
                    continue
            
            if pattern_config.exclude_extensions:
                ext = path.suffix.lower()
                if ext in pattern_config.exclude_extensions:
                    continue
            
            # Check patterns
            path_str = str(path)
            
            # Check exclude patterns
            excluded = False
            for pattern in pattern_config.exclude_patterns:
                if self._matches_glob_pattern(path_str, pattern):
                    excluded = True
                    break
            
            if excluded:
                continue
            
            # Check include patterns
            if pattern_config.include_patterns:
                included = False
                for pattern in pattern_config.include_patterns:
                    if self._matches_glob_pattern(path_str, pattern):
                        included = True
                        break
                
                if not included:
                    continue
            
            # Add to filtered paths
            filtered_paths.append(path)
        
        logger.info(f"Filtered {len(paths)} files to {len(filtered_paths)} files")
        return filtered_paths

    def _matches_glob_pattern(self, filepath: str, pattern: str) -> bool:
        """Check if a filepath matches a glob pattern.

        Args:
            filepath: Path to check
            pattern: Glob pattern

        Returns:
            True if the path matches the pattern, False otherwise
        """
        # Handle recursive glob patterns (**, which isn't natively supported in fnmatch)
        if "**" in pattern:
            # Convert ** to a regex pattern
            regex_pattern = pattern.replace(".", r"\.").replace("**", ".*").replace("*", "[^/]*").replace("?", ".")
            regex_pattern = f"^{regex_pattern}$"
            return bool(re.match(regex_pattern, filepath))
        else:
            # Use fnmatch for simple patterns
            return fnmatch.fnmatch(filepath, pattern)


class PatternSet:
    """Pattern set for specifying file inclusion/exclusion criteria."""

    def __init__(
        self,
        name: str,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        include_extensions: Optional[List[str]] = None,
        exclude_extensions: Optional[List[str]] = None,
        include_types: Optional[List[str]] = None,
        exclude_types: Optional[List[str]] = None,
    ):
        """Initialize a pattern set.

        Args:
            name: Pattern set name
            include_patterns: Glob patterns to include
            exclude_patterns: Glob patterns to exclude
            include_extensions: File extensions to include
            exclude_extensions: File extensions to exclude
            include_types: File types to include
            exclude_types: File types to exclude
        """
        self.name = name
        self.include_patterns = include_patterns or []
        self.exclude_patterns = exclude_patterns or []
        self.include_extensions = include_extensions or []
        self.exclude_extensions = exclude_extensions or []
        self.include_types = include_types or []
        self.exclude_types = exclude_types or []

    def to_pattern_config(self) -> PatternConfig:
        """Convert to a PatternConfig object.

        Returns:
            PatternConfig object
        """
        return PatternConfig(
            name=self.name,
            include_patterns=self.include_patterns,
            exclude_patterns=self.exclude_patterns,
            include_extensions=self.include_extensions,
            exclude_extensions=self.exclude_extensions,
            include_types=self.include_types,
            exclude_types=self.exclude_types,
        )

    def matches_file(self, filepath: Union[str, Path], file_type: Optional[str] = None) -> bool:
        """Check if a file matches this pattern set.

        Args:
            filepath: Path to check
            file_type: Optional file type

        Returns:
            True if the file matches, False otherwise
        """
        filepath = Path(filepath)
        filepath_str = str(filepath)
        
        # Check extensions
        if self.include_extensions:
            ext = filepath.suffix.lower()
            if ext not in self.include_extensions:
                return False
        
        if self.exclude_extensions:
            ext = filepath.suffix.lower()
            if ext in self.exclude_extensions:
                return False
        
        # Check file type if provided
        if file_type:
            if self.include_types and file_type not in self.include_types:
                return False
            
            if self.exclude_types and file_type in self.exclude_types:
                return False
        
        # Check exclude patterns
        for pattern in self.exclude_patterns:
            if PatternManager()._matches_glob_pattern(filepath_str, pattern):
                return False
        
        # Check include patterns
        if self.include_patterns:
            for pattern in self.include_patterns:
                if PatternManager()._matches_glob_pattern(filepath_str, pattern):
                    return True
            return False  # No include pattern matched
        
        # If no include patterns, include all files that weren't excluded
        return True