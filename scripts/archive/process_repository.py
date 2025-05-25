#!/usr/bin/env python3
"""
Script to implement the complete repository processing pipeline.
This script:
1. Clones/updates the repository if needed
2. Extracts files from the repository
3. Processes files in consistent batches of 5, with each batch in a single transaction
4. For each file, performs the complete processing workflow:
   - Store file content and basic metadata
   - Capture and store git metadata including commit hash
   - Generate and store tsvector from content
   - Generate complete Gemini analysis and store full JSON
   - Extract and store file_type, technical_level, and tags
   - Create embedding string from analysis
   - Generate and store embedding vector

Usage:
    python scripts/process_repository.py --repo-url https://github.com/modflowpy/flopy.git --batch-size 5 [--limit 5]
    python scripts/process_repository.py --repo-id 1 --batch-size 5 [--limit 5]
"""
import asyncio
import os
import sys
import json
import re
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gitcontext.lib.database.connection import get_session, session_context
from gitcontext.lib.database.repository import RepositoryRepository
from gitcontext.lib.database.repository_file import RepositoryFileRepository
from gitcontext.lib.database.models import Repository, RepositoryFile
from gitcontext.lib.embeddings.manager import EmbeddingManager, ProviderType
from gitcontext.lib.embeddings.google_genai import GoogleGenAIEmbeddingConfig
from gitcontext.lib.embeddings.openai import OpenAIEmbeddingConfig
from gitcontext.lib.git.repository import GitRepository, RepoStatus
from gitcontext.lib.file_processor.extractor import FileExtractor
from gitcontext.utils.config import Config, config
from gitcontext.utils.logger import get_logger, setup_logging

# Set up logging
logger = get_logger(__name__)
setup_logging(level="INFO")

# Load config from file
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "gitcontext-config.json")
config.load_from_file(CONFIG_FILE)

# Default repository URL (flopy)
DEFAULT_REPO_URL = "https://github.com/modflowpy/flopy.git"

async def create_embedding_manager() -> EmbeddingManager:
    """
    Create and configure the embedding manager with both
    OpenAI (for embeddings) and Google GenAI (for analysis).
    
    Returns:
        Configured EmbeddingManager instance
    """
    # Load API keys from config file
    openai_api_key = config.config.embedding.openai_api_key
    google_api_key = config.config.embedding.google_genai_api_key
    
    if not openai_api_key:
        logger.warning("OpenAI API key not set in config, embeddings will fail")
    
    if not google_api_key:
        logger.warning("Google GenAI API key not set in config, structured analysis will fail")
    
    # Create OpenAI config
    openai_config = OpenAIEmbeddingConfig(
        api_key=openai_api_key,
        model=config.config.embedding.openai_model,
        batch_size=config.config.embedding.batch_size,
        max_parallel_requests=config.config.embedding.parallel_workers
    )
    
    # Create Google GenAI config
    google_config = GoogleGenAIEmbeddingConfig(
        api_key=google_api_key,
        model=config.config.embedding.gemini_model,
        batch_size=1,  # Process one file at a time for analysis
        max_parallel_requests=config.config.embedding.parallel_workers
    )
    
    # Create manager with both providers
    manager = EmbeddingManager(
        primary_provider=ProviderType.OPENAI,
        secondary_provider=ProviderType.GOOGLE_GENAI,
        primary_config=openai_config,
        secondary_config=google_config,
        max_parallel_requests=5,
        batch_size=20,
        rate_limit_per_minute=100
    )
    
    return manager

def generate_tsvector(content: str) -> str:
    """
    Generate a tsvector representation of content for PostgreSQL full-text search.
    This is a simple implementation that normalizes text for better search results.
    
    Args:
        content: Text content to convert to tsvector
        
    Returns:
        Normalized string for tsvector conversion in PostgreSQL
    """
    if not content:
        return ""
        
    # Remove code comments
    content = re.sub(r'#.*$', ' ', content, flags=re.MULTILINE)  # Python comments
    content = re.sub(r'//.*$', ' ', content, flags=re.MULTILINE)  # JavaScript/C++ comments
    content = re.sub(r'/\*.*?\*/', ' ', content, flags=re.DOTALL)  # Multi-line comments
    
    # Normalize whitespace and convert to lowercase
    content = re.sub(r'\s+', ' ', content)
    content = content.lower().strip()
    
    # Remove common syntax characters
    content = re.sub(r'[^\w\s]', ' ', content)
    
    # Replace consecutive spaces with a single space
    content = re.sub(r'\s+', ' ', content)
    
    return content

