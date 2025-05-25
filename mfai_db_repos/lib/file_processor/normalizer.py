"""
Content normalization and preprocessing module.

This module provides functionality for normalizing and preprocessing file content
for better analysis and embedding generation.
"""
import re
import unicodedata
from enum import Enum
from typing import List, Optional, Tuple

import pygments
import pygments.lexers
import pygments.formatters
from pygments.lexers import guess_lexer
from pygments.util import ClassNotFound

from mfai_db_repos.utils.config import Config
from mfai_db_repos.utils.logger import get_logger

logger = get_logger(__name__)


class NormalizationLevel(str, Enum):
    """Levels of content normalization."""
    
    NONE = "none"  # No normalization
    MINIMAL = "minimal"  # Basic whitespace and encoding normalization
    STANDARD = "standard"  # Standard normalization with formatting and comment handling
    AGGRESSIVE = "aggressive"  # Aggressive normalization including code simplification


class ContentNormalizer:
    """Content normalization and preprocessing class."""
    
    # Common comment prefixes by language
    COMMENT_PREFIXES = {
        "python": ["#"],
        "javascript": ["//"],
        "typescript": ["//"],
        "java": ["//"],
        "c": ["//"],
        "c++": ["//"],
        "c#": ["//"],
        "go": ["//"],
        "rust": ["//"],
        "ruby": ["#"],
        "php": ["//", "#"],
        "html": ["<!--"],
        "css": ["/*"],
        "markdown": [],
        "text": [],
        "shell": ["#"],
        "yaml": ["#"],
        "json": [],
        "xml": ["<!--"],
    }
    
    # Block comment markers by language
    BLOCK_COMMENT_MARKERS = {
        "python": ("\"\"\"", "\"\"\""),
        "javascript": ("/*", "*/"),
        "typescript": ("/*", "*/"),
        "java": ("/*", "*/"),
        "c": ("/*", "*/"),
        "c++": ("/*", "*/"),
        "c#": ("/*", "*/"),
        "go": ("/*", "*/"),
        "rust": ("/*", "*/"),
        "php": ("/*", "*/"),
        "html": ("<!--", "-->"),
        "css": ("/*", "*/"),
        "markdown": ("", ""),
        "text": ("", ""),
        "shell": ("", ""),
        "yaml": ("", ""),
        "json": ("", ""),
        "xml": ("<!--", "-->"),
    }
    
    def __init__(
        self,
        config: Optional[Config] = None,
        normalization_level: NormalizationLevel = NormalizationLevel.STANDARD,
        max_line_length: int = 100,
        preserve_comments: bool = True,
        preserve_docstrings: bool = True,
        preserve_indentation: bool = True,
        remove_extra_whitespace: bool = True,
    ):
        """Initialize a content normalizer.
        
        Args:
            config: Optional Config instance
            normalization_level: Level of normalization to apply
            max_line_length: Maximum line length for wrapping
            preserve_comments: Whether to preserve comments
            preserve_docstrings: Whether to preserve docstrings
            preserve_indentation: Whether to preserve indentation
            remove_extra_whitespace: Whether to remove extra whitespace
        """
        self.config = config or Config()
        self.normalization_level = normalization_level
        self.max_line_length = max_line_length
        self.preserve_comments = preserve_comments
        self.preserve_docstrings = preserve_docstrings
        self.preserve_indentation = preserve_indentation
        self.remove_extra_whitespace = remove_extra_whitespace
    
    def normalize(
        self, 
        content: str, 
        language: Optional[str] = None,
        normalization_level: Optional[NormalizationLevel] = None,
    ) -> str:
        """Normalize content according to the specified level.
        
        Args:
            content: Content to normalize
            language: Language of the content (auto-detected if None)
            normalization_level: Override the default normalization level
            
        Returns:
            Normalized content
        """
        if not content:
            return content
        
        # Use specified normalization level or default
        level = normalization_level or self.normalization_level
        
        # Detect language if not provided
        if not language:
            language = self._detect_language(content)
        
        # Apply normalization based on level
        if level == NormalizationLevel.NONE:
            return content
        elif level == NormalizationLevel.MINIMAL:
            return self._apply_minimal_normalization(content)
        elif level == NormalizationLevel.STANDARD:
            return self._apply_standard_normalization(content, language)
        elif level == NormalizationLevel.AGGRESSIVE:
            return self._apply_aggressive_normalization(content, language)
        else:
            logger.warning(f"Unknown normalization level: {level}, using standard")
            return self._apply_standard_normalization(content, language)
    
    def _detect_language(self, content: str) -> str:
        """Detect the language of content.
        
        Args:
            content: Content to detect language for
            
        Returns:
            Detected language
        """
        try:
            lexer = guess_lexer(content)
            return lexer.name.lower()
        except ClassNotFound:
            # Default to text if can't detect
            return "text"
    
    def _apply_minimal_normalization(self, content: str) -> str:
        """Apply minimal normalization to content.
        
        Args:
            content: Content to normalize
            
        Returns:
            Normalized content
        """
        # Normalize Unicode
        content = unicodedata.normalize('NFC', content)
        
        # Normalize line endings to LF
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        
        # Remove null bytes
        content = content.replace('\0', '')
        
        # Remove BOM if present
        if content.startswith('\ufeff'):
            content = content[1:]
        
        # Handle trailing whitespace if configured
        if self.remove_extra_whitespace:
            # Remove trailing whitespace on each line
            lines = content.split('\n')
            lines = [line.rstrip() for line in lines]
            content = '\n'.join(lines)
            
            # Remove trailing blank lines
            content = content.rstrip('\n') + '\n'
        
        return content
    
    def _apply_standard_normalization(self, content: str, language: str) -> str:
        """Apply standard normalization to content.
        
        Args:
            content: Content to normalize
            language: Language of the content
            
        Returns:
            Normalized content
        """
        # First apply minimal normalization
        content = self._apply_minimal_normalization(content)
        
        # Get language-specific settings
        comment_prefixes = self.COMMENT_PREFIXES.get(language.lower(), ["#", "//"])
        block_comment_start, block_comment_end = self.BLOCK_COMMENT_MARKERS.get(
            language.lower(), ("/*", "*/")
        )
        
        # Process content line by line
        lines = content.split('\n')
        normalized_lines = []
        
        in_block_comment = False
        for line in lines:
            # Handle indentation
            if not self.preserve_indentation:
                line = line.lstrip()
            
            # Handle comments
            if not self.preserve_comments:
                # Handle line comments
                for prefix in comment_prefixes:
                    comment_pos = line.find(prefix)
                    if comment_pos >= 0:
                        line = line[:comment_pos].rstrip()
                        break
                
                # Skip empty lines after comment removal
                if not line.strip():
                    continue
            
            # Handle block comments
            if not self.preserve_comments and block_comment_start and block_comment_end:
                if in_block_comment:
                    end_pos = line.find(block_comment_end)
                    if end_pos >= 0:
                        line = line[end_pos + len(block_comment_end):].lstrip()
                        in_block_comment = False
                    else:
                        continue  # Skip this line inside a block comment
                
                start_pos = line.find(block_comment_start)
                if start_pos >= 0:
                    end_pos = line.find(block_comment_end, start_pos + len(block_comment_start))
                    if end_pos >= 0:
                        # Block comment ends on same line
                        line = line[:start_pos] + line[end_pos + len(block_comment_end):]
                    else:
                        # Block comment continues to next line
                        line = line[:start_pos]
                        in_block_comment = True
            
            # Handle multiple whitespace if configured
            if self.remove_extra_whitespace:
                # Replace tabs with spaces
                line = line.expandtabs(4)
                
                # Replace multiple spaces with a single space (except at beginning of line)
                if self.preserve_indentation:
                    # Preserve indentation
                    leading_space = re.match(r'^(\s*)', line).group(1)
                    rest_of_line = line[len(leading_space):]
                    rest_of_line = re.sub(r'\s+', ' ', rest_of_line)
                    line = leading_space + rest_of_line
                else:
                    line = re.sub(r'\s+', ' ', line)
            
            normalized_lines.append(line)
        
        return '\n'.join(normalized_lines)
    
    def _apply_aggressive_normalization(self, content: str, language: str) -> str:
        """Apply aggressive normalization to content.
        
        Args:
            content: Content to normalize
            language: Language of the content
            
        Returns:
            Normalized content
        """
        # First apply standard normalization
        content = self._apply_standard_normalization(content, language)
        
        # Try to use Pygments for syntax highlighting and formatting
        try:
            # Get lexer for the language
            if language.lower() == "text":
                # Don't try to format plain text
                return content
            
            try:
                lexer = pygments.lexers.get_lexer_by_name(language.lower())
            except ClassNotFound:
                lexer = pygments.lexers.guess_lexer(content)
            
            # Format the code
            formatter = pygments.formatters.get_formatter_by_name("text")
            
            # Generate highlighted code and strip ANSI control characters
            highlighted = pygments.highlight(content, lexer, formatter)
            
            # Additional processing after Pygments formatting
            lines = highlighted.split('\n')
            processed_lines = []
            
            for line in lines:
                # Remove trailing whitespace
                line = line.rstrip()
                
                # Apply additional processing for aggressive normalization
                # For example, convert identifiers to a standard form
                
                processed_lines.append(line)
            
            # Join lines and return
            result = '\n'.join(processed_lines)
            return result
            
        except Exception as e:
            logger.warning(f"Error during aggressive normalization: {e}")
            # Fall back to standard normalization
            return content
    
    def extract_code_blocks(
        self, 
        content: str, 
        language: Optional[str] = None
    ) -> List[Tuple[str, str]]:
        """Extract code blocks from content.
        
        Args:
            content: Content to extract code blocks from
            language: Language of the content
            
        Returns:
            List of (code, language) tuples
        """
        if not content:
            return []
        
        # Detect language if not provided
        if not language:
            language = self._detect_language(content)
        
        # For markdown, extract code blocks with language markers
        if language.lower() == "markdown":
            return self._extract_markdown_code_blocks(content)
        
        # For other languages, just return the whole content as a single block
        return [(content, language)]
    
    def _extract_markdown_code_blocks(self, content: str) -> List[Tuple[str, str]]:
        """Extract code blocks from markdown content.
        
        Args:
            content: Markdown content
            
        Returns:
            List of (code, language) tuples
        """
        code_blocks = []
        
        # Regular expression to match fenced code blocks
        # This matches ```language\ncode\n``` patterns
        pattern = r'```(\w*)\n(.*?)\n```'
        matches = re.findall(pattern, content, re.DOTALL)
        
        for lang, code in matches:
            if not lang:
                lang = "text"  # Default language
            code_blocks.append((code, lang))
        
        return code_blocks
    
    def normalize_for_embedding(
        self, 
        content: str, 
        language: Optional[str] = None,
        max_length: Optional[int] = None,
    ) -> str:
        """Normalize content specifically for embedding generation.
        
        Args:
            content: Content to normalize
            language: Language of the content
            max_length: Maximum content length (truncates if longer)
            
        Returns:
            Normalized content
        """
        if not content:
            return content
        
        # First apply standard normalization
        normalized = self.normalize(content, language, NormalizationLevel.STANDARD)
        
        # For code, extract and emphasize important parts
        if language and language.lower() != "text" and language.lower() != "markdown":
            # Try to extract function/class definitions and docstrings
            normalized = self._extract_important_code_parts(normalized, language)
        
        # Truncate if needed
        if max_length and len(normalized) > max_length:
            normalized = normalized[:max_length]
        
        return normalized
    
    def _extract_important_code_parts(self, content: str, language: str) -> str:
        """Extract and emphasize important parts of code.
        
        Args:
            content: Code content
            language: Language of the code
            
        Returns:
            Processed content emphasizing important parts
        """
        # Different extraction strategies based on language
        if language.lower() in {"python", "javascript", "typescript", "java", "c#", "go"}:
            return self._extract_classes_and_functions(content, language)
        else:
            # For other languages, just return normalized content
            return content
    
    def _extract_classes_and_functions(self, content: str, language: str) -> str:
        """Extract class and function definitions with docstrings.
        
        Args:
            content: Code content
            language: Programming language
            
        Returns:
            Processed content with class and function definitions
        """
        # Language-specific patterns for detecting classes and functions
        patterns = {
            "python": {
                "class": r'class\s+(\w+)[^\n{]*:',
                "function": r'def\s+(\w+)[^\n{]*:',
                "docstring": r'"""(.*?)"""',
            },
            "javascript": {
                "class": r'class\s+(\w+)[^\n{]*{',
                "function": r'function\s+(\w+)[^\n{]*{',
                "method": r'(\w+)\s*\([^)]*\)\s*{',
                "docstring": r'/\*\*(.*?)\*/',
            },
            "typescript": {
                "class": r'class\s+(\w+)[^\n{]*{',
                "function": r'function\s+(\w+)[^\n{]*{',
                "method": r'(\w+)\s*\([^)]*\)\s*[:{\n]',
                "docstring": r'/\*\*(.*?)\*/',
            },
            "java": {
                "class": r'class\s+(\w+)[^\n{]*{',
                "function": r'(public|private|protected)?\s+\w+\s+(\w+)\s*\([^)]*\)\s*[^;]*{',
                "docstring": r'/\*\*(.*?)\*/',
            },
            "c#": {
                "class": r'class\s+(\w+)[^\n{]*{',
                "function": r'(public|private|protected)?\s+\w+\s+(\w+)\s*\([^)]*\)\s*[^;]*{',
                "docstring": r'/\*\*(.*?)\*/',
            },
            "go": {
                "function": r'func\s+(\w+)[^\n{]*{',
                "struct": r'type\s+(\w+)\s+struct\s*{',
                "interface": r'type\s+(\w+)\s+interface\s*{',
                "comment": r'//\s*(.*?)$',
            },
        }
        
        # Get language-specific patterns
        lang_patterns = patterns.get(language.lower(), patterns["python"])
        
        # Extract important definitions
        important_parts = []
        
        # Add filename or module documentation if available
        file_docstring = self._extract_file_docstring(content, language)
        if file_docstring:
            important_parts.append(file_docstring)
        
        # Extract classes with their docstrings
        if "class" in lang_patterns:
            class_matches = re.finditer(lang_patterns["class"], content, re.MULTILINE)
            for match in class_matches:
                class_name = match.group(1)
                class_start = match.start()
                
                # Try to extract class docstring
                class_content = content[class_start:]
                docstring = self._extract_docstring(class_content, language)
                
                important_parts.append(f"CLASS: {class_name}")
                if docstring:
                    important_parts.append(f"DOCSTRING: {docstring}")
        
        # Extract functions/methods with their docstrings
        function_pattern = lang_patterns.get("function")
        if function_pattern:
            function_matches = re.finditer(function_pattern, content, re.MULTILINE)
            for match in function_matches:
                function_name = match.group(1) if "(" not in match.group(1) else match.group(2)
                function_start = match.start()
                
                # Try to extract function docstring
                function_content = content[function_start:]
                docstring = self._extract_docstring(function_content, language)
                
                important_parts.append(f"FUNCTION: {function_name}")
                if docstring:
                    important_parts.append(f"DOCSTRING: {docstring}")
        
        # If no important parts were found, return the original content
        if not important_parts:
            return content
        
        # Prepend the important parts to the original content
        important_summary = "\n".join(important_parts)
        return f"{important_summary}\n\n{content}"
    
    def _extract_file_docstring(self, content: str, language: str) -> str:
        """Extract file-level docstring.
        
        Args:
            content: Code content
            language: Programming language
            
        Returns:
            File docstring if found, empty string otherwise
        """
        # Language-specific patterns for file docstrings
        patterns = {
            "python": r'^"""(.*?)"""',
            "javascript": r'^/\*\*(.*?)\*/',
            "typescript": r'^/\*\*(.*?)\*/',
            "java": r'^/\*\*(.*?)\*/',
            "c#": r'^/\*\*(.*?)\*/',
            "go": r'^/\*(.*?)\*/',
        }
        
        pattern = patterns.get(language.lower())
        if not pattern:
            return ""
        
        match = re.search(pattern, content, re.DOTALL)
        if match:
            docstring = match.group(1)
            # Clean up the docstring
            docstring = re.sub(r'\n\s*\*\s*', ' ', docstring)  # Clean up multiline comments
            docstring = re.sub(r'\s+', ' ', docstring)  # Normalize whitespace
            return docstring.strip()
        
        return ""
    
    def _extract_docstring(self, content: str, language: str) -> str:
        """Extract docstring from code block.
        
        Args:
            content: Code content
            language: Programming language
            
        Returns:
            Docstring if found, empty string otherwise
        """
        # Language-specific patterns for docstrings
        patterns = {
            "python": r'"""(.*?)"""',
            "javascript": r'/\*\*(.*?)\*/',
            "typescript": r'/\*\*(.*?)\*/',
            "java": r'/\*\*(.*?)\*/',
            "c#": r'/\*\*(.*?)\*/',
            "go": r'//(.*?)$',
        }
        
        pattern = patterns.get(language.lower())
        if not pattern:
            return ""
        
        # For Go-style comments, look for a block of consecutive comment lines
        if language.lower() == "go":
            lines = content.split('\n')
            comment_lines = []
            for line in lines[:5]:  # Look at first few lines
                line = line.strip()
                if line.startswith('//'):
                    comment_lines.append(line[2:].strip())
                elif not comment_lines:
                    continue  # Still looking for first comment
                else:
                    break  # End of comment block
            
            if comment_lines:
                return ' '.join(comment_lines)
            return ""
        
        # For other languages, use regex pattern
        match = re.search(pattern, content, re.DOTALL)
        if match:
            docstring = match.group(1)
            # Clean up the docstring
            docstring = re.sub(r'\n\s*\*\s*', ' ', docstring)  # Clean up multiline comments
            docstring = re.sub(r'\s+', ' ', docstring)  # Normalize whitespace
            return docstring.strip()
        
        return ""