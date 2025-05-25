"""
Unit tests for file processor components.

These tests verify the functionality of file extraction, filtering, and processing.
"""
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union
from unittest.mock import Mock, patch

import pytest

from mfai_db_repos.lib.file_processor.extractor import FileExtractor
from mfai_db_repos.lib.file_processor.filter import FileFilter, FileTypeDetector
from mfai_db_repos.lib.file_processor.metadata import MetadataExtractor
from mfai_db_repos.lib.file_processor.patterns import PatternConfig, PatternManager, PatternSet
from mfai_db_repos.lib.file_processor.processor import FileProcessor
from mfai_db_repos.lib.git.repository import GitRepository, RepoStatus


class TestFileExtractor:
    """Test cases for FileExtractor class."""

    @pytest.fixture
    def temp_file(self):
        """Create a temporary file for testing."""
        fd, path = tempfile.mkstemp()
        try:
            with os.fdopen(fd, "w") as f:
                f.write("Test content for file extractor")
            yield path
        finally:
            os.unlink(path)

    def test_get_file_type(self, temp_file):
        """Test file type detection."""
        extractor = FileExtractor()
        
        # Test with known extensions
        assert extractor.get_file_type("test.py") == "python"
        assert extractor.get_file_type("test.js") == "javascript"
        assert extractor.get_file_type("test.html") == "html"
        assert extractor.get_file_type("test.jpg") == "binary"
        
        # Test with temporary file (should be detected as text)
        assert extractor.get_file_type(temp_file) == "text"

    def test_is_binary_file(self, temp_file):
        """Test binary file detection."""
        extractor = FileExtractor()
        
        # Test with known binary extensions
        assert extractor.is_binary_file("test.jpg") is True
        assert extractor.is_binary_file("test.png") is True
        assert extractor.is_binary_file("test.exe") is True
        
        # Test with known text extensions
        assert extractor.is_binary_file("test.py") is False
        assert extractor.is_binary_file("test.js") is False
        assert extractor.is_binary_file("test.html") is False
        
        # Test with temporary file (should be detected as text)
        assert extractor.is_binary_file(temp_file) is False

    def test_matches_patterns(self):
        """Test pattern matching."""
        extractor = FileExtractor()
        
        # Test include patterns
        include_patterns = ["**/*.py", "**/*.js", "docs/**"]
        assert extractor.matches_patterns("test.py", include_patterns=include_patterns) is True
        assert extractor.matches_patterns("src/test.py", include_patterns=include_patterns) is True
        assert extractor.matches_patterns("docs/test.txt", include_patterns=include_patterns) is True
        assert extractor.matches_patterns("test.txt", include_patterns=include_patterns) is False
        
        # Test exclude patterns
        exclude_patterns = ["**/*.pyc", "**/node_modules/**"]
        assert extractor.matches_patterns("test.pyc", exclude_patterns=exclude_patterns) is False
        assert extractor.matches_patterns("node_modules/test.js", exclude_patterns=exclude_patterns) is False
        assert extractor.matches_patterns("test.py", exclude_patterns=exclude_patterns) is True
        
        # Test both include and exclude patterns
        assert extractor.matches_patterns(
            "test.py", 
            include_patterns=include_patterns, 
            exclude_patterns=exclude_patterns
        ) is True
        assert extractor.matches_patterns(
            "test.pyc", 
            include_patterns=include_patterns, 
            exclude_patterns=exclude_patterns
        ) is False

    def test_should_process_file(self, temp_file):
        """Test file processing eligibility check."""
        extractor = FileExtractor(max_file_size_mb=1)
        
        # Test with existing file
        assert extractor.should_process_file(temp_file) is True
        
        # Test with nonexistent file
        assert extractor.should_process_file("nonexistent.py") is False
        
        # Test with patterns
        include_patterns = ["**/*.py"]
        exclude_patterns = ["**/*.pyc"]
        
        assert extractor.should_process_file(
            temp_file, 
            include_patterns=include_patterns, 
            exclude_patterns=exclude_patterns
        ) is False  # Doesn't match include pattern
        
        # Rename temp file to .py extension for pattern testing
        temp_py = f"{temp_file}.py"
        try:
            os.symlink(temp_file, temp_py)
            assert extractor.should_process_file(
                temp_py, 
                include_patterns=include_patterns, 
                exclude_patterns=exclude_patterns
            ) is True
        except (OSError, PermissionError):
            # Skip if symlink creation fails
            pass
        finally:
            if os.path.exists(temp_py):
                os.unlink(temp_py)

    def test_extract_content(self, temp_file):
        """Test content extraction."""
        extractor = FileExtractor()
        
        # Test with existing file
        content = extractor.extract_content(temp_file)
        assert content == "Test content for file extractor"
        
        # Test with nonexistent file
        content = extractor.extract_content("nonexistent.py")
        assert content is None

    def test_get_file_metadata(self, temp_file):
        """Test metadata extraction."""
        extractor = FileExtractor()
        
        # Test with existing file
        metadata = extractor.get_file_metadata(temp_file)
        assert metadata["filename"] == os.path.basename(temp_file)
        assert metadata["file_size"] > 0
        assert isinstance(metadata["last_modified"], datetime)
        
        # Test with nonexistent file
        metadata = extractor.get_file_metadata("nonexistent.py")
        assert "error" in metadata