def extract_tags_from_analysis(analysis: Dict[str, Any]) -> List[str]:
    """
    Extract tags from the analysis output.
    
    Args:
        analysis: Analysis dictionary from Gemini
        
    Returns:
        List of tags
    """
    tags = set()
    
    # Add keywords as tags
    if 'keywords' in analysis and analysis['keywords']:
        tags.update(analysis['keywords'])
    
    # Add key concepts as tags
    if 'key_concepts' in analysis and analysis['key_concepts']:
        tags.update(analysis['key_concepts'])
        
    # Add related topics
    if 'related_topics' in analysis and analysis['related_topics']:
        tags.update(analysis['related_topics'])
        
    # Return as sorted list of strings
    return sorted(tags)

async def get_repository_files(repo_id: int, session, limit: Optional[int] = None) -> List[RepositoryFile]:
    """
    Get files for a repository.
    
    Args:
        repo_id: Repository ID
        session: Database session
        limit: Optional limit on number of files to process
        
    Returns:
        List of RepositoryFile objects
    """
    file_repo = RepositoryFileRepository(session)
    files = await file_repo.get_by_repository_id(repo_id, limit)
    return files

async def process_file_batch(
    files: List[RepositoryFile],
    embedding_manager: EmbeddingManager,
    git_repo: GitRepository,
    batch_index: int,
    total_batches: int
) -> Tuple[int, int]:
    """
    Process a batch of files to populate all database fields.
    
    Args:
        files: List of RepositoryFile objects to process
        embedding_manager: EmbeddingManager instance
        git_repo: GitRepository instance for getting commit information
        batch_index: Index of the current batch (for logging)
        total_batches: Total number of batches (for logging)
        
    Returns:
        Tuple of (success_count, failure_count)
    """
    success_count = 0
    failure_count = 0
    
    # Process all files in this batch within a single transaction
    async with session_context() as session:
        file_repo = RepositoryFileRepository(session)
        
        try:
            for i, file in enumerate(files):
                file_index = i + 1
                logger.info(f"Batch {batch_index+1}/{total_batches} - Processing file {file_index}/{len(files)}: {file.filepath}")
                
                try:
                    # Skip empty files
                    if not file.content or file.content.strip() == "":
                        logger.info(f"Skipping empty file: {file.filepath}")
                        failure_count += 1
                        continue
                    
                    # 1. Get git metadata including commit hash
                    try:
                        commit_hash = git_repo.get_file_commit_hash(file.filepath)
                        file.repo_commit_hash = commit_hash
                        logger.debug(f"Got commit hash {commit_hash} for {file.filepath}")
                    except Exception as e:
                        logger.warning(f"Failed to get commit hash for {file.filepath}: {e}")
                    
                    # 2. Generate tsvector for PostgreSQL full-text search
                    file.content_tsvector = generate_tsvector(file.content)
                    logger.debug(f"Generated tsvector for {file.filepath}")
                    
                    # 3. Generate structured analysis using Google Gemini
                    analysis = await embedding_manager.analyze_file_content(file.content)
                    logger.debug(f"Generated analysis for {file.filepath}")
                    
                    # 4. Store the complete analysis JSON
                    file.analysis = analysis
                    
                    # 5. Extract and store file_type and technical_level
                    file.file_type = analysis.get('document_type', 'Unknown')
                    file.technical_level = analysis.get('technical_level', 'Unknown')
                    
                    # 6. Extract and store tags as a list of strings
                    file.tags = extract_tags_from_analysis(analysis)
                    
                    # 7. Create embedding string from analysis
                    embedding_text = f"""
                    Title: {analysis.get('title', 'No title')}
                    
                    Summary: {analysis.get('summary', 'No summary')}
                    
                    Key Concepts: {', '.join(analysis.get('key_concepts', []))}
                    
                    Potential Questions: {' '.join(analysis.get('potential_questions', []))}
                    
                    Keywords: {', '.join(analysis.get('keywords', []))}
                    
                    Document Type: {analysis.get('document_type', 'Unknown')}
                    
                    Technical Level: {analysis.get('technical_level', 'Unknown')}
                    
                    Related Topics: {', '.join(analysis.get('related_topics', []))}
                    
                    Prerequisites: {', '.join(analysis.get('prerequisites', []))}
                    """
                    
                    # Add code snippets if available
                    if analysis.get('code_snippets') and len(analysis.get('code_snippets', [])) > 0:
                        snippet_texts = []
                        for j, snippet in enumerate(analysis.get('code_snippets', [])):
                            snippet_text = f"Snippet {j+1} ({snippet.get('language', 'unknown')}): {snippet.get('purpose', '')}\n{snippet.get('summary', '')}"
                            snippet_texts.append(snippet_text)
                        
                        # Join with explicit newlines
                        joined_snippets = "\n".join(snippet_texts)
                        embedding_text += f"""
                    Code Snippets:
                    {joined_snippets}
                    """
                        
                        if analysis.get('code_snippets_overview'):
                            embedding_text += f"""
                    Code Snippets Overview: {analysis.get('code_snippets_overview')}
                    """
                    
                    # Add component properties if available
                    if analysis.get('component_properties'):
                        cp = analysis.get('component_properties', {})
                        embedding_text += f"""
                    Component Type: {cp.get('component_type', 'Unknown')}
                    API Elements: {', '.join(cp.get('api_elements', []))}
                    Required Parameters: {', '.join(cp.get('required_parameters', []))}
                    Optional Parameters: {', '.join(cp.get('optional_parameters', []))}
                    Related Components: {', '.join(cp.get('related_components', []))}
                    """
                    
                    # 8. Generate embedding from the analysis text
                    embedding_vector = await embedding_manager.embed_text(embedding_text)
                    logger.debug(f"Generated embedding vector for {file.filepath}")
                    
                    # Convert embedding to list if it's a numpy array
                    embedding_list = embedding_vector.vector.tolist() if hasattr(embedding_vector.vector, 'tolist') else list(embedding_vector.vector)
                    
                    # Update the file with embedding string and vector
                    file.embedding = str(embedding_list)
                    file.embedding_string = embedding_text
                    
                    # Update the file record
                    await file_repo.update(file)
                    logger.info(f"Successfully processed {file.filepath}")
                    success_count += 1
                    
                except Exception as e:
                    logger.error(f"Error processing file {file.filepath}: {str(e)}")
                    failure_count += 1
            
            # Commit all changes at once for this batch
            await session.commit()
            logger.info(f"Batch {batch_index+1}/{total_batches} completed: {success_count} succeeded, {failure_count} failed")
            
        except Exception as e:
            logger.error(f"Batch transaction failed: {str(e)}")
            await session.rollback()
            # Consider all files in the batch as failed
            failure_count = len(files)
    
    return (success_count, failure_count)

