"""
README Builder Tool - Extracts analysis from database and builds comprehensive READMEs.

This tool implements the hybrid README rebuilding system that combines:
1. Database analysis extraction
2. File system structure
3. AI-generated summaries and navigation
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from mfai_db_repos.lib.database.models import Repository, RepositoryFile
from mfai_db_repos.lib.database.connection import get_connection_url
from mfai_db_repos.utils.logger import get_logger
from mfai_db_repos.utils.env import load_env

# Load environment variables
load_env()

logger = get_logger(__name__)


class ReadmeBuilder:
    """Builds comprehensive README files from database analysis and file structure."""
    
    def __init__(self, repo_path: str, repo_name: Optional[str] = None):
        """Initialize the README builder.
        
        Args:
            repo_path: Path to the repository
            repo_name: Repository name in database (defaults to directory name)
        """
        self.repo_path = Path(repo_path)
        self.repo_name = repo_name or self.repo_path.name
        self.file_analyses: Dict[str, dict] = {}
        self.directory_structure: Dict[str, List[str]] = defaultdict(list)
        
    def extract_database_analysis(self) -> bool:
        """Extract all file analysis data from the database.
        
        Returns:
            True if extraction succeeded, False otherwise
        """
        try:
            # Use DATABASE_URL directly from environment for simplicity
            database_url = os.environ.get("DATABASE_URL")
            if not database_url:
                # Fall back to building URL from components
                from mfai_db_repos.utils.config import config
                config.load_from_env()
                db_config = config.config.database
                database_url = f"postgresql://{db_config.user}:{db_config.password}@{db_config.host}:{db_config.port}/{db_config.database}"
                if db_config.sslmode == "require":
                    database_url += "?sslmode=require"
            
            # Create sync engine and session
            engine = create_engine(database_url)
            Session = sessionmaker(bind=engine)
            
            with Session() as session:
                # Get repository
                repo = session.query(Repository).filter(
                    Repository.name == self.repo_name
                ).first()
                
                if not repo:
                    logger.error(f"Repository '{self.repo_name}' not found in database")
                    return False
                
                # Get all files for this repository
                files = session.query(RepositoryFile).filter(
                    RepositoryFile.repo_id == repo.id
                ).all()
                
                logger.info(f"Found {len(files)} files in database for {self.repo_name}")
                
                # Extract analysis for each file
                for file in files:
                    if file.analysis:
                        try:
                            analysis = json.loads(file.analysis) if isinstance(file.analysis, str) else file.analysis
                            self.file_analyses[file.filepath] = {
                                'title': analysis.get('title', file.filepath),
                                'summary': analysis.get('summary', ''),
                                'key_concepts': analysis.get('key_concepts', []),
                                'potential_questions': analysis.get('potential_questions', []),
                                'keywords': analysis.get('keywords', []),
                                'technical_level': file.technical_level,
                                'file_type': file.file_type,
                                'tags': file.tags if file.tags else []
                            }
                            
                            # Build directory structure
                            dir_path = str(Path(file.filepath).parent)
                            if dir_path == '.':
                                dir_path = ''
                            self.directory_structure[dir_path].append(file.filepath)
                            
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse analysis for {file.filepath}")
                
                logger.info(f"Successfully extracted {len(self.file_analyses)} file analyses")
                return True
                
        except Exception as e:
            logger.error(f"Failed to extract database analysis: {e}")
            return False
    
    def _create_directory_tree(self, indent: int = 0, current_dir: str = '') -> List[str]:
        """Create a visual directory tree with descriptions.
        
        Args:
            indent: Current indentation level
            current_dir: Current directory path
            
        Returns:
            List of tree lines
        """
        lines = []
        indent_str = '  ' * indent
        
        # Get subdirectories and files for current directory
        subdirs = []
        files = self.directory_structure.get(current_dir, [])
        
        # Find subdirectories
        for dir_path in self.directory_structure:
            if dir_path == current_dir:
                continue
            if dir_path.startswith(current_dir):
                # Check if this is a direct subdirectory
                relative = dir_path[len(current_dir):].lstrip('/')
                if '/' not in relative and relative:
                    subdirs.append(relative)
        
        # Sort subdirectories and files
        subdirs.sort()
        files.sort()
        
        # Add subdirectories
        for subdir in subdirs:
            full_path = os.path.join(current_dir, subdir) if current_dir else subdir
            lines.append(f"{indent_str}├── {subdir}/")
            lines.extend(self._create_directory_tree(indent + 1, full_path))
        
        # Add files with descriptions
        for i, file_path in enumerate(files):
            if Path(file_path).parent == Path(current_dir):
                file_name = Path(file_path).name
                is_last = i == len(files) - 1 and not subdirs
                prefix = '└──' if is_last else '├──'
                
                analysis = self.file_analyses.get(file_path, {})
                title = analysis.get('title', '')
                if title and title != file_name:
                    lines.append(f"{indent_str}{prefix} {file_name} - {title}")
                else:
                    lines.append(f"{indent_str}{prefix} {file_name}")
        
        return lines
    
    def _generate_topic_indexes(self) -> Dict[str, List[str]]:
        """Generate topic-based indexes from file analyses.
        
        Returns:
            Dictionary mapping topics to file paths
        """
        topic_index = defaultdict(list)
        
        for file_path, analysis in self.file_analyses.items():
            # Extract topics from keywords and key concepts
            topics = set()
            
            # Add from keywords
            for keyword in analysis.get('keywords', []):
                topics.add(keyword.lower())
            
            # Add from key concepts (simplified)
            for concept in analysis.get('key_concepts', []):
                # Extract main topic from concept
                if isinstance(concept, str):
                    main_topic = concept.split(':')[0].strip().lower()
                    topics.add(main_topic)
            
            # Add from file type
            file_type = analysis.get('file_type', '')
            if file_type:
                topics.add(file_type.lower())
            
            # Map file to topics
            for topic in topics:
                topic_index[topic].append(file_path)
        
        # Sort topics and remove small ones
        filtered_topics = {}
        for topic, files in sorted(topic_index.items()):
            if len(files) >= 2:  # Only keep topics with 2+ files
                filtered_topics[topic] = sorted(files)
        
        return filtered_topics
    
    def _collect_all_questions(self) -> List[str]:
        """Collect all unique potential questions from analyses.
        
        Returns:
            List of unique questions
        """
        all_questions = set()
        
        for analysis in self.file_analyses.values():
            for question in analysis.get('potential_questions', []):
                if isinstance(question, str) and question.strip():
                    all_questions.add(question.strip())
        
        return sorted(list(all_questions))
    
    def build_readme(self) -> str:
        """Build a comprehensive README from the extracted data.
        
        Returns:
            Complete README content as markdown
        """
        sections = []
        
        # Header
        sections.append(f"# {self.repo_name.upper()} Repository")
        sections.append("")
        sections.append(f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        sections.append("")
        
        # Quick Navigation
        sections.append("## 🗺️ Quick Navigation")
        sections.append("")
        sections.append("- [Directory Structure](#directory-structure)")
        sections.append("- [File Descriptions](#file-descriptions)")
        sections.append("- [Topic Index](#topic-index)")
        sections.append("- [Common Questions](#common-questions)")
        sections.append("- [Search Keywords](#search-keywords)")
        sections.append("")
        
        # Directory Structure
        sections.append("## 📁 Directory Structure")
        sections.append("")
        sections.append("```")
        sections.append(f"{self.repo_name}/")
        tree_lines = self._create_directory_tree(indent=1)
        sections.extend(tree_lines)
        sections.append("```")
        sections.append("")
        
        # File Descriptions
        sections.append("## 📄 File Descriptions")
        sections.append("")
        
        # Group files by directory
        dirs_processed = set()
        for dir_path in sorted(self.directory_structure.keys()):
            if dir_path and dir_path not in dirs_processed:
                sections.append(f"### {dir_path}/")
                sections.append("")
                dirs_processed.add(dir_path)
            elif not dir_path:
                sections.append("### Root Directory")
                sections.append("")
            
            # Add files in this directory
            files = self.directory_structure[dir_path]
            for file_path in sorted(files):
                analysis = self.file_analyses.get(file_path, {})
                file_name = Path(file_path).name
                
                sections.append(f"#### `{file_name}`")
                
                # Summary
                summary = analysis.get('summary', 'No summary available.')
                sections.append(f"*{summary}*")
                sections.append("")
                
                # Key concepts
                concepts = analysis.get('key_concepts', [])
                if concepts:
                    sections.append("**Key Concepts:**")
                    for concept in concepts[:5]:  # Limit to 5
                        sections.append(f"- {concept}")
                    sections.append("")
                
                # Technical level and type
                tech_level = analysis.get('technical_level', 'unknown')
                file_type = analysis.get('file_type', 'unknown')
                sections.append(f"*Technical Level: {tech_level} | Type: {file_type}*")
                sections.append("")
        
        # Topic Index
        sections.append("## 🏷️ Topic Index")
        sections.append("")
        sections.append("*Files grouped by topic for easy discovery:*")
        sections.append("")
        
        topic_index = self._generate_topic_indexes()
        for topic, files in sorted(topic_index.items()):
            sections.append(f"### {topic.title()}")
            for file_path in files[:10]:  # Limit to 10 files per topic
                file_name = Path(file_path).name
                sections.append(f"- `{file_path}` - {self.file_analyses.get(file_path, {}).get('title', file_name)}")
            if len(files) > 10:
                sections.append(f"- *...and {len(files) - 10} more files*")
            sections.append("")
        
        # Common Questions
        sections.append("## ❓ Common Questions")
        sections.append("")
        sections.append("*Questions that this repository's documentation can help answer:*")
        sections.append("")
        
        questions = self._collect_all_questions()
        for i, question in enumerate(questions[:20], 1):  # Top 20 questions
            sections.append(f"{i}. {question}")
        sections.append("")
        
        # Search Keywords
        sections.append("## 🔍 Search Keywords")
        sections.append("")
        sections.append("*Use these keywords to find relevant files:*")
        sections.append("")
        
        # Collect all keywords
        all_keywords = set()
        for analysis in self.file_analyses.values():
            for keyword in analysis.get('keywords', []):
                if keyword:
                    all_keywords.add(keyword)
        
        # Group keywords by first letter
        keyword_groups = defaultdict(list)
        for keyword in sorted(all_keywords):
            first_letter = keyword[0].upper()
            keyword_groups[first_letter].append(keyword)
        
        # Display keywords
        for letter in sorted(keyword_groups.keys()):
            keywords = keyword_groups[letter]
            sections.append(f"**{letter}:** {', '.join(keywords[:10])}")
            if len(keywords) > 10:
                sections.append(f"  *...and {len(keywords) - 10} more*")
        
        sections.append("")
        sections.append("---")
        sections.append("")
        sections.append("*This README was automatically generated using AI analysis of the repository contents.*")
        
        return '\n'.join(sections)
    
    def save_readme(self, output_path: Optional[str] = None) -> str:
        """Save the generated README to a file.
        
        Args:
            output_path: Path to save README (defaults to repo_path/README_GENERATED.md)
            
        Returns:
            Path where README was saved
        """
        if not output_path:
            output_path = self.repo_path / "README_GENERATED.md"
        else:
            output_path = Path(output_path)
        
        readme_content = self.build_readme()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        logger.info(f"README saved to {output_path}")
        return str(output_path)


def main():
    """Main function to build README for a repository."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Build comprehensive README from database analysis")
    parser.add_argument("repo_path", help="Path to the repository")
    parser.add_argument("--repo-name", help="Repository name in database (defaults to directory name)")
    parser.add_argument("--output", help="Output path for README (defaults to repo_path/README_GENERATED.md)")
    
    args = parser.parse_args()
    
    # Create builder
    builder = ReadmeBuilder(args.repo_path, args.repo_name)
    
    # Extract analysis
    if not builder.extract_database_analysis():
        logger.error("Failed to extract database analysis")
        return 1
    
    # Save README
    output_path = builder.save_readme(args.output)
    print(f"README generated successfully: {output_path}")
    
    return 0


if __name__ == "__main__":
    exit(main())