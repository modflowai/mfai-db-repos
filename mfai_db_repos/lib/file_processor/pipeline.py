"""
Content extraction pipeline module.

This module provides a configurable pipeline for extracting and processing
file content from repositories, combining multiple processing steps.
"""
import asyncio
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from mfai_db_repos.lib.file_processor.encoding import EncodingDetector
from mfai_db_repos.lib.file_processor.extractor import FileExtractor
from mfai_db_repos.lib.file_processor.filter import FileFilter, FileTypeDetector
from mfai_db_repos.lib.file_processor.ignores import IgnoreManager
from mfai_db_repos.lib.file_processor.metadata import MetadataExtractor
from mfai_db_repos.lib.file_processor.normalizer import ContentNormalizer, NormalizationLevel
from mfai_db_repos.lib.file_processor.tracker import FileStatus, FileStatusTracker
from mfai_db_repos.lib.git.repository import GitRepository
from mfai_db_repos.utils.config import Config
from mfai_db_repos.utils.logger import get_logger

logger = get_logger(__name__)


class ProcessingStage(str, Enum):
    """Processing stages in the extraction pipeline."""
    
    FILTERING = "filtering"  # File filtering stage
    EXTRACTION = "extraction"  # Content extraction stage
    ENCODING = "encoding"  # Encoding detection and handling stage
    NORMALIZATION = "normalization"  # Content normalization stage
    METADATA = "metadata"  # Metadata extraction stage
    PROCESSING = "processing"  # Custom processing stage


