#!/usr/bin/env python3
"""
Test script for single file update functionality.
This script demonstrates how to update a single file in a repository.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from mfai_db_repos.core.services.processing_service import RepositoryProcessingService
from mfai_db_repos.utils.logger import setup_logging


async def test_single_file_update():
    """Test updating a single file in a repository."""
    # Set up logging
    setup_logging(level="INFO")
    
    # Test parameters - adjust these for your test
    repo_id = 1  # Change this to an existing repository ID
    filepath = "README.md"  # File to update
    include_readme = False  # Don't include README in its own analysis
    
    print(f"\n=== Testing Single File Update ===")
    print(f"Repository ID: {repo_id}")
    print(f"File path: {filepath}")
    print(f"Include README: {include_readme}")
    print("=" * 35)
    
    # Create service
    service = RepositoryProcessingService()
    
    try:
        # Update the file
        print(f"\nUpdating file '{filepath}'...")
        success = await service.update_single_file(
            repo_id=repo_id,
            filepath=filepath,
            include_readme=include_readme,
        )
        
        if success:
            print(f"✅ Successfully updated file: {filepath}")
        else:
            print(f"❌ Failed to update file: {filepath}")
            print("Check the logs above for error details.")
            
    except Exception as e:
        print(f"❌ Error during update: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("Starting single file update test...")
    asyncio.run(test_single_file_update())
    print("\nTest completed!")