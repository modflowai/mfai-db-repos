"""
Configuration management module for the GitContext application.

This module provides facilities for loading, validating, and accessing
application configuration from various sources (environment variables,
configuration files, and command-line arguments).
"""
import os
import json
from pathlib import Path
from typing import Any, Optional, Union

from pydantic import BaseModel, Field


class DatabaseConfig(BaseModel):
    """Database connection configuration."""

    host: str = Field(default="localhost")
    port: int = Field(default=5437)
    user: str = Field(default="postgres")
    password: str = Field(default="postgres")
    database: str = Field(default="mfai_db_repos")
    poolsize: int = Field(default=5)
    connect_timeout: int = Field(default=30)
    sslmode: str = Field(default="prefer")
    is_serverless: bool = Field(default=False)
    use_connection_pooler: bool = Field(default=False)
    pool_recycle: int = Field(default=1800)  # 30 minutes to prevent stale connections


class EmbeddingConfig(BaseModel):
    """Configuration for the embedding generation system."""

    openai_api_key: Optional[str] = Field(default=None)
    openai_model: str = Field(default="text-embedding-ada-002")
    google_genai_api_key: Optional[str] = Field(default=None)
    gemini_model: str = Field(default="gemini-2.5-flash-preview-05-20")
    embedding_dimensions: int = Field(default=1536)
    parallel_workers: int = Field(default=5)
    max_content_length: int = Field(default=60000)
    batch_size: int = Field(default=20)


class GitConfig(BaseModel):
    """Configuration for Git repository operations."""

    default_clone_path: Path = Field(default=Path.home() / ".gitcontext" / "repositories")
    default_branch: str = Field(default="main")
    depth: Optional[int] = Field(default=None)  # None means full clone
    github_token: Optional[str] = Field(default=None)  # GitHub Personal Access Token for private repos


class FileFilterConfig(BaseModel):
    """Configuration for file filtering rules."""

    include_patterns: list[str] = Field(default=[
        # Python files
        "**/*.py", 
        # Documentation
        "**/*.md", "**/*.txt", 
        # TypeScript files
        "**/*.ts", "**/*.tsx", 
        # JavaScript files
        "**/*.js", "**/*.jsx", 
        # Web files
        "**/*.html", "**/*.css", "**/*.scss", "**/*.sass",
        # Data files 
        "**/*.json", "**/*.yml", "**/*.yaml"
    ])
    exclude_patterns: list[str] = Field(
        default=[
            "**/.git/**",
            "**/node_modules/**",
            "**/__pycache__/**",
            "**/.pytest_cache/**",
            "**/venv/**",
            "**/.venv/**",
        ]
    )
    
    # Additional patterns for test files (not excluded by default)
    test_patterns: list[str] = Field(
        default=[
            "**/tests/**",
            "**/test_*.py",
            "**/*_test.py",
            "**/__tests__/**",
            "**/test/**",
        ]
    )
    max_file_size_mb: float = Field(default=10.0)  # 10MB


class AppConfig(BaseModel):
    """Main application configuration."""

    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    git: GitConfig = Field(default_factory=GitConfig)
    file_filter: FileFilterConfig = Field(default_factory=FileFilterConfig)
    log_level: str = Field(default="INFO")
    log_file: Optional[Path] = Field(default=None)


class Config:
    """Configuration manager class that loads and provides access to application settings."""

    _instance: Optional["Config"] = None
    _config: AppConfig

    def __new__(cls) -> "Config":
        """Implement the Singleton pattern."""
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._config = AppConfig()
        return cls._instance

    def load_from_env(self) -> None:
        """Load configuration from environment variables."""
        # Database configuration
        if os.environ.get("DB_HOST"):
            self._config.database.host = os.environ["DB_HOST"]
        if os.environ.get("DB_PORT"):
            self._config.database.port = int(os.environ["DB_PORT"])
        if os.environ.get("DB_USER"):
            self._config.database.user = os.environ["DB_USER"]
        if os.environ.get("DB_PASSWORD"):
            self._config.database.password = os.environ["DB_PASSWORD"]
        if os.environ.get("DB_NAME"):
            self._config.database.database = os.environ["DB_NAME"]
        if os.environ.get("DB_SSLMODE"):
            self._config.database.sslmode = os.environ["DB_SSLMODE"]
        if os.environ.get("DB_SERVERLESS"):
            self._config.database.is_serverless = os.environ["DB_SERVERLESS"].lower() in ("true", "1", "yes")
        if os.environ.get("DB_USE_POOLER"):
            self._config.database.use_connection_pooler = os.environ["DB_USE_POOLER"].lower() in ("true", "1", "yes")

        # Embedding configuration
        if os.environ.get("OPENAI_API_KEY"):
            self._config.embedding.openai_api_key = os.environ["OPENAI_API_KEY"]
        if os.environ.get("GOOGLE_API_KEY"):
            self._config.embedding.google_genai_api_key = os.environ["GOOGLE_API_KEY"]
        
        # Git configuration
        if os.environ.get("GITHUB_TOKEN"):
            self._config.git.github_token = os.environ["GITHUB_TOKEN"]
        
        # Logging configuration
        if os.environ.get("LOG_LEVEL"):
            self._config.log_level = os.environ["LOG_LEVEL"]
        if os.environ.get("LOG_FILE"):
            self._config.log_file = Path(os.environ["LOG_FILE"])

    def load_from_file(self, config_file: Union[str, Path]) -> None:
        """Load configuration from a JSON file."""
        config_path = Path(config_file)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")

        with open(config_path, "r") as f:
            config_data = json.load(f)
            
        # Use pydantic to parse and validate the config data
        app_config = AppConfig.model_validate(config_data)
        self._config = app_config

    def save_to_file(self, config_file: Union[str, Path]) -> None:
        """Save current configuration to a JSON file."""
        config_path = Path(config_file)
        
        # Create parent directories if they don't exist
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, "w") as f:
            f.write(self._config.model_dump_json(indent=2))

    @property
    def config(self) -> AppConfig:
        """Get the current configuration."""
        return self._config

    def get(self) -> AppConfig:
        """Get the current configuration (alternative to property)."""
        return self._config

    def update(self, **kwargs: Any) -> None:
        """Update configuration with provided values."""
        config_dict = self._config.model_dump()
        
        for key, value in kwargs.items():
            if "." in key:
                # Handle nested configuration like "database.host"
                parts = key.split(".")
                current = config_dict
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = value
            else:
                # Handle top-level configuration
                config_dict[key] = value
        
        # Use pydantic to validate the updated config
        self._config = AppConfig.model_validate(config_dict)


# Global configuration instance
config = Config()