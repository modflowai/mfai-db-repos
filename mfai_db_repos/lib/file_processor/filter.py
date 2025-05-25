"""
File type selection and filtering module.

This module provides functionality for selecting and filtering files based on
various criteria such as file type, extension, and content patterns.
"""
import fnmatch
import re
from pathlib import Path
from typing import Dict, List, Optional, Union

from mfai_db_repos.utils.config import config
from mfai_db_repos.utils.logger import get_logger

logger = get_logger(__name__)


class FileTypeDetector:
    """File type detection class."""

    # Common file extensions by type
    FILE_TYPE_EXTENSIONS: Dict[str, List[str]] = {
        "source_code": [
            # Python
            ".py", ".pyi", ".pyx", ".pxd", ".pxi",
            # JavaScript / TypeScript
            ".js", ".jsx", ".ts", ".tsx",
            # Java
            ".java", ".kt", ".groovy",
            # C / C++
            ".c", ".h", ".cpp", ".hpp", ".cc", ".cxx",
            # C#
            ".cs",
            # Ruby
            ".rb",
            # Go
            ".go",
            # Rust
            ".rs",
            # PHP
            ".php",
            # Swift
            ".swift",
            # Other languages
            ".scala", ".clj", ".erl", ".ex", ".exs", ".elm", ".hs", ".lua", ".r",
        ],
        "web": [
            ".html", ".htm", ".css", ".scss", ".sass", ".less", ".jsp", ".asp", ".aspx",
        ],
        "data": [
            ".json", ".xml", ".yml", ".yaml", ".toml", ".csv", ".tsv", ".sql", ".graphql",
        ],
        "documentation": [
            ".md", ".rst", ".txt", ".tex", ".adoc", ".wiki", ".org", ".rtf", ".docx", ".pdf",
        ],
        "configuration": [
            ".ini", ".cfg", ".conf", ".config", ".properties", ".env", ".rc",
        ],
        "script": [
            ".sh", ".bash", ".zsh", ".ps1", ".bat", ".cmd",
        ],
        "markup": [
            ".svg", ".tex", ".sgml", ".dtd", ".xhtml", ".jinja", ".j2", ".tmpl",
        ],
        "binary": [
            # Executables
            ".exe", ".dll", ".so", ".dylib", ".bin",
            # Archives
            ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
            # Images
            ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".ico",
            # Audio
            ".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a",
            # Video
            ".mp4", ".avi", ".mkv", ".mov", ".webm", ".flv",
            # Other binary
            ".pdf", ".docx", ".xlsx", ".pptx", ".class", ".pyc", ".pyo", ".wasm",
        ],
    }

    # Mapping from language/format to broader category
    FILE_TYPE_CATEGORIES: Dict[str, str] = {
        # Programming languages
        "python": "source_code",
        "javascript": "source_code",
        "typescript": "source_code",
        "java": "source_code",
        "c": "source_code",
        "c++": "source_code",
        "c#": "source_code",
        "go": "source_code",
        "rust": "source_code",
        "ruby": "source_code",
        "php": "source_code",
        "swift": "source_code",
        "kotlin": "source_code",
        "scala": "source_code",
        # Web
        "html": "web",
        "css": "web",
        "scss": "web",
        "sass": "web",
        "less": "web",
        # Data
        "json": "data",
        "xml": "data",
        "yaml": "data",
        "toml": "data",
        "csv": "data",
        "sql": "data",
        "graphql": "data",
        # Documentation
        "markdown": "documentation",
        "rst": "documentation",
        "text": "documentation",
        "latex": "documentation",
        # Configuration
        "config": "configuration",
        "ini": "configuration",
        "properties": "configuration",
        # Scripts
        "shell": "script",
        "batch": "script",
        "powershell": "script",
        # Binary
        "binary": "binary",
        "image": "binary",
        "audio": "binary",
        "video": "binary",
    }

    def __init__(self):
        """Initialize a file type detector."""

    def detect_file_type(self, filepath: Union[str, Path]) -> str:
        """Detect the file type based on extension.

        Args:
            filepath: Path to the file

        Returns:
            File type string
        """
        filepath = Path(filepath)
        extension = filepath.suffix.lower()
        
        # Check if it's a binary extension
        for file_type, extensions in self.FILE_TYPE_EXTENSIONS.items():
            if extension in extensions:
                return file_type
        
        # If no match by extension, try to guess by filename
        filename = filepath.name.lower()
        
        # Check for common filenames
        if filename in ["readme", "readme.md", "readme.txt"]:
            return "documentation"
        elif filename in ["license", "license.txt", "copying", "copyright"]:
            return "documentation"
        elif filename in ["dockerfile", "makefile", "gemfile", "rakefile"]:
            return "configuration"
        elif filename in [".gitignore", ".dockerignore", ".gitattributes"]:
            return "configuration"
        
        # Default to unknown
        return "unknown"

    def get_category_for_file_type(self, file_type: str) -> str:
        """Get the broader category for a specific file type.

        Args:
            file_type: File type string

        Returns:
            Category string
        """
        if file_type in self.FILE_TYPE_CATEGORIES:
            return self.FILE_TYPE_CATEGORIES[file_type]
        
        # Look for partial match
        for known_type, category in self.FILE_TYPE_CATEGORIES.items():
            if known_type in file_type or file_type in known_type:
                return category
        
        return "unknown"


