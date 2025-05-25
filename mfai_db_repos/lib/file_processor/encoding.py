"""
File encoding detection and handling module.

This module provides functionality for detecting and handling different file encodings
for reliable content extraction and processing.
"""
import codecs
import os
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple, Union

import chardet
from mfai_db_repos.utils.config import Config
from mfai_db_repos.utils.logger import get_logger

logger = get_logger(__name__)


class EncodingConfidence(Enum):
    """Confidence levels for encoding detection."""
    
    HIGH = "high"  # High confidence (> 0.9)
    MEDIUM = "medium"  # Medium confidence (0.6 - 0.9)
    LOW = "low"  # Low confidence (< 0.6)
    UNKNOWN = "unknown"  # Unable to determine


class EncodingResult:
    """Result of file encoding detection."""
    
    def __init__(
        self,
        encoding: str,
        confidence: EncodingConfidence,
        bom_detected: bool = False,
        fallback_used: bool = False,
    ):
        """Initialize encoding detection result.
        
        Args:
            encoding: Detected encoding
            confidence: Confidence level
            bom_detected: Whether a BOM was detected
            fallback_used: Whether a fallback encoding was used
        """
        self.encoding = encoding
        self.confidence = confidence
        self.bom_detected = bom_detected
        self.fallback_used = fallback_used
    
    def __str__(self) -> str:
        """String representation of encoding result.
        
        Returns:
            String representation
        """
        result = f"Encoding: {self.encoding}, Confidence: {self.confidence.value}"
        if self.bom_detected:
            result += ", BOM detected"
        if self.fallback_used:
            result += ", fallback used"
        return result


