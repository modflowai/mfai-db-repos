#!/usr/bin/env python3
"""Test with a simple code snippet that has problematic patterns."""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from mfai_db_repos.lib.embeddings.google_genai import GoogleGenAIEmbeddingProvider, GoogleGenAIEmbeddingConfig
from mfai_db_repos.utils.logger import get_logger

logger = get_logger(__name__)


# Simple test content with the exact problematic patterns from mfreadnam.py
TEST_CONTENT = '''
def parse_file(filepath):
    """Parse a file with quote handling."""
    # This has the problematic patterns from the failing file
    if '"' in filepath:
        filepath = filepath.replace('"', "")
    if "'" in filepath:
        filepath = filepath.replace("'", "")
    
    # Check for backslashes
    if "\\" in filepath:
        print("Found backslash")
    
    # Check comment lines
    if line[0] != "#":
        process_line(line)
'''


async def test_simple():
    """Test with simple content."""
    
    # Initialize the provider
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.error("GOOGLE_API_KEY not found in environment")
        return False
        
    config = GoogleGenAIEmbeddingConfig(api_key=api_key)
    provider = GoogleGenAIEmbeddingProvider(config)
    
    logger.info(f"Testing with simple content, length: {len(TEST_CONTENT)} characters")
    
    # Test encoding
    encoded = provider._encode_content_base64(TEST_CONTENT)
    logger.info(f"Encoded content length: {len(encoded)} characters")
    
    # Try to generate analysis
    try:
        result = await provider.generate_structured_analysis(TEST_CONTENT)
        logger.info("✓ Simple analysis completed successfully!")
        logger.info(f"  Title: {result.title}")
        logger.info(f"  Document type: {result.document_type}")
        return True
    except Exception as e:
        logger.error(f"✗ Simple analysis failed: {type(e).__name__}: {str(e)}")
        return False


async def main():
    """Run the test."""
    success = await test_simple()
    
    if success:
        logger.info("\n✓ Simple test passed! Now testing with the full file...")
        
        # If simple test passes, try the full file
        test_file = Path(__file__).parent / "example_files_test_analysis" / "mfreadnam.py"
        if test_file.exists():
            content = test_file.read_text()
            
            config = GoogleGenAIEmbeddingConfig(api_key=os.getenv("GOOGLE_API_KEY"))
            provider = GoogleGenAIEmbeddingProvider(config)
            
            try:
                result = await provider.generate_structured_analysis(content)
                logger.info("✓ Full file analysis completed successfully!")
                return True
            except Exception as e:
                logger.error(f"✗ Full file analysis failed: {type(e).__name__}: {str(e)}")
                return False
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)