async def process_repository(
    repo_id: int,
    limit: Optional[int] = None,
    batch_size: int = 5
) -> Tuple[int, int]:
    """
    Process all files in a repository to populate all database fields.
    
    Args:
        repo_id: ID of repository to process
        limit: Optional limit on number of files to process
        batch_size: Number of files to process in each batch
        
    Returns:
        Tuple of (success_count, failure_count)
    """
    total_success = 0
    total_failure = 0
    
    # Check if repository exists and get repository information
    async with session_context() as session:
        repo_repo = RepositoryRepository(session)
        repository = await repo_repo.get_by_id(repo_id)
        
        if not repository:
            logger.error(f"Repository with ID {repo_id} not found")
            return (0, 0)
            
        logger.info(f"Processing repository: {repository.name} ({repository.url})")
    
    # Initialize Git repository
    git_repo = GitRepository(repository.url, repository.clone_path, repository.default_branch)
    
    if not git_repo.is_cloned():
        logger.error(f"Repository is not cloned. Please clone it first using the CLI.")
        return (0, 0)
    
    # Create embedding manager
    embedding_manager = await create_embedding_manager()
    
    # Get all files for the repository
    async with session_context() as session:
        files = await get_repository_files(repo_id, session, limit)
        
        if not files:
            logger.info(f"No files found for repository ID {repo_id}")
            return (0, 0)
        
        total_files = len(files)
        logger.info(f"Found {total_files} files to process")
        
        # Create batches of files
        batches = [files[i:i + batch_size] for i in range(0, total_files, batch_size)]
        total_batches = len(batches)
        logger.info(f"Split into {total_batches} batches of {batch_size} files")
        
        # Process each batch sequentially to ensure orderly processing
        for i, batch in enumerate(batches):
            batch_success, batch_failure = await process_file_batch(
                batch, 
                embedding_manager, 
                git_repo, 
                i, 
                total_batches
            )
            
            total_success += batch_success
            total_failure += batch_failure
            
            logger.info(f"Completed batch {i+1}/{total_batches}: {batch_success} succeeded, {batch_failure} failed")
            logger.info(f"Progress: {total_success + total_failure}/{total_files} files processed ({total_success} succeeded, {total_failure} failed)")
            
            # Add a small delay between batches to avoid overwhelming APIs
            await asyncio.sleep(1)
    
    logger.info(f"Repository processing completed: {total_success} succeeded, {total_failure} failed")
    return (total_success, total_failure)

async def main():
    """Run the main procedure."""
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(description='Process repository files and populate all database fields')
        parser.add_argument('--repo-id', type=int, default=DEFAULT_REPO_ID,
                            help='Repository ID (default: flopy repository)')
        parser.add_argument('--limit', type=int, default=None,
                            help='Limit number of files to process')
        parser.add_argument('--batch-size', type=int, default=5,
                            help='Number of files to process in each batch')
        args = parser.parse_args()
        
        # Run the process
        success, failure = await process_repository(
            repo_id=args.repo_id,
            limit=args.limit, 
            batch_size=args.batch_size
        )
        
        print(f"\nProcessing complete!")
        print(f"Successfully processed: {success} files")
        print(f"Failed to process: {failure} files")
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        import traceback
        print(f"\nError: {str(e)}")
        print(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())