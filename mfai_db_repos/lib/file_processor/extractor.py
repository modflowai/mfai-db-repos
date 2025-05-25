"""
File extraction and content parsing module.

This module provides functionality for extracting and processing file content from repositories.
"""
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

import chardet
import magic
from mfai_db_repos.utils.env import get_float_env
from mfai_db_repos.utils.logger import get_logger

logger = get_logger(__name__)


class FileExtractor:
    """File content extraction and processing class."""

    # Common binary file extensions to skip without content analysis
    BINARY_EXTENSIONS = {
        # Images
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".ico", ".svg",
        # Audio
        ".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a",
        # Video
        ".mp4", ".avi", ".mkv", ".mov", ".webm", ".flv",
        # Archives
        ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
        # Executables
        ".exe", ".dll", ".so", ".dylib", ".bin",
        # Miscellaneous
        ".pdf", ".docx", ".xlsx", ".pptx", ".class", ".pyc",
    }

    # Common text file extensions with their types
    TEXT_EXTENSIONS: Dict[str, str] = {
        # Programming languages
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".java": "java",
        ".c": "c",
        ".cpp": "c++",
        ".h": "c_header",
        ".hpp": "c++_header",
        ".cs": "csharp",
        ".go": "go",
        ".rs": "rust",
        ".rb": "ruby",
        ".php": "php",
        ".swift": "swift",
        ".kt": "kotlin",
        ".scala": "scala",
        # Web
        ".html": "html",
        ".htm": "html",
        ".css": "css",
        ".scss": "scss",
        ".sass": "sass",
        ".less": "less",
        ".json": "json",
        ".xml": "xml",
        ".yaml": "yaml",
        ".yml": "yaml",
        # Documentation
        ".md": "markdown",
        ".rst": "rst",
        ".txt": "text",
        ".tex": "latex",
        # Config
        ".conf": "config",
        ".cfg": "config",
        ".ini": "config",
        ".env": "config",
        ".toml": "config",
        # Scripts
        ".sh": "shell",
        ".bash": "shell",
        ".zsh": "shell",
        ".ps1": "powershell",
        ".bat": "batch",
    }

    def __init__(
        self,
        max_file_size_mb: Optional[float] = None,
        max_content_length: Optional[int] = None,
    ):
        """Initialize a file extractor.

        Args:
            max_file_size_mb: Maximum file size to process in MB
            max_content_length: Maximum content length in characters
        """
        self.max_file_size_bytes = (max_file_size_mb or get_float_env("MAX_FILE_SIZE_MB", 10)) * 1024 * 1024
        self.max_content_length = max_content_length or 60000  # Default to 60K characters

    def get_file_type(self, filepath: Union[str, Path]) -> str:
        """Determine the file type based on extension and content.

        Args:
            filepath: Path to the file

        Returns:
            File type string
        """
        filepath = Path(filepath)
        extension = filepath.suffix.lower()
        
        # First check if it's a known binary extension
        if extension in self.BINARY_EXTENSIONS:
            return "binary"
        
        # Next check if it's a known text extension
        if extension in self.TEXT_EXTENSIONS:
            return self.TEXT_EXTENSIONS[extension]
        
        # Try to detect using magic bytes if available
        try:
            mime_type = magic.from_file(str(filepath), mime=True)
            if mime_type.startswith("text/"):
                return "text"
            elif "xml" in mime_type:
                return "xml"
            elif "json" in mime_type:
                return "json"
            else:
                return "binary"
        except (ImportError, IOError):
            # Fallback to basic extension check if magic failed
            if not extension:
                # No extension, try to detect if it's a text file
                try:
                    with open(filepath, "rb") as f:
                        content = f.read(1024)  # Read first KB
                        if b"\x00" in content:  # Contains null bytes, likely binary
                            return "binary"
                        return "text"
                except IOError:
                    return "unknown"
            
            # Unknown extension, treat as text by default
            return "text"

    def is_binary_file(self, filepath: Union[str, Path]) -> bool:
        """Check if a file is binary.

        Args:
            filepath: Path to the file

        Returns:
            True if the file is binary, False otherwise
        """
        # Check by extension first
        filepath = Path(filepath)
        extension = filepath.suffix.lower()
        
        if extension in self.BINARY_EXTENSIONS:
            return True
        
        # Check by content if extension is unknown
        try:
            with open(filepath, "rb") as f:
                content = f.read(1024)  # Read first KB
                return b"\x00" in content  # Contains null bytes, likely binary
        except IOError:
            logger.warning(f"Failed to read file {filepath}")
            return True  # Assume binary if can't read

    def matches_patterns(
        self, 
        filepath: Union[str, Path],
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        include_tests: bool = False,
    ) -> bool:
        """Check if a file path matches the include/exclude patterns.

        Args:
            filepath: Path to check
            include_patterns: List of glob patterns to include
            exclude_patterns: List of glob patterns to exclude
            include_tests: Whether to include test files and directories

        Returns:
            True if the file should be included, False otherwise
        """
        # Normalize to Path object and convert to string for pattern matching
        filepath = str(Path(filepath))
        
        # Use config patterns if not provided
        from mfai_db_repos.utils.config import config
        file_filter_config = config.config.file_filter
        
        # Use config patterns if not provided
        include_patterns = include_patterns or file_filter_config.include_patterns
        
        # Start with base exclude patterns
        if exclude_patterns is None:
            exclude_patterns = list(file_filter_config.exclude_patterns)
            
            # Add test patterns to exclude list if not including tests
            if not include_tests and hasattr(file_filter_config, 'test_patterns'):
                exclude_patterns.extend(file_filter_config.test_patterns)
        
        # Check exclude patterns
        for pattern in exclude_patterns:
            if self._matches_glob_pattern(filepath, pattern):
                return False
        
        # If no include patterns, include all files
        if not include_patterns:
            return True
        
        # Check include patterns
        for pattern in include_patterns:
            if self._matches_glob_pattern(filepath, pattern):
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
        import fnmatch
        
        # First, try with simple fnmatch which handles basic globs
        if fnmatch.fnmatch(filepath, pattern):
            return True
            
        # Special handling for directory matching with **
        if "**" in pattern:
            # For pattern like **/tests/** - check if 'tests' is anywhere in the path
            if pattern == "**/tests/**" or pattern == "**/test/**":
                dir_name = pattern.split("**/")[1].split("/**")[0]
                path_parts = Path(filepath).parts
                return dir_name in path_parts
                
            # Special check for test_*.py, *_test.py, etc.
            if pattern.endswith(".py"):
                basename = Path(filepath).name
                if pattern == "**/test_*.py" and basename.startswith("test_"):
                    return True
                if pattern == "**/*_test.py" and basename.endswith("_test.py"):
                    return True
                if pattern == "**/*_tests.py" and basename.endswith("_tests.py"):
                    return True
                
        # No match found
        return False

    def should_process_file(
        self,
        filepath: Union[str, Path],
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        include_tests: bool = False,
    ) -> bool:
        """Check if a file should be processed based on all criteria.

        Args:
            filepath: Path to the file
            include_patterns: List of glob patterns to include
            exclude_patterns: List of glob patterns to exclude
            include_tests: Whether to include test files and directories

        Returns:
            True if the file should be processed, False otherwise
        """
        filepath = Path(filepath)
        
        # Check if file exists
        if not filepath.exists():
            return False
        
        # Check file size
        if filepath.stat().st_size > self.max_file_size_bytes:
            logger.debug(f"Skipping {filepath} due to size ({filepath.stat().st_size} bytes)")
            return False
        
        # Check if it's a binary file
        if self.is_binary_file(filepath):
            logger.debug(f"Skipping binary file {filepath}")
            return False
        
        # Check patterns
        if not self.matches_patterns(filepath, include_patterns, exclude_patterns, include_tests):
            logger.debug(f"Skipping {filepath} due to pattern mismatch")
            return False
        
        return True

    def extract_content(self, filepath: Union[str, Path]) -> Optional[str]:
        """Extract content from a file.

        Args:
            filepath: Path to the file

        Returns:
            File content as string or None if extraction failed
        """
        filepath = Path(filepath)
        
        # Check if we should process this file (assume not including tests by default)
        if not self.should_process_file(filepath, include_tests=False):
            return None
        
        try:
            # First try to read with UTF-8
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
            except UnicodeDecodeError:
                # If UTF-8 fails, detect encoding
                with open(filepath, "rb") as f:
                    raw_content = f.read()
                encoding_result = chardet.detect(raw_content)
                encoding = encoding_result["encoding"] or "utf-8"
                
                # Try again with detected encoding
                try:
                    content = raw_content.decode(encoding)
                except UnicodeDecodeError:
                    # If all else fails, decode with errors ignored
                    content = raw_content.decode("utf-8", errors="replace")
            
            # Trim content if it's too long
            if len(content) > self.max_content_length:
                logger.debug(f"Trimming content of {filepath} to {self.max_content_length} characters")
                content = content[:self.max_content_length]
            
            return content
        except Exception as e:
            logger.warning(f"Failed to extract content from {filepath}: {e}")
            return None

    def get_file_metadata(self, filepath: Union[str, Path]) -> Dict[str, Union[str, int, datetime]]:
        """Get metadata for a file.

        Args:
            filepath: Path to the file

        Returns:
            Dictionary with file metadata
        """
        filepath = Path(filepath)
        
        try:
            stat = filepath.stat()
            
            return {
                "filename": filepath.name,
                "filepath": str(filepath),
                "extension": filepath.suffix.lower(),
                "file_size": stat.st_size,
                "last_modified": datetime.fromtimestamp(stat.st_mtime),
                "file_type": self.get_file_type(filepath),
            }
        except OSError as e:
            logger.warning(f"Failed to get metadata for {filepath}: {e}")
            return {
                "filename": filepath.name,
                "filepath": str(filepath),
                "extension": filepath.suffix.lower(),
                "error": str(e),
            }