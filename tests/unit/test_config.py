"""
Tests for the configuration management module.
"""
import os
import tempfile
from pathlib import Path

import pytest

from mfai_db_repos.utils.config import Config, AppConfig


def test_default_config():
    """Test default configuration values."""
    config = Config()
    assert config.config.database.host == "localhost"
    assert config.config.database.port == 5437
    assert config.config.embedding.parallel_workers == 5


def test_env_config():
    """Test loading configuration from environment variables."""
    # Save original environment variables
    original_db_host = os.environ.get("DB_HOST")
    original_db_port = os.environ.get("DB_PORT")
    
    try:
        # Set test environment variables
        os.environ["DB_HOST"] = "testhost"
        os.environ["DB_PORT"] = "1234"
        
        # Create a new config instance to load from env
        config = Config()
        config.load_from_env()
        
        # Verify configuration was loaded from environment
        assert config.config.database.host == "testhost"
        assert config.config.database.port == 1234
    finally:
        # Restore original environment variables
        if original_db_host is not None:
            os.environ["DB_HOST"] = original_db_host
        else:
            os.environ.pop("DB_HOST", None)
            
        if original_db_port is not None:
            os.environ["DB_PORT"] = original_db_port
        else:
            os.environ.pop("DB_PORT", None)


def test_file_config():
    """Test loading and saving configuration from/to a file."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp_file:
        temp_path = Path(temp_file.name)
    
    try:
        # Create a config with custom values
        config = Config()
        config.update(
            **{
                "database.host": "filehost",
                "database.port": 9999,
                "embedding.parallel_workers": 10,
            }
        )
        
        # Save config to file
        config.save_to_file(temp_path)
        
        # Create a new config instance
        new_config = Config()
        # Load config from file
        new_config.load_from_file(temp_path)
        
        # Verify configuration was loaded correctly
        assert new_config.config.database.host == "filehost"
        assert new_config.config.database.port == 9999
        assert new_config.config.embedding.parallel_workers == 10
    finally:
        # Clean up temporary file
        if temp_path.exists():
            temp_path.unlink()