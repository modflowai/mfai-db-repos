"""
File processor module for the GitContext application.

This module provides functionality for processing files from Git repositories,
including extracting content, filtering by type, and analyzing metadata.
"""
from mfai_db_repos.lib.file_processor.extractor import FileExtractor
from mfai_db_repos.lib.file_processor.filter import FileFilter, FileTypeDetector
from mfai_db_repos.lib.file_processor.metadata import MetadataExtractor
from mfai_db_repos.lib.file_processor.patterns import PatternManager, PatternSet, PatternConfig
from mfai_db_repos.lib.file_processor.processor import FileProcessor

__all__ = [
    "FileExtractor",
    "FileFilter",
    "FileTypeDetector",
    "MetadataExtractor",
    "PatternManager",
    "PatternSet",
    "PatternConfig",
    "FileProcessor",
]
