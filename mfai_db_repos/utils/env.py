"""
Environment variable utilities for GitContext.

This module provides functions for loading and accessing environment variables
from a .env file.
"""
import os
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv

from mfai_db_repos.utils.logger import get_logger

logger = get_logger(__name__)

# Default values
DEFAULT_ENV = {
    # API Keys
    "OPENAI_API_KEY": "",  # Must be provided by user
    "GOOGLE_API_KEY": "",  # Must be provided by user
    
    # Database
    "DB_HOST": "localhost",
    "DB_PORT": "5437",
    "DB_NAME": "mfai_db_repos",
    "DB_USER": "postgres",
    "DB_PASSWORD": "postgres",
    
    # Processing
    "BATCH_SIZE": "5",
    "PARALLEL_WORKERS": "5",
    "MAX_FILE_SIZE_MB": "10",
}

# Load environment variables
def load_env(env_file: Optional[str] = None) -> Dict[str, str]:
    """
    Load environment variables from .env file.
    
    Args:
        env_file: Path to .env file (default: .env in project root)
        
    Returns:
        Dictionary of environment variables with default values for missing ones
    """
    # Find project root (where .env file should be)
    project_root = find_project_root()
    
    # Use specified env_file or default to .env in project root
    env_path = env_file if env_file else os.path.join(project_root, ".env")
    
    # Load .env file if it exists
    if os.path.exists(env_path):
        logger.debug(f"Loading environment variables from {env_path}")
        load_dotenv(env_path)
    else:
        logger.warning(f".env file not found at {env_path}, using default values")
    
    # Get environment variables with defaults
    env_vars = {}
    for key, default in DEFAULT_ENV.items():
        env_vars[key] = os.environ.get(key, default)
    
    return env_vars

def find_project_root() -> str:
    """
    Find the project root directory.
    
    Returns:
        Path to the project root directory
    """
    # Start from the current file
    current_path = Path(__file__).resolve()
    
    # Go up until we find the project root (where .env or pyproject.toml would be)
    for path in [current_path, *current_path.parents]:
        if (path / ".env").exists() or (path / "pyproject.toml").exists():
            return str(path)
    
    # If not found, use the directory containing this file's parent directory
    return str(current_path.parent.parent.parent)

# Global environment variables (loaded once)
env = load_env()

def get_env(key: str, default: Any = None) -> Any:
    """
    Get an environment variable.
    
    Args:
        key: Environment variable key
        default: Default value if not found
        
    Returns:
        Environment variable value
    """
    return env.get(key, default)

def get_int_env(key: str, default: int = 0) -> int:
    """
    Get an environment variable as an integer.
    
    Args:
        key: Environment variable key
        default: Default value if not found or not an integer
        
    Returns:
        Environment variable value as an integer
    """
    try:
        return int(env.get(key, default))
    except (ValueError, TypeError):
        return default

def get_float_env(key: str, default: float = 0.0) -> float:
    """
    Get an environment variable as a float.
    
    Args:
        key: Environment variable key
        default: Default value if not found or not a float
        
    Returns:
        Environment variable value as a float
    """
    try:
        return float(env.get(key, default))
    except (ValueError, TypeError):
        return default

def get_bool_env(key: str, default: bool = False) -> bool:
    """
    Get an environment variable as a boolean.
    
    Args:
        key: Environment variable key
        default: Default value if not found
        
    Returns:
        Environment variable value as a boolean
    """
    value = env.get(key, str(default)).lower()
    return value in ("1", "true", "yes", "y", "t")