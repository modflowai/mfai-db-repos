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


def update_repository_metadata(repo_name: str, navigation_file: str = None):
    """Update repository with clone path and navigation metadata."""
    
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
        
        # Read navigation guide if provided
        if navigation_file and Path(navigation_file).exists():
            with open(navigation_file, 'r', encoding='utf-8') as f:
                navigation_content = f.read()
            
            metadata['navigation_guide'] = navigation_content
            metadata['navigation_generated_at'] = '2025-05-28T06:00:00Z'
            metadata['navigation_type'] = 'gemini_generated'
            logger.info(f"Read navigation guide from {navigation_file}")
        
        # Update repository
        conn.execute(
            text('''
                UPDATE repositories 
                SET clone_path = :clone_path,
                    metadata = :metadata,
                    updated_at = NOW()
                WHERE id = :repo_id
            '''),
            {
                'clone_path': clone_path,
                'metadata': json.dumps(metadata),
                'repo_id': repo_id
            }
        )
        conn.commit()
        
        logger.info(f"Updated repository {repo_name} (ID: {repo_id})")
        logger.info(f"  Clone path: {clone_path}")
        logger.info(f"  Metadata keys: {list(metadata.keys())}")
        
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