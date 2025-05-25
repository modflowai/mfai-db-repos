"""
Pytest configuration file.
"""
import os
import sys
from pathlib import Path

# Add the project root directory to the Python path
# to make the 'mfai_db_repos' package importable during tests
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Fixtures shared across all tests go here
import pytest


@pytest.fixture
def test_data_dir():
    """Return the path to the test data directory."""
    return os.path.join(os.path.dirname(__file__), "data")