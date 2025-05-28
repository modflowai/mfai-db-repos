"""
Update repository metadata with navigation guide and clone path.
"""
import json
import os
from pathlib import Path

from sqlalchemy import create_engine, text
from mfai_db_repos.utils.env import load_env
from mfai_db_repos.utils.logger import get_logger

load_env()
logger = get_logger(__name__)


def calculate_repository_type(repo_id: int, conn) -> dict:
    """Calculate repository type based on file extensions and content."""
    
    # Get file statistics from repository files
    result = conn.execute(
        text('''
            SELECT file_path, language, content_type 
            FROM repository_files 
            WHERE repository_id = :repo_id
        '''),
        {'repo_id': repo_id}
    )
    
    files = result.fetchall()
    if not files:
        return {'repository_type': 'unknown', 'file_statistics': {}}
    
    # File extension mappings
    code_extensions = {'.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.cs', '.php', '.rb', '.go', '.rs', '.swift', '.kt', '.scala', '.r', '.m', '.f90', '.f', '.for', '.jl'}
    doc_extensions = {'.md', '.rst', '.txt', '.doc', '.docx', '.pdf', '.html', '.tex', '.adoc'}
    config_extensions = {'.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf', '.xml'}
    
    file_counts = {'code': 0, 'documentation': 0, 'config': 0, 'other': 0}
    language_counts = {}
    content_type_counts = {}
    
    for file in files:
        file_path = file.file_path
        language = file.language or 'unknown'
        content_type = file.content_type or 'unknown'
        
        # Count by file extension
        ext = Path(file_path).suffix.lower()
        if ext in code_extensions:
            file_counts['code'] += 1
        elif ext in doc_extensions:
            file_counts['documentation'] += 1
        elif ext in config_extensions:
            file_counts['config'] += 1
        else:
            file_counts['other'] += 1
        
        # Count by detected language
        language_counts[language] = language_counts.get(language, 0) + 1
        
        # Count by content type
        content_type_counts[content_type] = content_type_counts.get(content_type, 0) + 1
    
    total_files = sum(file_counts.values())
    code_ratio = file_counts['code'] / total_files if total_files > 0 else 0
    doc_ratio = file_counts['documentation'] / total_files if total_files > 0 else 0
    
    # Determine repository type
    if code_ratio >= 0.6:
        repo_type = 'code'
    elif doc_ratio >= 0.6:
        repo_type = 'documentation'
    elif code_ratio >= 0.3 and doc_ratio >= 0.3:
        repo_type = 'hybrid'
    else:
        repo_type = 'mixed'
    
    file_stats = {
        'total_files': total_files,
        'file_type_counts': file_counts,
        'language_distribution': dict(sorted(language_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
        'content_type_distribution': dict(sorted(content_type_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
        'code_ratio': round(code_ratio, 3),
        'documentation_ratio': round(doc_ratio, 3)
    }
    
    return {
        'repository_type': repo_type,
        'file_statistics': file_stats
    }


def update_repository_metadata(repo_name: str, navigation_file: str = None):
    """Update repository with clone path, navigation metadata, and repository type."""
    
    database_url = os.environ.get('DATABASE_URL')
    engine = create_engine(database_url)
    
    with engine.connect() as conn:
        # Get repository
        result = conn.execute(text('SELECT id, name FROM repositories WHERE name = :name'), {'name': repo_name})
        repo = result.fetchone()
        
        if not repo:
            logger.error(f"Repository {repo_name} not found")
            return False
        
        repo_id = repo.id
        
        # Prepare update data
        clone_path = f"analyzed_repos/{repo_name}"
        metadata = {}
        
        # Calculate repository type and file statistics
        repo_analysis = calculate_repository_type(repo_id, conn)
        metadata.update(repo_analysis)
        
        # Read navigation guide if provided
        if navigation_file and Path(navigation_file).exists():
            with open(navigation_file, 'r', encoding='utf-8') as f:
                navigation_content = f.read()
            
            metadata['navigation_guide'] = navigation_content
            metadata['navigation_generated_at'] = '2025-05-28T06:00:00Z'
            metadata['navigation_type'] = 'gemini_generated'
            logger.info(f"Read navigation guide from {navigation_file}")
        
        # Update repository with repository_type field and metadata
        repo_type = metadata.get('repository_type', 'unknown')
        conn.execute(
            text('''
                UPDATE repositories 
                SET clone_path = :clone_path,
                    metadata = :metadata,
                    repository_type = :repository_type,
                    updated_at = NOW()
                WHERE id = :repo_id
            '''),
            {
                'clone_path': clone_path,
                'metadata': json.dumps(metadata),
                'repository_type': repo_type,
                'repo_id': repo_id
            }
        )
        conn.commit()
        
        logger.info(f"Updated repository {repo_name} (ID: {repo_id})")
        logger.info(f"  Clone path: {clone_path}")
        logger.info(f"  Repository type: {repo_type}")
        logger.info(f"  Metadata keys: {list(metadata.keys())}")
        if 'file_statistics' in metadata:
            stats = metadata['file_statistics']
            logger.info(f"  File statistics: {stats['total_files']} files, {stats['code_ratio']:.1%} code, {stats['documentation_ratio']:.1%} docs")
        
        return True


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Update repository metadata")
    parser.add_argument("repo_name", help="Repository name")
    parser.add_argument("--navigation-file", help="Path to navigation guide file")
    
    args = parser.parse_args()
    
    success = update_repository_metadata(args.repo_name, args.navigation_file)
    
    if success:
        print(f"Successfully updated metadata for {args.repo_name}")
    else:
        print(f"Failed to update metadata for {args.repo_name}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())