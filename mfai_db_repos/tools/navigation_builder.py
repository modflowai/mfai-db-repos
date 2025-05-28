"""
Navigation Metadata Builder - Extracts patterns and builds navigation guides for MCP tools.

This tool implements Step 1 of the Navigation Metadata System:
1. Pattern extraction from database analysis
2. Fixed-size navigation structure generation
3. Query routing rules creation
"""
import json
import os
import re
from collections import defaultdict, Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from mfai_db_repos.lib.database.models import Repository, RepositoryFile
from mfai_db_repos.utils.logger import get_logger
from mfai_db_repos.utils.env import load_env

# Load environment variables
load_env()

logger = get_logger(__name__)


class NavigationBuilder:
    """Builds navigation metadata from repository analysis."""
    
    def __init__(self, repo_name: str):
        """Initialize the navigation builder.
        
        Args:
            repo_name: Repository name in database
        """
        self.repo_name = repo_name
        self.file_analyses: Dict[str, dict] = {}
        self.all_keywords: List[str] = []
        self.all_concepts: List[str] = []
        self.all_questions: List[str] = []
        self.error_patterns: Set[str] = set()
        self.parameter_patterns: Set[str] = set()
        self.tool_references: Set[str] = set()
        
    def extract_from_database(self) -> bool:
        """Extract analysis data from database."""
        try:
            # Use DATABASE_URL directly
            database_url = os.environ.get("DATABASE_URL")
            if not database_url:
                from mfai_db_repos.utils.config import config
                config.load_from_env()
                db_config = config.config.database
                database_url = f"postgresql://{db_config.user}:{db_config.password}@{db_config.host}:{db_config.port}/{db_config.database}"
                if db_config.sslmode == "require":
                    database_url += "?sslmode=require"
            
            engine = create_engine(database_url)
            Session = sessionmaker(bind=engine)
            
            with Session() as session:
                # Get repository
                repo = session.query(Repository).filter(
                    Repository.name == self.repo_name
                ).first()
                
                if not repo:
                    logger.error(f"Repository '{self.repo_name}' not found")
                    return False
                
                self.repo_id = repo.id
                self.repo_url = repo.url
                
                # Get all files
                files = session.query(RepositoryFile).filter(
                    RepositoryFile.repo_id == repo.id
                ).all()
                
                logger.info(f"Processing {len(files)} files for navigation")
                
                # Extract patterns from each file
                for file in files:
                    if file.analysis:
                        try:
                            analysis = json.loads(file.analysis) if isinstance(file.analysis, str) else file.analysis
                            
                            # Store for pattern extraction
                            self.file_analyses[file.filepath] = analysis
                            
                            # Collect all keywords and concepts
                            self.all_keywords.extend(analysis.get('keywords', []))
                            self.all_concepts.extend(analysis.get('key_concepts', []))
                            self.all_questions.extend(analysis.get('potential_questions', []))
                            
                            # Extract patterns from content
                            self._extract_patterns_from_file(file, analysis)
                            
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse analysis for {file.filepath}")
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to extract from database: {e}")
            return False
    
    def _extract_patterns_from_file(self, file: RepositoryFile, analysis: dict):
        """Extract query patterns from file content and analysis."""
        # Look for error patterns in summaries and questions
        text_to_scan = " ".join([
            analysis.get('summary', ''),
            " ".join(analysis.get('potential_questions', [])),
            " ".join(analysis.get('key_concepts', []))
        ])
        
        # Extract ERROR/WARNING patterns
        error_matches = re.findall(r'(ERROR|WARNING|FAILED?):?\s*[^.]+', text_to_scan, re.IGNORECASE)
        self.error_patterns.update(error_matches[:20])  # Limit to top 20
        
        # Extract UPPERCASE parameter patterns
        param_matches = re.findall(r'\b[A-Z][A-Z_]+[A-Z]\b', text_to_scan)
        # Filter out common words
        param_matches = [p for p in param_matches if len(p) > 3 and p not in ['THE', 'AND', 'FOR', 'WITH']]
        self.parameter_patterns.update(param_matches[:30])  # Limit to top 30
        
        # Look for tool references (other repos)
        tool_keywords = ['MODFLOW', 'PEST', 'FloPy', 'pyEMU', 'PLPROC', 'MT3D', 'SEAWAT', 'USG']
        for tool in tool_keywords:
            if tool.lower() in text_to_scan.lower() and tool.lower() not in self.repo_name.lower():
                self.tool_references.add(tool)
    
    def _calculate_expertise_scores(self) -> Dict[str, int]:
        """Calculate what this repository is THE authority on."""
        # Count keyword frequencies
        keyword_freq = Counter(k.lower() for k in self.all_keywords if k)
        concept_freq = Counter()
        
        # Extract main topics from concepts
        for concept in self.all_concepts:
            if isinstance(concept, str):
                # Extract first part before colon or dash
                main_topic = concept.split(':')[0].split('-')[0].strip().lower()
                if main_topic:
                    concept_freq[main_topic] += 1
        
        # Combine frequencies
        all_freq = keyword_freq + concept_freq
        
        # Get top expertise areas
        expertise = {}
        for topic, count in all_freq.most_common(10):
            # Score from 1-10 based on frequency
            if count > 20:
                score = 10
            elif count > 15:
                score = 9
            elif count > 10:
                score = 8
            elif count > 5:
                score = 7
            else:
                score = 5
            expertise[topic] = score
        
        return expertise
    
    def _generate_primary_purpose(self) -> str:
        """Generate a one-sentence primary purpose."""
        # Simple approach: Find the most common themes
        top_keywords = Counter(self.all_keywords).most_common(5)
        top_concepts = Counter(c.split(':')[0].strip() for c in self.all_concepts if isinstance(c, str)).most_common(3)
        
        # Build a purpose statement
        main_topic = top_concepts[0][0] if top_concepts else "analysis"
        supporting_topics = [k[0] for k in top_keywords[:3] if k[0]]
        
        purpose = f"{main_topic.capitalize()} tool for {', '.join(supporting_topics)}"
        
        # Refine based on repo name
        if 'pest' in self.repo_name.lower():
            purpose = "Parameter estimation and model calibration tool for groundwater modeling"
        elif 'modflow' in self.repo_name.lower():
            purpose = "Groundwater flow modeling system for simulating aquifer behavior"
        elif 'flopy' in self.repo_name.lower():
            purpose = "Python package for creating, running, and post-processing MODFLOW models"
        
        return purpose
    
    def _build_query_router(self) -> List[Dict[str, str]]:
        """Build query pattern to tool mapping."""
        router = []
        
        # Error patterns
        if self.error_patterns:
            router.append({
                "pattern": "ERROR: or error messages",
                "pattern_type": "quoted error text",
                "tool": "FTS",
                "example": f'"{list(self.error_patterns)[0]}"' if self.error_patterns else "ERROR: message"
            })
        
        # Parameter patterns
        if self.parameter_patterns:
            router.append({
                "pattern": "UPPERCASE_PARAMETERS",
                "pattern_type": "control file variables",
                "tool": "FTS",
                "example": list(self.parameter_patterns)[0] if self.parameter_patterns else "PARAM_NAME"
            })
        
        # Conceptual patterns
        router.extend([
            {
                "pattern": "how to ...",
                "pattern_type": "workflow questions",
                "tool": "Vector",
                "example": "how to set up calibration"
            },
            {
                "pattern": "what is ...",
                "pattern_type": "concept explanations",
                "tool": "Vector",
                "example": "what is regularization"
            },
            {
                "pattern": "explain ...",
                "pattern_type": "theory questions",
                "tool": "Vector",
                "example": "explain Jacobian matrix"
            }
        ])
        
        return router
    
    def build_navigation_structure(self) -> Dict:
        """Build the complete navigation structure."""
        expertise_scores = self._calculate_expertise_scores()
        query_router = self._build_query_router()
        
        # Determine repository type
        total_files = len(self.file_analyses)
        md_files = sum(1 for f in self.file_analyses if f.endswith('.md'))
        py_files = sum(1 for f in self.file_analyses if f.endswith('.py'))
        
        if md_files > py_files * 2:
            repo_type = "documentation"
        elif py_files > md_files * 2:
            repo_type = "code"
        else:
            repo_type = "hybrid"
        
        # Build FTS and Vector use cases
        fts_keywords = list(self.parameter_patterns)[:10] + [p.split(':')[0] for p in self.error_patterns][:5]
        vector_topics = [q for q in self.all_questions if any(starter in q.lower() for starter in ['how', 'what', 'why', 'when'])][:5]
        
        navigation = {
            "repository_name": self.repo_name,
            "repository_type": repo_type,
            "primary_purpose": self._generate_primary_purpose(),
            "expertise_scores": expertise_scores,
            "query_routing": {
                "router_table": query_router,
                "fts_triggers": ["ERROR:", "WARNING:", "UPPERCASE_WORDS", "quoted strings"],
                "vector_triggers": ["how to", "what is", "explain", "why", "when to use"]
            },
            "search_guidance": {
                "use_fts_for": fts_keywords[:10],
                "use_vector_for": vector_topics[:5],
                "common_patterns": [
                    {"query": f"{self.repo_name} error", "tool": "FTS"},
                    {"query": f"{self.repo_name} tutorial", "tool": "Vector"},
                    {"query": list(self.parameter_patterns)[0] if self.parameter_patterns else "PARAM", "tool": "FTS"}
                ]
            },
            "integration_context": {
                "references_tools": list(self.tool_references),
                "typical_workflow": "Unknown - requires Step 2 LLM analysis"
            },
            "statistics": {
                "total_files": total_files,
                "unique_concepts": len(set(self.all_concepts)),
                "unique_keywords": len(set(self.all_keywords)),
                "documentation_files": md_files,
                "code_files": py_files
            }
        }
        
        return navigation
    
    def generate_navigation_markdown(self, nav_data: Dict) -> str:
        """Generate navigation-focused markdown (max 100 lines)."""
        lines = []
        
        # Header
        lines.append(f"# {nav_data['repository_name'].upper()} - Navigation Guide")
        lines.append("")
        
        # Primary Purpose
        lines.append("## 🎯 Primary Purpose")
        lines.append(nav_data['primary_purpose'])
        lines.append("")
        
        # Search Guidance
        lines.append("## 🔍 Search Guidance")
        fts_items = nav_data['search_guidance']['use_fts_for'][:5]
        vector_items = nav_data['search_guidance']['use_vector_for'][:3]
        
        lines.append(f"- **Use FTS for:** {', '.join(fts_items)}")
        lines.append(f"- **Use Vector for:** {', '.join(vector_items)}")
        lines.append(f"- **Repository type:** {nav_data['repository_type']}")
        lines.append("")
        
        # Query Router
        lines.append("## 📊 Query Router")
        lines.append("| Pattern | Type | Tool | Example |")
        lines.append("|---------|------|------|---------|")
        for route in nav_data['query_routing']['router_table'][:5]:
            lines.append(f"| {route['pattern']} | {route['pattern_type']} | {route['tool']} | {route['example']} |")
        lines.append("")
        
        # Expertise
        lines.append("## 🏷️ Repository Expertise")
        top_expertise = sorted(nav_data['expertise_scores'].items(), key=lambda x: x[1], reverse=True)[:5]
        lines.append(f"**Authoritative for:** {', '.join(k for k, v in top_expertise)}")
        lines.append("")
        
        # Integration
        if nav_data['integration_context']['references_tools']:
            lines.append("## 🔗 Integration Context")
            lines.append(f"**References:** {', '.join(nav_data['integration_context']['references_tools'])}")
            lines.append("")
        
        # Keep under 100 lines
        return '\n'.join(lines[:100])
    
    def save_outputs(self, output_dir: Path = None) -> Tuple[str, str]:
        """Save navigation markdown and JSON metadata."""
        if output_dir is None:
            output_dir = Path(f"analyzed_repos/{self.repo_name}")
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Build navigation structure
        nav_data = self.build_navigation_structure()
        
        # Save JSON metadata
        json_path = output_dir / "navigation_metadata.json"
        with open(json_path, 'w') as f:
            json.dump(nav_data, f, indent=2)
        
        # Save navigation markdown
        markdown = self.generate_navigation_markdown(nav_data)
        md_path = output_dir / "NAVIGATION.md"
        with open(md_path, 'w') as f:
            f.write(markdown)
        
        logger.info(f"Saved navigation to {md_path} and {json_path}")
        return str(md_path), str(json_path)


def main():
    """Main function to build navigation for a repository."""
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description="Build navigation metadata from repository analysis")
    parser.add_argument("repo_name", help="Repository name in database")
    parser.add_argument("--output-dir", help="Output directory (defaults to analyzed_repos/repo_name)")
    
    args = parser.parse_args()
    
    # Create builder
    builder = NavigationBuilder(args.repo_name)
    
    # Extract from database
    if not builder.extract_from_database():
        logger.error("Failed to extract analysis from database")
        return 1
    
    # Save outputs
    output_dir = Path(args.output_dir) if args.output_dir else None
    md_path, json_path = builder.save_outputs(output_dir)
    
    print(f"Navigation metadata generated:")
    print(f"  Markdown: {md_path}")
    print(f"  JSON: {json_path}")
    
    return 0


if __name__ == "__main__":
    exit(main())