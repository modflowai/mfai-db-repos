"""
Metadata extraction module for repositories and files.

This module provides functionality for extracting and analyzing metadata
from repositories and files to enhance the indexed content.
"""
import os
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import git
import pygments
import pygments.lexers
from pygments.lexers import get_lexer_for_filename
from pygments.token import Token
from pygments.util import ClassNotFound

from mfai_db_repos.lib.git.repository import GitRepository
from mfai_db_repos.utils.logger import get_logger

logger = get_logger(__name__)


class MetadataExtractor:
    """Metadata extraction and analysis class."""

    # Technical complexity levels
    COMPLEXITY_LEVELS = ["low", "medium", "high", "very_high"]

    def __init__(self):
        """Initialize a metadata extractor."""

    def extract_repository_metadata(self, git_repo: GitRepository) -> Dict[str, Union[str, int, List[str]]]:
        """Extract metadata from a Git repository.

        Args:
            git_repo: Git repository instance

        Returns:
            Dictionary with repository metadata
        """
        metadata = {}
        
        if not git_repo.is_cloned() or not git_repo.repo:
            return metadata
        
        try:
            # Basic repository information
            repo = git_repo.repo
            
            # Get repository statistics
            stats = git_repo.get_repo_stats()
            metadata.update(stats)
            
            # Get primary language
            languages = self._get_repository_languages(git_repo)
            if languages:
                metadata["primary_language"] = languages[0][0]
                metadata["languages"] = [lang for lang, _ in languages[:10]]  # Top 10 languages
            
            # Get top contributors
            contributors = self._get_top_contributors(git_repo)
            if contributors:
                metadata["top_contributors"] = [name for name, _ in contributors[:5]]  # Top 5 contributors
            
            # Check if it has readme
            repo_path = Path(repo.working_dir)
            readme_files = list(repo_path.glob("README*"))
            metadata["has_readme"] = len(readme_files) > 0
            
            # Check if it has license
            license_files = list(repo_path.glob("LICENSE*")) + list(repo_path.glob("COPYING*"))
            metadata["has_license"] = len(license_files) > 0
            
            # Check if it has tests
            test_dirs = []
            for root, dirs, _ in os.walk(repo_path):
                if any(test_dir in dirs for test_dir in ["test", "tests", "spec", "specs"]):
                    test_dirs.append(root)
            metadata["has_tests"] = len(test_dirs) > 0
            
            return metadata
        except Exception as e:
            logger.warning(f"Failed to extract repository metadata: {e}")
            return metadata

    def _get_repository_languages(self, git_repo: GitRepository) -> List[Tuple[str, int]]:
        """Get the languages used in a repository by file count.

        Args:
            git_repo: Git repository instance

        Returns:
            List of (language, count) tuples sorted by count
        """
        if not git_repo.is_cloned() or not git_repo.repo:
            return []
        
        repo_path = Path(git_repo.repo.working_dir)
        language_counts = Counter()
        
        for root, _, files in os.walk(repo_path):
            # Skip .git directory
            if ".git" in Path(root).parts:
                continue
            
            for filename in files:
                filepath = Path(root) / filename
                
                try:
                    # Try to get lexer for the file
                    lexer = get_lexer_for_filename(filepath.name)
                    language = lexer.name
                    language_counts[language] += 1
                except ClassNotFound:
                    # If no lexer found, use extension
                    ext = filepath.suffix.lower()
                    if ext:
                        language_counts[ext[1:]] += 1  # Remove leading dot
                    else:
                        language_counts["unknown"] += 1
        
        # Sort by count
        return sorted(language_counts.items(), key=lambda x: x[1], reverse=True)

    def _get_top_contributors(self, git_repo: GitRepository) -> List[Tuple[str, int]]:
        """Get the top contributors to a repository.

        Args:
            git_repo: Git repository instance

        Returns:
            List of (author, commit_count) tuples sorted by commit count
        """
        if not git_repo.is_cloned() or not git_repo.repo:
            return []
        
        try:
            repo = git_repo.repo
            
            # Count commits by author
            author_counts = Counter()
            for commit in repo.iter_commits(max_count=500):  # Limit to avoid slow operation
                author = f"{commit.author.name} <{commit.author.email}>"
                author_counts[author] += 1
            
            # Sort by commit count
            return sorted(author_counts.items(), key=lambda x: x[1], reverse=True)
        except (git.GitCommandError, AttributeError) as e:
            logger.warning(f"Failed to get top contributors: {e}")
            return []

    def extract_file_metadata(
        self,
        filepath: Union[str, Path],
        content: Optional[str] = None,
    ) -> Dict[str, Union[str, int, List[str]]]:
        """Extract metadata from a file.

        Args:
            filepath: Path to the file
            content: Optional file content (if already available)

        Returns:
            Dictionary with file metadata
        """
        filepath = Path(filepath)
        metadata = {}
        
        try:
            # Basic file information
            metadata["filename"] = filepath.name
            metadata["extension"] = filepath.suffix.lower()
            
            # Read content if not provided
            if content is None and filepath.exists():
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                except UnicodeDecodeError:
                    # If UTF-8 fails, skip content analysis
                    content = None
            
            # If content is available, analyze it
            if content:
                # Detect language
                try:
                    lexer = get_lexer_for_filename(filepath.name)
                    metadata["language"] = lexer.name
                except ClassNotFound:
                    metadata["language"] = "text"
                
                # Count lines
                lines = content.splitlines()
                metadata["line_count"] = len(lines)
                
                # Count non-empty lines
                metadata["non_empty_line_count"] = sum(1 for line in lines if line.strip())
                
                # Estimate complexity
                metadata["complexity"] = self._estimate_complexity(content, metadata.get("language", "text"))
                
                # Extract keywords
                metadata["keywords"] = self._extract_keywords(content, metadata.get("language", "text"))
            
            return metadata
        except Exception as e:
            logger.warning(f"Failed to extract file metadata for {filepath}: {e}")
            return metadata

    def _estimate_complexity(self, content: str, language: str) -> str:
        """Estimate the technical complexity of file content.

        Args:
            content: File content
            language: Programming language

        Returns:
            Complexity level (low, medium, high, very_high)
        """
        # Simple heuristics for complexity estimation
        line_count = len(content.splitlines())
        
        # Check for complex patterns
        patterns = {
            "class_def": r"\\bclass\\s+\\w+",
            "function_def": r"\\bdef\\s+\\w+|function\\s+\\w+",
            "conditional": r"\\bif\\s+|\\belse\\s+|\\belif\\s+|\\bswitch\\s+|\\bcase\\s+",
            "loop": r"\\bfor\\s+|\\bwhile\\s+|\\bdo\\s+",
            "import": r"\\bimport\\s+|\\brequire\\s+|\\binclude\\s+",
            "exception": r"\\btry\\s+|\\bcatch\\s+|\\bexcept\\s+|\\bfinally\\s+|\\bthrow\\s+|\\braise\\s+",
            "async": r"\\basync\\s+|\\bawait\\s+|\\bPromise\\b|\\bfuture\\b",
            "regex": r"\\bregex\\b|\\bpattern\\b|\\b[r]?[\"\'].*?[\\\\/\\[\\]\\(\\)\\{\\}\\*\\+\\?\\|].*?[\"\']",
        }
        
        # Count pattern matches
        complexity_score = 0
        for pattern_name, pattern in patterns.items():
            matches = len(re.findall(pattern, content, re.IGNORECASE))
            complexity_score += matches
        
        # Normalize by line count to get complexity per line
        if line_count > 0:
            complexity_per_line = complexity_score / line_count
        else:
            complexity_per_line = 0
        
        # Determine complexity level
        if complexity_per_line < 0.1 or line_count < 20:
            return "low"
        elif complexity_per_line < 0.2 or line_count < 100:
            return "medium"
        elif complexity_per_line < 0.3 or line_count < 500:
            return "high"
        else:
            return "very_high"

    def _extract_keywords(self, content: str, language: str) -> List[str]:
        """Extract important keywords from file content.

        Args:
            content: File content
            language: Programming language

        Returns:
            List of keywords
        """
        # Try to use Pygments for token extraction
        try:
            lexer = pygments.lexers.get_lexer_by_name(language.lower())
        except ClassNotFound:
            try:
                lexer = pygments.lexers.guess_lexer(content)
            except ClassNotFound:
                # Fallback to regex-based extraction
                return self._extract_keywords_with_regex(content)
        
        # Extract tokens using Pygments
        tokens = list(pygments.lex(content, lexer))
        
        # Collect important tokens
        keywords = []
        current_identifier = ""
        
        for token_type, value in tokens:
            if token_type in Token.Name or token_type in Token.Keyword:
                # Skip common keywords and short identifiers
                if (
                    len(value) > 2
                    and value not in ["def", "class", "function", "import", "from", "public", "private"]
                    and not value.startswith("__")
                ):
                    keywords.append(value)
        
        # Limit to unique keywords
        unique_keywords = list(set(keywords))
        
        # Sort by length (longer keywords are often more specific)
        unique_keywords.sort(key=len, reverse=True)
        
        # Return top 20 keywords
        return unique_keywords[:20]

    def _extract_keywords_with_regex(self, content: str) -> List[str]:
        """Extract keywords using regex patterns when Pygments lexer is not available.

        Args:
            content: File content

        Returns:
            List of keywords
        """
        # Define patterns for identifier extraction
        identifier_pattern = r"\\b[a-zA-Z_][a-zA-Z0-9_]{2,}\\b"
        
        # Extract all identifiers
        identifiers = re.findall(identifier_pattern, content)
        
        # Count occurrence of each identifier
        counter = Counter(identifiers)
        
        # Get most common identifiers, excluding very common ones
        common_words = {"the", "and", "this", "that", "with", "from", "have", "for", "not", "are", "function"}
        keywords = [word for word, count in counter.most_common(30) if word.lower() not in common_words]
        
        return keywords[:20]