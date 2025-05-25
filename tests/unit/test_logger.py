"""
Tests for the logger module.
"""
import logging
import tempfile
from pathlib import Path

import pytest

from mfai_db_repos.utils.config import config
from mfai_db_repos.utils.logger import get_logger, logger_manager


def test_get_logger():
    """Test retrieving a logger by name."""
    logger = get_logger("test_logger")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_logger"
    
    # Ensure the same logger is returned for the same name
    logger2 = get_logger("test_logger")
    assert logger is logger2


def test_log_level():
    """Test setting the log level."""
    logger = get_logger("test_log_level")
    
    # Test setting log level by string
    logger_manager.set_log_level("DEBUG")
    assert logger.level == logging.DEBUG
    
    # Test setting log level by integer
    logger_manager.set_log_level(logging.INFO)
    assert logger.level == logging.INFO
    
    # Verify config is updated
    assert config.config.log_level == "INFO"


def test_file_logging():
    """Test logging to a file."""
    # Create a temporary log file
    with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as temp_file:
        log_path = Path(temp_file.name)
    
    try:
        # Configure logging to file
        original_log_file = config.config.log_file
        config.config.log_file = log_path
        
        # Reinitialize logger to pick up the new config
        logger_manager._setup_default_logger()
        
        # Get a test logger and log a message
        logger = get_logger("test_file_logger")
        test_message = "Test file logging message"
        logger.info(test_message)
        
        # Verify message was written to the log file
        with open(log_path, "r") as f:
            log_content = f.read()
            assert test_message in log_content
            
    finally:
        # Restore original config
        config.config.log_file = original_log_file
        logger_manager._setup_default_logger()
        
        # Clean up temporary file
        if log_path.exists():
            log_path.unlink()