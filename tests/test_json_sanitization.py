#!/usr/bin/env python3
"""Test the JSON sanitization with problematic files."""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from mfai_db_repos.lib.embeddings.google_genai import GoogleGenAIEmbeddingProvider, GoogleGenAIEmbeddingConfig
from mfai_db_repos.utils.logger import get_logger
import logging

# Set logging level to DEBUG to see more details
logging.basicConfig(level=logging.DEBUG)
logger = get_logger(__name__)
logger.setLevel(logging.DEBUG)


async def test_sanitization():
    """Test the sanitization function with the problematic file."""
    
    # Read the problematic file
    test_file = Path(__file__).parent / "example_files_test_analysis" / "mfreadnam.py"
    if not test_file.exists():
        logger.error(f"Test file not found: {test_file}")
        return False
        
    content = test_file.read_text()
    logger.info(f"Read test file: {test_file.name}, length: {len(content)} characters")
    
    # Initialize the provider
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.error("GOOGLE_API_KEY not found in environment")
        return False
        
    config = GoogleGenAIEmbeddingConfig(api_key=api_key)
    provider = GoogleGenAIEmbeddingProvider(config)
    
    # Test base64 encoding
    logger.info("Testing content encoding...")
    encoded = provider._encode_content_base64(content)
    logger.info(f"Original content length: {len(content)} characters")
    logger.info(f"Encoded content length: {len(encoded)} characters")
    
    # Verify encoding/decoding works
    import base64
    decoded = base64.b64decode(encoded).decode('utf-8')
    if decoded == content:
        logger.info("✓ Base64 encoding/decoding verified successfully")
    else:
        logger.error("✗ Base64 encoding/decoding mismatch!")
        return False
    
    # Try to generate analysis
    logger.info("\nTesting structured analysis generation...")
    try:
        result = await provider.generate_structured_analysis(content)
        logger.info("✓ Analysis completed successfully!")
        logger.info(f"  Title: {result.title}")
        logger.info(f"  Summary length: {len(result.summary)} characters")
        logger.info(f"  Key concepts: {len(result.key_concepts)}")
        logger.info(f"  Keywords: {len(result.keywords)}")
        logger.info(f"  Document type: {result.document_type}")
        logger.info(f"  Technical level: {result.technical_level}")
        logger.info(f"  Potential questions: {len(result.potential_questions)}")
        
        # Validate all required fields are present
        required_fields = ['title', 'summary', 'key_concepts', 'keywords', 
                          'document_type', 'technical_level', 'potential_questions']
        missing_fields = []
        for field in required_fields:
            if not getattr(result, field, None):
                missing_fields.append(field)
                
        if missing_fields:
            logger.warning(f"Missing required fields: {missing_fields}")
            return False
        else:
            logger.info("✓ All required fields present")
            return True
            
    except Exception as e:
        logger.error(f"✗ Analysis failed with error: {type(e).__name__}: {str(e)}")
        import traceback
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        return False


async def main():
    """Run the test."""
    logger.info("Starting JSON sanitization test...")
    success = await test_sanitization()
    
    if success:
        logger.info("\n✓ Test completed successfully! The sanitization appears to be working.")
    else:
        logger.error("\n✗ Test failed. The sanitization needs further adjustment.")
        
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)