class FileFilter:
    """File filtering class for selecting files based on various criteria."""

    def __init__(
        self,
        include_types: Optional[List[str]] = None,
        exclude_types: Optional[List[str]] = None,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        max_file_size_mb: Optional[float] = None,
    ):
        """Initialize a file filter.

        Args:
            include_types: List of file types to include
            exclude_types: List of file types to exclude
            include_patterns: List of glob patterns to include
            exclude_patterns: List of glob patterns to exclude
            max_file_size_mb: Maximum file size to process in MB
        """
        file_filter_config = config.config.file_filter
        
        self.include_types = include_types
        self.exclude_types = exclude_types or ["binary"]
        self.include_patterns = include_patterns or file_filter_config.include_patterns
        self.exclude_patterns = exclude_patterns or file_filter_config.exclude_patterns
        self.max_file_size_bytes = (max_file_size_mb or file_filter_config.max_file_size_mb) * 1024 * 1024
        
        # Initialize file type detector
        self.type_detector = FileTypeDetector()

    def should_process_file(self, filepath: Union[str, Path]) -> bool:
        """Check if a file should be processed based on all criteria.

        Args:
            filepath: Path to the file

        Returns:
            True if the file should be processed, False otherwise
        """
        filepath = Path(filepath)
        
        # Check if file exists
        if not filepath.exists():
            return False
        
        # Check file size
        if self.max_file_size_bytes > 0 and filepath.stat().st_size > self.max_file_size_bytes:
            logger.debug(f"Skipping {filepath} due to size ({filepath.stat().st_size} bytes)")
            return False
        
        # Check file type
        file_type = self.type_detector.detect_file_type(filepath)
        
        # Check include/exclude types
        if self.include_types and file_type not in self.include_types:
            logger.debug(f"Skipping {filepath} due to type not in include list")
            return False
        
        if self.exclude_types and file_type in self.exclude_types:
            logger.debug(f"Skipping {filepath} due to type in exclude list")
            return False
        
        # Check patterns
        if not self._matches_patterns(filepath):
            logger.debug(f"Skipping {filepath} due to pattern mismatch")
            return False
        
        return True

    def _matches_patterns(self, filepath: Path) -> bool:
        """Check if a file path matches the include/exclude patterns.

        Args:
            filepath: Path to check

        Returns:
            True if the file should be included, False otherwise
        """
        # Convert to string for pattern matching
        filepath_str = str(filepath)
        
        # Check exclude patterns
        for pattern in self.exclude_patterns:
            if self._matches_glob_pattern(filepath_str, pattern):
                return False
        
        # If no include patterns, include all files
        if not self.include_patterns:
            return True
        
        # Check include patterns
        for pattern in self.include_patterns:
            if self._matches_glob_pattern(filepath_str, pattern):
                return True
        
        # No match found
        return False

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

    def filter_files(
        self,
        file_paths: List[Union[str, Path]],
        base_path: Optional[Union[str, Path]] = None,
    ) -> List[Path]:
        """Filter a list of files based on the configured criteria.

        Args:
            file_paths: List of file paths to filter
            base_path: Base path for relative paths (if needed)

        Returns:
            List of filtered file paths
        """
        filtered_paths = []
        
        for filepath in file_paths:
            # Convert to Path objects
            path = Path(filepath)
            
            # Make absolute if base_path is provided
            if base_path:
                abs_path = Path(base_path) / path
            else:
                abs_path = path.resolve()
            
            # Check if the file should be processed
            if self.should_process_file(abs_path):
                filtered_paths.append(abs_path)
        
        return filtered_paths