@dataclass
class ProcessingResult:
    """Result of content extraction and processing."""
    
    # File information
    path: str
    name: str
    extension: Optional[str] = None
    
    # Content
    content: Optional[str] = None
    normalized_content: Optional[str] = None
    
    # Metadata
    size: Optional[int] = None
    language: Optional[str] = None
    encoding: Optional[str] = None
    last_modified: Optional[float] = None
    status: Optional[str] = None
    
    # Additional metadata
    metadata: Optional[Dict[str, Any]] = None
    
    # Processing status
    success: bool = False
    error: Optional[str] = None
    skipped: bool = False
    skip_reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation.
        
        Returns:
            Dictionary representation
        """
        return {
            "path": self.path,
            "name": self.name,
            "extension": self.extension,
            "content": self.content,
            "normalized_content": self.normalized_content,
            "size": self.size,
            "language": self.language,
            "encoding": self.encoding,
            "last_modified": self.last_modified,
            "status": self.status,
            "metadata": self.metadata,
            "success": self.success,
            "error": self.error,
            "skipped": self.skipped,
            "skip_reason": self.skip_reason,
        }


class ProcessingOptions:
    """Options for content extraction and processing."""
    
    def __init__(
        self,
        max_file_size_mb: float = 10.0,
        max_content_length: int = 100000,
        normalization_level: NormalizationLevel = NormalizationLevel.STANDARD,
        extract_metadata: bool = True,
        ignore_binary_files: bool = True,
        ignore_categories: Optional[List[str]] = None,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        include_extensions: Optional[List[str]] = None,
        exclude_extensions: Optional[List[str]] = None,
        follow_symlinks: bool = False,
    ):
        """Initialize processing options.
        
        Args:
            max_file_size_mb: Maximum file size to process in MB
            max_content_length: Maximum content length in characters
            normalization_level: Level of content normalization
            extract_metadata: Whether to extract metadata
            ignore_binary_files: Whether to ignore binary files
            ignore_categories: Categories of files to ignore
            include_patterns: Glob patterns to include
            exclude_patterns: Glob patterns to exclude
            include_extensions: File extensions to include
            exclude_extensions: File extensions to exclude
            follow_symlinks: Whether to follow symbolic links
        """
        self.max_file_size_mb = max_file_size_mb
        self.max_file_size_bytes = int(max_file_size_mb * 1024 * 1024)
        self.max_content_length = max_content_length
        self.normalization_level = normalization_level
        self.extract_metadata = extract_metadata
        self.ignore_binary_files = ignore_binary_files
        self.ignore_categories = ignore_categories or ["git", "ide"]
        self.include_patterns = include_patterns or []
        self.exclude_patterns = exclude_patterns or []
        self.include_extensions = include_extensions or []
        self.exclude_extensions = exclude_extensions or []
        self.follow_symlinks = follow_symlinks


class ExtractionPipeline:
    """Pipeline for content extraction and processing."""
    
    def __init__(
        self,
        config: Optional[Config] = None,
        options: Optional[ProcessingOptions] = None,
        custom_processors: Optional[Dict[ProcessingStage, List[Callable]]] = None,
    ):
        """Initialize an extraction pipeline.
        
        Args:
            config: Optional Config instance
            options: Processing options
            custom_processors: Custom processing functions for each stage
        """
        self.config = config or Config()
        self.options = options or ProcessingOptions()
        self.custom_processors = custom_processors or {}
        
        # Initialize pipeline components
        self._init_components()
    
    def _init_components(self) -> None:
        """Initialize pipeline components."""
        # File type detection
        self.type_detector = FileTypeDetector()
        
        # File filtering
        self.file_filter = FileFilter(
            include_patterns=self.options.include_patterns,
            exclude_patterns=self.options.exclude_patterns,
            max_file_size_mb=self.options.max_file_size_mb,
        )
        
        # Ignore management
        self.ignore_manager = IgnoreManager()
        if self.options.ignore_categories:
            self.ignore_manager.add_common_ignores(self.options.ignore_categories)
        
        # File extraction
        self.file_extractor = FileExtractor(
            max_file_size_mb=self.options.max_file_size_mb,
            max_content_length=self.options.max_content_length,
        )
        
        # Encoding detection
        self.encoding_detector = EncodingDetector()
        
        # Content normalization
        self.content_normalizer = ContentNormalizer(
            normalization_level=self.options.normalization_level,
        )
        
        # Metadata extraction
        self.metadata_extractor = MetadataExtractor()
        
        # Status tracking
        self.status_tracker = FileStatusTracker(
            use_content_hash=True,
        )
    
    def process_file(
        self,
        filepath: Union[str, Path],
        base_path: Optional[Union[str, Path]] = None,
        status: Optional[FileStatus] = None,
    ) -> ProcessingResult:
        """Process a single file through the extraction pipeline.
        
        Args:
            filepath: Path to the file
            base_path: Base path for relative paths
            status: Optional file status
            
        Returns:
            ProcessingResult with extracted content and metadata
        """
        filepath = Path(filepath)
        
        # Make absolute path if base_path is provided
        if base_path and not filepath.is_absolute():
            abs_path = Path(base_path) / filepath
        else:
            abs_path = filepath.absolute()
        
        # Get relative path if base_path is provided
        if base_path:
            try:
                rel_path = filepath.relative_to(base_path)
            except ValueError:
                rel_path = filepath
        else:
            rel_path = filepath
        
        # Initialize result
        result = ProcessingResult(
            path=str(rel_path),
            name=filepath.name,
            extension=filepath.suffix.lower() if filepath.suffix else None,
        )
        
        try:
            # Check if file exists and is a regular file
            if not abs_path.exists():
                result.skipped = True
                result.skip_reason = "File does not exist"
                return result
            
            if not abs_path.is_file():
                result.skipped = True
                result.skip_reason = "Not a regular file"
                return result
            
            # Run filtering stage
            if not self._run_filtering_stage(abs_path, result):
                return result
            
            # Run encoding detection and extraction stage
            if not self._run_extraction_stage(abs_path, result):
                return result
            
            # Run normalization stage
            if not self._run_normalization_stage(result):
                return result
            
            # Run metadata extraction stage
            if not self._run_metadata_stage(abs_path, result):
                return result
            
            # Run custom processing stage
            if not self._run_custom_processing_stage(result):
                return result
            
            # Mark as successful
            result.success = True
            
            return result
        except Exception as e:
            logger.error(f"Error processing file {filepath}: {str(e)}")
            result.success = False
            result.error = str(e)
            return result
    
    def _run_filtering_stage(self, filepath: Path, result: ProcessingResult) -> bool:
        """Run the filtering stage of the pipeline.
        
        Args:
            filepath: Path to the file
            result: Processing result to update
            
        Returns:
            True if file should be processed, False if skipped
        """
        # Run custom filters first
        if ProcessingStage.FILTERING in self.custom_processors:
            for processor in self.custom_processors[ProcessingStage.FILTERING]:
                if not processor(filepath, result):
                    result.skipped = True
                    result.skip_reason = "Custom filter"
                    return False
        
        # Check ignore patterns
        if self.ignore_manager.should_ignore(filepath, is_dir=False):
            result.skipped = True
            result.skip_reason = "Ignored by pattern"
            return False
        
        # Check file size
        try:
            stat = filepath.stat()
            result.size = stat.st_size
            result.last_modified = stat.st_mtime
            
            if stat.st_size > self.options.max_file_size_bytes:
                result.skipped = True
                result.skip_reason = f"File too large ({stat.st_size} bytes)"
                return False
            
        except Exception as e:
            result.skipped = True
            result.skip_reason = f"Error reading file stats: {str(e)}"
            return False
        
        # Check file type
        file_type = self.type_detector.detect_file_type(filepath)
        
        # Check binary files
        if self.options.ignore_binary_files and file_type == "binary":
            result.skipped = True
            result.skip_reason = "Binary file"
            return False
        
        # Check file extension inclusion/exclusion
        if self.options.include_extensions and result.extension:
            if result.extension not in self.options.include_extensions:
                result.skipped = True
                result.skip_reason = f"Extension {result.extension} not in include list"
                return False
        
        if self.options.exclude_extensions and result.extension:
            if result.extension in self.options.exclude_extensions:
                result.skipped = True
                result.skip_reason = f"Extension {result.extension} in exclude list"
                return False
        
        # Check file filter
        if not self.file_filter.should_process_file(filepath):
            result.skipped = True
            result.skip_reason = "Failed file filter checks"
            return False
        
        return True
    
    def _run_extraction_stage(self, filepath: Path, result: ProcessingResult) -> bool:
        """Run the extraction stage of the pipeline.
        
        Args:
            filepath: Path to the file
            result: Processing result to update
            
        Returns:
            True if extraction succeeded, False otherwise
        """
        # Run custom extractors first
        if ProcessingStage.EXTRACTION in self.custom_processors:
            for processor in self.custom_processors[ProcessingStage.EXTRACTION]:
                processor_result = processor(filepath, result)
                if processor_result is False:
                    result.skipped = True
                    result.skip_reason = "Custom extractor rejected"
                    return False
                elif isinstance(processor_result, str):
                    result.content = processor_result
                    # Skip default extraction if content was provided
                    return True
        
        # Detect encoding
        if ProcessingStage.ENCODING in self.custom_processors:
            for processor in self.custom_processors[ProcessingStage.ENCODING]:
                encoding_result = processor(filepath, result)
                if encoding_result is False:
                    result.skipped = True
                    result.skip_reason = "Custom encoding detector rejected"
                    return False
                elif isinstance(encoding_result, str):
                    result.encoding = encoding_result
        
        # If encoding wasn't set by custom processor, detect it
        if not result.encoding:
            encoding_result = self.encoding_detector.detect_file_encoding(filepath)
            result.encoding = encoding_result.encoding
        
        # Extract content
        content, _ = self.encoding_detector.read_file_with_encoding(
            filepath, encoding=result.encoding
        )
        
        if content is None:
            result.skipped = True
            result.skip_reason = "Failed to extract content"
            return False
        
        # Limit content length if needed
        if self.options.max_content_length > 0 and len(content) > self.options.max_content_length:
            logger.debug(f"Truncating content of {filepath} to {self.options.max_content_length} characters")
            content = content[:self.options.max_content_length]
        
        result.content = content
        
        return True
    
    def _run_normalization_stage(self, result: ProcessingResult) -> bool:
        """Run the normalization stage of the pipeline.
        
        Args:
            result: Processing result to update
            
        Returns:
            True if normalization succeeded, False otherwise
        """
        if not result.content:
            return True  # Nothing to normalize
        
        # Run custom normalizers first
        if ProcessingStage.NORMALIZATION in self.custom_processors:
            for processor in self.custom_processors[ProcessingStage.NORMALIZATION]:
                processor_result = processor(result.content, result)
                if processor_result is False:
                    result.skipped = True
                    result.skip_reason = "Custom normalizer rejected"
                    return False
                elif isinstance(processor_result, str):
                    result.normalized_content = processor_result
                    # Skip default normalization if content was provided
                    return True
        
        # Normalize content
        try:
            normalized = self.content_normalizer.normalize(
                result.content,
                language=result.language,
                normalization_level=self.options.normalization_level,
            )
            result.normalized_content = normalized
            return True
        except Exception as e:
            logger.warning(f"Error normalizing content: {str(e)}")
            # Still consider successful, just use original content
            result.normalized_content = result.content
            return True
    
    def _run_metadata_stage(self, filepath: Path, result: ProcessingResult) -> bool:
        """Run the metadata extraction stage of the pipeline.
        
        Args:
            filepath: Path to the file
            result: Processing result to update
            
        Returns:
            True if metadata extraction succeeded, False otherwise
        """
        if not self.options.extract_metadata:
            return True  # Skip metadata extraction
        
        # Run custom metadata extractors first
        if ProcessingStage.METADATA in self.custom_processors:
            for processor in self.custom_processors[ProcessingStage.METADATA]:
                metadata = processor(filepath, result)
                if metadata is False:
                    result.skipped = True
                    result.skip_reason = "Custom metadata extractor rejected"
                    return False
                elif isinstance(metadata, dict):
                    result.metadata = metadata
                    # Skip default metadata extraction if metadata was provided
                    return True
        
        # Extract metadata
        try:
            metadata = self.metadata_extractor.extract_file_metadata(
                filepath, content=result.content
            )
            
            # Update result with metadata
            result.metadata = metadata
            
            # Set language from metadata if not already set
            if not result.language and "language" in metadata:
                result.language = metadata["language"]
            
            return True
        except Exception as e:
            logger.warning(f"Error extracting metadata: {str(e)}")
            # Still consider successful
            return True
    
    def _run_custom_processing_stage(self, result: ProcessingResult) -> bool:
        """Run the custom processing stage of the pipeline.
        
        Args:
            result: Processing result to update
            
        Returns:
            True if processing succeeded, False otherwise
        """
        if ProcessingStage.PROCESSING in self.custom_processors:
            for processor in self.custom_processors[ProcessingStage.PROCESSING]:
                processor_result = processor(result)
                if processor_result is False:
                    result.skipped = True
                    result.skip_reason = "Custom processor rejected"
                    return False
        
        return True
    
    def process_files(
        self,
        filepaths: List[Union[str, Path]],
        base_path: Optional[Union[str, Path]] = None,
        max_workers: int = 5,
    ) -> List[ProcessingResult]:
        """Process multiple files through the extraction pipeline.
        
        Args:
            filepaths: List of file paths
            base_path: Base path for relative paths
            max_workers: Maximum number of concurrent workers
            
        Returns:
            List of ProcessingResult objects
        """
        results = []
        
        for filepath in filepaths:
            result = self.process_file(filepath, base_path)
            results.append(result)
        
        return results
    
    async def process_files_async(
        self,
        filepaths: List[Union[str, Path]],
        base_path: Optional[Union[str, Path]] = None,
        max_workers: int = 5,
    ) -> List[ProcessingResult]:
        """Process multiple files asynchronously through the extraction pipeline.
        
        Args:
            filepaths: List of file paths
            base_path: Base path for relative paths
            max_workers: Maximum number of concurrent workers
            
        Returns:
            List of ProcessingResult objects
        """
        async def process_file_task(filepath: Union[str, Path]) -> ProcessingResult:
            return self.process_file(filepath, base_path)
        
        # Use semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_workers)
        
        async def process_with_semaphore(filepath: Union[str, Path]) -> ProcessingResult:
            async with semaphore:
                return await asyncio.to_thread(process_file_task, filepath)
        
        # Create tasks
        tasks = [process_with_semaphore(filepath) for filepath in filepaths]
        
        # Execute tasks and collect results
        results = await asyncio.gather(*tasks)
        
        return results
    
    def process_directory(
        self,
        directory_path: Union[str, Path],
        recursive: bool = True,
        max_files: Optional[int] = None,
        max_workers: int = 5,
    ) -> List[ProcessingResult]:
        """Process all files in a directory.
        
        Args:
            directory_path: Path to directory
            recursive: Whether to process subdirectories
            max_files: Maximum number of files to process
            max_workers: Maximum number of concurrent workers
            
        Returns:
            List of ProcessingResult objects
        """
        directory_path = Path(directory_path)
        
        if not directory_path.exists() or not directory_path.is_dir():
            logger.warning(f"Directory not found: {directory_path}")
            return []
        
        # Collect all file paths
        filepaths = []
        
        if recursive:
            for root, _, files in os.walk(directory_path):
                for filename in files:
                    filepath = Path(root) / filename
                    filepaths.append(filepath)
                    
                    if max_files and len(filepaths) >= max_files:
                        break
                
                if max_files and len(filepaths) >= max_files:
                    break
        else:
            for entry in directory_path.iterdir():
                if entry.is_file():
                    filepaths.append(entry)
                    
                    if max_files and len(filepaths) >= max_files:
                        break
        
        # Process files
        return self.process_files(filepaths, base_path=directory_path, max_workers=max_workers)
    
    async def process_directory_async(
        self,
        directory_path: Union[str, Path],
        recursive: bool = True,
        max_files: Optional[int] = None,
        max_workers: int = 5,
    ) -> List[ProcessingResult]:
        """Process all files in a directory asynchronously.
        
        Args:
            directory_path: Path to directory
            recursive: Whether to process subdirectories
            max_files: Maximum number of files to process
            max_workers: Maximum number of concurrent workers
            
        Returns:
            List of ProcessingResult objects
        """
        directory_path = Path(directory_path)
        
        if not directory_path.exists() or not directory_path.is_dir():
            logger.warning(f"Directory not found: {directory_path}")
            return []
        
        # Collect all file paths
        filepaths = []
        
        if recursive:
            for root, _, files in os.walk(directory_path):
                for filename in files:
                    filepath = Path(root) / filename
                    filepaths.append(filepath)
                    
                    if max_files and len(filepaths) >= max_files:
                        break
                
                if max_files and len(filepaths) >= max_files:
                    break
        else:
            for entry in directory_path.iterdir():
                if entry.is_file():
                    filepaths.append(entry)
                    
                    if max_files and len(filepaths) >= max_files:
                        break
        
        # Process files asynchronously
        return await self.process_files_async(
            filepaths, base_path=directory_path, max_workers=max_workers
        )
    
    def process_repository(
        self,
        git_repo: GitRepository,
        incremental: bool = True,
        max_files: Optional[int] = None,
        max_workers: int = 5,
    ) -> List[ProcessingResult]:
        """Process files in a Git repository.
        
        Args:
            git_repo: Git repository instance
            incremental: Whether to process only changed files
            max_files: Maximum number of files to process
            max_workers: Maximum number of concurrent workers
            
        Returns:
            List of ProcessingResult objects
        """
        if not git_repo.is_cloned() or not git_repo.repo:
            logger.warning("Cannot process repository: not cloned")
            return []
        
        repo_path = Path(git_repo.repo.working_dir)
        
        # Parse .gitignore files
        self.ignore_manager.parse_gitignore_in_repo(repo_path)
        
        # Get files to process
        if incremental:
            # Get changed files
            tracked_files = self.status_tracker.track_repository(git_repo)
            filepaths = []
            
            for entry in tracked_files:
                if entry.status != FileStatus.DELETED:
                    filepaths.append(repo_path / entry.path)
                    
                    if max_files and len(filepaths) >= max_files:
                        break
        else:
            # Process all files
            return self.process_directory(
                repo_path, recursive=True, max_files=max_files, max_workers=max_workers
            )
        
        # Process files
        return self.process_files(filepaths, base_path=repo_path, max_workers=max_workers)