class EncodingDetector:
    """File encoding detection and handling class."""
    
    # Common encoding BOM signatures
    BOM_SIGNATURES = {
        codecs.BOM_UTF8: "utf-8-sig",
        codecs.BOM_UTF16_LE: "utf-16-le",
        codecs.BOM_UTF16_BE: "utf-16-be",
        codecs.BOM_UTF32_LE: "utf-32-le",
        codecs.BOM_UTF32_BE: "utf-32-be",
    }
    
    # Common encodings to try in order of preference
    COMMON_ENCODINGS = [
        "utf-8",
        "latin1",
        "cp1252",
        "iso-8859-1",
        "ascii",
        "utf-16",
        "windows-1250",
        "windows-1252",
    ]
    
    # Language-specific encodings
    LANGUAGE_ENCODINGS = {
        # East Asian languages
        "ja": ["shift_jis", "euc_jp", "iso2022_jp"],
        "ko": ["euc_kr", "cp949"],
        "zh": ["gb2312", "gbk", "gb18030", "big5", "hz"],
        # Cyrillic
        "ru": ["koi8_r", "cp1251", "iso8859_5"],
        # Arabic
        "ar": ["cp1256", "iso8859_6"],
        # Hebrew
        "he": ["cp1255", "iso8859_8"],
        # Greek
        "el": ["cp1253", "iso8859_7"],
        # Turkish
        "tr": ["cp1254", "iso8859_9"],
        # Thai
        "th": ["cp874", "iso8859_11"],
    }
    
    def __init__(
        self,
        config: Optional[Config] = None,
        fallback_encodings: Optional[List[str]] = None,
        default_encoding: str = "utf-8",
        strict_mode: bool = False,
    ):
        """Initialize an encoding detector.
        
        Args:
            config: Optional Config instance
            fallback_encodings: List of fallback encodings to try
            default_encoding: Default encoding to use if detection fails
            strict_mode: Whether to use strict mode for encoding errors
        """
        self.config = config or Config()
        self.fallback_encodings = fallback_encodings or self.COMMON_ENCODINGS
        self.default_encoding = default_encoding
        self.strict_mode = strict_mode
    
    def detect_file_encoding(self, filepath: Union[str, Path]) -> EncodingResult:
        """Detect the encoding of a file.
        
        Args:
            filepath: Path to the file
            
        Returns:
            EncodingResult with detected encoding and confidence
        """
        filepath = Path(filepath)
        
        if not filepath.exists() or not filepath.is_file():
            logger.warning(f"File not found or not a file: {filepath}")
            return EncodingResult(
                encoding=self.default_encoding,
                confidence=EncodingConfidence.UNKNOWN,
                fallback_used=True,
            )
        
        try:
            # First check for BOM
            with open(filepath, "rb") as f:
                raw_data = f.read(4)  # Read first 4 bytes to check for BOM
                
                for bom, encoding in self.BOM_SIGNATURES.items():
                    if raw_data.startswith(bom):
                        logger.debug(f"BOM detected for {filepath}: {encoding}")
                        return EncodingResult(
                            encoding=encoding,
                            confidence=EncodingConfidence.HIGH,
                            bom_detected=True,
                        )
            
            # Read file and detect encoding using chardet
            with open(filepath, "rb") as f:
                raw_data = f.read(min(1024 * 1024, os.path.getsize(filepath)))  # Read up to 1MB
                
                detection = chardet.detect(raw_data)
                encoding = detection["encoding"]
                confidence = detection["confidence"]
                
                if not encoding:
                    logger.warning(f"Could not detect encoding for {filepath}, using default")
                    return EncodingResult(
                        encoding=self.default_encoding,
                        confidence=EncodingConfidence.UNKNOWN,
                        fallback_used=True,
                    )
                
                # Normalize encoding name
                encoding = encoding.lower().replace("-", "_")
                
                # Determine confidence level
                if confidence >= 0.9:
                    confidence_level = EncodingConfidence.HIGH
                elif confidence >= 0.6:
                    confidence_level = EncodingConfidence.MEDIUM
                else:
                    confidence_level = EncodingConfidence.LOW
                
                logger.debug(f"Detected encoding for {filepath}: {encoding} ({confidence})")
                return EncodingResult(
                    encoding=encoding,
                    confidence=confidence_level,
                )
                
        except (IOError, OSError) as e:
            logger.warning(f"Error detecting encoding for {filepath}: {e}")
            return EncodingResult(
                encoding=self.default_encoding,
                confidence=EncodingConfidence.UNKNOWN,
                fallback_used=True,
            )
    
    def read_file_with_encoding(
        self,
        filepath: Union[str, Path],
        encoding: Optional[str] = None,
        fallback_encodings: Optional[List[str]] = None,
    ) -> Tuple[Optional[str], EncodingResult]:
        """Read a file with the specified encoding, with fallbacks.
        
        Args:
            filepath: Path to the file
            encoding: Encoding to use (auto-detected if None)
            fallback_encodings: List of fallback encodings to try
            
        Returns:
            Tuple of (file_content, encoding_result)
        """
        filepath = Path(filepath)
        
        if not filepath.exists() or not filepath.is_file():
            logger.warning(f"File not found or not a file: {filepath}")
            return None, EncodingResult(
                encoding=self.default_encoding,
                confidence=EncodingConfidence.UNKNOWN,
                fallback_used=True,
            )
        
        # If encoding is not specified, detect it
        if not encoding:
            encoding_result = self.detect_file_encoding(filepath)
            encoding = encoding_result.encoding
        else:
            encoding_result = EncodingResult(
                encoding=encoding,
                confidence=EncodingConfidence.HIGH,
            )
        
        # Try to read with detected encoding
        try:
            with open(filepath, "r", encoding=encoding, errors="strict" if self.strict_mode else "replace") as f:
                content = f.read()
            return content, encoding_result
        except UnicodeDecodeError as e:
            logger.debug(f"Failed to read {filepath} with encoding {encoding}: {e}")
            
            # Try fallback encodings
            fallback_encodings = fallback_encodings or self.fallback_encodings
            for fallback_encoding in fallback_encodings:
                if fallback_encoding == encoding:
                    continue  # Skip already tried encoding
                
                try:
                    with open(filepath, "r", encoding=fallback_encoding, errors="strict" if self.strict_mode else "replace") as f:
                        content = f.read()
                    
                    logger.debug(f"Successfully read {filepath} with fallback encoding {fallback_encoding}")
                    return content, EncodingResult(
                        encoding=fallback_encoding,
                        confidence=EncodingConfidence.MEDIUM,
                        fallback_used=True,
                    )
                except UnicodeDecodeError:
                    continue
            
            # If all fallbacks fail, use default encoding with error replacement
            try:
                with open(filepath, "r", encoding=self.default_encoding, errors="replace") as f:
                    content = f.read()
                
                logger.warning(f"Falling back to default encoding with error replacement for {filepath}")
                return content, EncodingResult(
                    encoding=self.default_encoding,
                    confidence=EncodingConfidence.LOW,
                    fallback_used=True,
                )
            except Exception as e:
                logger.error(f"Failed to read {filepath} with any encoding: {e}")
                return None, EncodingResult(
                    encoding=self.default_encoding,
                    confidence=EncodingConfidence.UNKNOWN,
                    fallback_used=True,
                )
        except Exception as e:
            logger.error(f"Error reading {filepath}: {e}")
            return None, EncodingResult(
                encoding=self.default_encoding,
                confidence=EncodingConfidence.UNKNOWN,
                fallback_used=True,
            )
    
    def detect_language_from_encoding(self, encoding: str) -> Optional[str]:
        """Attempt to detect the likely language based on encoding.
        
        Args:
            encoding: File encoding
            
        Returns:
            Detected language code or None
        """
        encoding = encoding.lower().replace("-", "_")
        
        # Map encoding to likely language
        for language, encodings in self.LANGUAGE_ENCODINGS.items():
            if encoding in encodings:
                return language
        
        # Special cases
        if encoding in {"shift_jis", "euc_jp"}:
            return "ja"  # Japanese
        elif encoding in {"euc_kr", "cp949"}:
            return "ko"  # Korean
        elif encoding in {"gb2312", "gbk", "gb18030", "big5"}:
            return "zh"  # Chinese
        elif encoding in {"koi8_r", "cp1251"}:
            return "ru"  # Russian
        
        # No specific language detected
        return None