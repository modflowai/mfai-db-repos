#!/usr/bin/env python3
"""
Test script to verify the structured analysis and embedding generation pipeline.
This script:
1. Fetches a small sample of repository files
2. Generates analysis and embeddings using Gemini and OpenAI
3. Verifies the results were correctly stored in the database

The script uses API keys from the gitcontext-config.json file in the project root.
"""
import asyncio
import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gitcontext.lib.database.connection import get_session, session_context
from gitcontext.lib.database.repository import RepositoryRepository
from gitcontext.lib.database.repository_file import RepositoryFileRepository
from gitcontext.lib.database.models import RepositoryFile
from gitcontext.lib.embeddings.manager import ProviderType, EmbeddingManager  
from gitcontext.lib.embeddings.openai import OpenAIEmbeddingConfig
from gitcontext.lib.embeddings.google_genai import GoogleGenAIEmbeddingConfig
from gitcontext.utils.config import Config, config
from gitcontext.utils.logger import get_logger, setup_logging

# Set up logging
logger = get_logger(__name__)
setup_logging(level="INFO")

# Load config from file
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "gitcontext-config.json")
config.load_from_file(CONFIG_FILE)
logger.info(f"Loaded configuration from {CONFIG_FILE}")

# Default repository ID (flopy)
DEFAULT_REPO_ID = 1  # Change this to match your repository ID
SAMPLE_SIZE = 5  # Number of files to test

async def get_sample_files(repo_id: int, session, sample_size: int = SAMPLE_SIZE) -> List[RepositoryFile]:
    """
    Get a sample of files from the repository.
    
    Args:
        repo_id: Repository ID
        session: Database session
        sample_size: Number of files to sample
        
    Returns:
        List of RepositoryFile objects
    """
    file_repo = RepositoryFileRepository(session)
    files = await file_repo.get_by_repository_id(repo_id, sample_size)
    return files

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
        max_parallel_requests=config.config.embedding.parallel_workers,
        batch_size=config.config.embedding.batch_size,
        rate_limit_per_minute=100
    )
    
    return manager

async def generate_analysis_and_embedding(
    file: RepositoryFile,
    embedding_manager: EmbeddingManager,
    session
) -> bool:
    """
    Generate structured analysis and embedding for a single file.
    
    Args:
        file: RepositoryFile to process
        embedding_manager: EmbeddingManager instance
        session: Database session
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Skip empty files
        if not file.content or file.content.strip() == "":
            logger.info(f"Skipping empty file: {file.filepath}")
            return False
            
        # Step 1: Generate structured analysis using Google Gemini
        analysis = await embedding_manager.analyze_file_content(file.content)
        logger.info(f"Generated analysis for {file.filepath}")
        
        # Step 2: Create an embedding string from the analysis
        # Format the analysis into a structured text for embedding
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
            for i, snippet in enumerate(analysis.get('code_snippets', [])):
                snippet_text = f"Snippet {i+1} ({snippet.get('language', 'unknown')}): {snippet.get('purpose', '')}\n{snippet.get('summary', '')}"
                snippet_texts.append(snippet_text)
            
            # Join with explicit newlines instead of escaped character
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
        
        # Step 3: Generate embedding from the analysis text
        embedding_vector = await embedding_manager.embed_text(embedding_text)
        logger.info(f"Generated embedding from analysis for {file.filepath}")
        
        # Step 4: Store the analysis and embedding in the database
        # Convert embedding to list if it's a numpy array
        embedding_list = embedding_vector.vector.tolist() if hasattr(embedding_vector.vector, 'tolist') else list(embedding_vector.vector)
        
        # Update the file record
        file_repo = RepositoryFileRepository(session)
        
        # Store the analysis in the metadata JSON field
        metadata = file.repo_metadata or {}
        metadata["analysis"] = analysis
        
        # Update the file with both analysis and embedding
        file.embedding = str(embedding_list)
        file.embedding_string = embedding_text
        file.repo_metadata = metadata
        
        await file_repo.update(file)
        logger.info(f"Updated file record with analysis and embedding: {file.filepath}")
        
        return True
    except Exception as e:
        logger.error(f"Error processing file {file.filepath}: {str(e)}")
        return False

async def test_sample_files(repo_id: int):
    """
    Test the embedding generation pipeline with a sample of files.
    
    Args:
        repo_id: Repository ID
    """
    # Create embedding manager
    embedding_manager = await create_embedding_manager()
    
    async with session_context() as session:
        # Get sample files
        files = await get_sample_files(repo_id, session)
        
        if not files:
            print(f"No files found for repository ID {repo_id}")
            return
        
        print(f"Testing with {len(files)} sample files from repository ID {repo_id}")
        
        # Process each file
        for i, file in enumerate(files):
            print(f"\nProcessing sample file {i+1}/{len(files)}: {file.filepath}")
            
            # Generate analysis and embedding
            success = await generate_analysis_and_embedding(file, embedding_manager, session)
            
            if success:
                print(f"✅ Successfully generated analysis and embedding")
                
                # Fetch updated file from database to verify
                file_repo = RepositoryFileRepository(session)
                updated_file = await file_repo.get_by_id(file.id)
                
                # Verify analysis
                if updated_file.repo_metadata and "analysis" in updated_file.repo_metadata:
                    analysis = updated_file.repo_metadata["analysis"]
                    print("\nStructured Analysis:")
                    print(f"Title: {analysis.get('title', 'N/A')}")
                    print(f"Summary: {analysis.get('summary', 'N/A')[:100]}...")
                    print(f"Key Concepts: {', '.join(analysis.get('key_concepts', []))[:100]}...")
                    print(f"Keywords: {', '.join(analysis.get('keywords', []))[:100]}...")
                else:
                    print("❌ Analysis not found in metadata")
                
                # Verify embedding
                if updated_file.embedding and updated_file.embedding_string:
                    # Get length of embedding
                    embedding_len = len(eval(updated_file.embedding))
                    print(f"\nEmbedding details:")
                    print(f"Embedding dimensions: {embedding_len}")
                    print(f"Embedding string: {updated_file.embedding_string[:100]}...")
                else:
                    print("❌ Embedding or embedding string not found")
            else:
                print(f"❌ Failed to generate analysis and embedding")

async def main():
    """Run the main test procedure."""
    try:
        # Parse command line arguments
        import argparse
        parser = argparse.ArgumentParser(description='Test embedding generation with sample files')
        parser.add_argument('--repo-id', type=int, default=DEFAULT_REPO_ID,
                            help='Repository ID (default: flopy repository)')
        parser.add_argument('--sample-size', type=int, default=SAMPLE_SIZE,
                            help='Number of files to sample')
        args = parser.parse_args()
        
        # Run the test
        await test_sample_files(args.repo_id)
        
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