class TestFileTypeDetector:
    """Test cases for FileTypeDetector class."""

    def test_detect_file_type(self):
        """Test file type detection."""
        detector = FileTypeDetector()
        
        # Test with known extensions
        assert detector.detect_file_type("test.py") == "source_code"
        assert detector.detect_file_type("test.js") == "source_code"
        assert detector.detect_file_type("test.html") == "web"
        assert detector.detect_file_type("test.json") == "data"
        assert detector.detect_file_type("test.md") == "documentation"
        assert detector.detect_file_type("test.cfg") == "configuration"
        assert detector.detect_file_type("test.sh") == "script"
        assert detector.detect_file_type("test.jpg") == "binary"
        
        # Test with common filenames
        assert detector.detect_file_type("README.md") == "documentation"
        assert detector.detect_file_type("LICENSE") == "documentation"
        assert detector.detect_file_type("Dockerfile") == "configuration"
        assert detector.detect_file_type(".gitignore") == "configuration"
        
        # Test with unknown extension
        assert detector.detect_file_type("test.xyz") == "unknown"

    def test_get_category_for_file_type(self):
        """Test file type categorization."""
        detector = FileTypeDetector()
        
        # Test with known types
        assert detector.get_category_for_file_type("python") == "source_code"
        assert detector.get_category_for_file_type("javascript") == "source_code"
        assert detector.get_category_for_file_type("html") == "web"
        assert detector.get_category_for_file_type("json") == "data"
        assert detector.get_category_for_file_type("markdown") == "documentation"
        assert detector.get_category_for_file_type("config") == "configuration"
        assert detector.get_category_for_file_type("shell") == "script"
        assert detector.get_category_for_file_type("binary") == "binary"
        
        # Test with partial match
        assert detector.get_category_for_file_type("typescript_jsx") == "source_code"
        
        # Test with unknown type
        assert detector.get_category_for_file_type("unknown_type") == "unknown"


class TestFileFilter:
    """Test cases for FileFilter class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory with test files."""
        temp_dir = tempfile.mkdtemp()
        
        # Create test files
        files = {
            "test.py": "Python test file",
            "test.js": "JavaScript test file",
            "test.html": "HTML test file",
            "test.md": "Markdown test file",
            "test.jpg": "Binary test file",
            "node_modules/test.js": "JS in node_modules",
            "docs/test.txt": "Text in docs",
        }
        
        try:
            for filepath, content in files.items():
                full_path = os.path.join(temp_dir, filepath)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "w") as f:
                    f.write(content)
            
            yield temp_dir
        finally:
            import shutil
            shutil.rmtree(temp_dir)

    def test_should_process_file(self, temp_dir):
        """Test file processing eligibility check."""
        file_filter = FileFilter(
            include_types=["source_code", "documentation"],
            exclude_types=["binary"],
            include_patterns=["**/*.py", "**/*.js", "**/*.md"],
            exclude_patterns=["**/node_modules/**"],
        )
        
        # Test with various files
        assert file_filter.should_process_file(os.path.join(temp_dir, "test.py")) is True
        assert file_filter.should_process_file(os.path.join(temp_dir, "test.js")) is True
        assert file_filter.should_process_file(os.path.join(temp_dir, "test.md")) is True
        assert file_filter.should_process_file(os.path.join(temp_dir, "test.html")) is False  # Not in include patterns
        assert file_filter.should_process_file(os.path.join(temp_dir, "test.jpg")) is False  # Excluded type
        assert file_filter.should_process_file(os.path.join(temp_dir, "node_modules/test.js")) is False  # Excluded pattern
        
        # Test with nonexistent file
        assert file_filter.should_process_file(os.path.join(temp_dir, "nonexistent.py")) is False

    def test_filter_files(self, temp_dir):
        """Test file filtering."""
        file_filter = FileFilter(
            include_types=["source_code", "documentation"],
            exclude_types=["binary"],
            include_patterns=["**/*.py", "**/*.js", "**/*.md"],
            exclude_patterns=["**/node_modules/**"],
        )
        
        # Get all files in temp_dir
        all_files = []
        for root, _, files in os.walk(temp_dir):
            for file in files:
                all_files.append(os.path.join(root, file))
        
        # Filter files
        filtered_files = file_filter.filter_files(all_files)
        
        # Verify results
        assert len(filtered_files) == 3
        assert any(str(path).endswith("test.py") for path in filtered_files)
        assert any(str(path).endswith("test.js") for path in filtered_files)
        assert any(str(path).endswith("test.md") for path in filtered_files)
        assert not any(str(path).endswith("test.html") for path in filtered_files)
        assert not any(str(path).endswith("test.jpg") for path in filtered_files)
        assert not any("node_modules" in str(path) for path in filtered_files)


class TestPatternManager:
    """Test cases for PatternManager class."""

    def test_init(self):
        """Test pattern manager initialization."""
        manager = PatternManager()
        
        # Test preset patterns
        assert "all_code" in manager.patterns
        assert "python_only" in manager.patterns
        assert "javascript_only" in manager.patterns
        assert "documentation" in manager.patterns
        assert "config_files" in manager.patterns

    def test_add_pattern_config(self):
        """Test adding a new pattern configuration."""
        manager = PatternManager()
        
        # Create a new pattern config
        pattern_config = PatternConfig(
            name="test_pattern",
            description="Test pattern",
            include_patterns=["**/*.test"],
            exclude_patterns=["**/skip/**"],
        )
        
        # Add to manager
        manager.add_pattern_config(pattern_config)
        
        # Verify
        assert "test_pattern" in manager.patterns
        assert manager.patterns["test_pattern"] == pattern_config

    def test_get_pattern_config(self):
        """Test getting a pattern configuration."""
        manager = PatternManager()
        
        # Get existing pattern
        pattern = manager.get_pattern_config("all_code")
        assert pattern is not None
        assert pattern.name == "all_code"
        
        # Get nonexistent pattern
        pattern = manager.get_pattern_config("nonexistent")
        assert pattern is None

    def test_list_pattern_configs(self):
        """Test listing pattern configurations."""
        manager = PatternManager()
        
        # List patterns
        patterns = manager.list_pattern_configs()
        assert len(patterns) >= 5  # At least 5 preset patterns
        assert all(isinstance(p, PatternConfig) for p in patterns)

    def test_remove_pattern_config(self):
        """Test removing a pattern configuration."""
        manager = PatternManager()
        
        # Create a new pattern config
        pattern_config = PatternConfig(
            name="test_pattern",
            description="Test pattern",
            include_patterns=["**/*.test"],
            exclude_patterns=["**/skip/**"],
        )
        
        # Add to manager
        manager.add_pattern_config(pattern_config)
        
        # Verify it exists
        assert "test_pattern" in manager.patterns
        
        # Remove it
        result = manager.remove_pattern_config("test_pattern")
        assert result is True
        assert "test_pattern" not in manager.patterns
        
        # Try to remove nonexistent pattern
        result = manager.remove_pattern_config("nonexistent")
        assert result is False

    def test_filter_files(self, tmpdir):
        """Test filtering files with pattern configurations."""
        manager = PatternManager()
        
        # Create test files
        files = [
            tmpdir.join("test.py"),
            tmpdir.join("test.js"),
            tmpdir.join("test.md"),
            tmpdir.join("test.txt"),
            tmpdir.join("node_modules/test.js"),
        ]
        
        for file in files:
            file.write("test", ensure=True)
        
        # Convert to string paths
        file_paths = [str(f) for f in files]
        
        # Filter with python_only pattern
        filtered = manager.filter_files(file_paths, "python_only")
        assert len(filtered) == 1
        assert str(filtered[0]).endswith("test.py")
        
        # Filter with all_code pattern
        filtered = manager.filter_files(file_paths, "all_code")
        assert len(filtered) == 2  # test.py and test.js (not in node_modules)
        
        # Filter with documentation pattern
        filtered = manager.filter_files(file_paths, "documentation")
        assert len(filtered) == 1
        assert str(filtered[0]).endswith("test.md")
        
        # Filter with default pattern
        filtered = manager.filter_files(file_paths)
        assert len(filtered) > 0