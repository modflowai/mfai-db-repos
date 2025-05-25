"""
Logging module for the GitContext application.

This module provides a centralized logging system with configurable
handlers, formatters, and log levels.
"""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional, Union

from rich.console import Console
from rich.logging import RichHandler

from mfai_db_repos.utils.config import config


class Logger:
    """Logger manager for the GitContext application."""

    _instance: Optional["Logger"] = None
    _loggers: dict[str, logging.Logger] = {}

    def __new__(cls) -> "Logger":
        """Implement the Singleton pattern."""
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance._setup_default_logger()
        return cls._instance

    def _setup_default_logger(self) -> None:
        """Configure the default logger."""
        # Get log level from config
        log_level_str = config.config.log_level.upper()
        log_level = getattr(logging, log_level_str, logging.INFO)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        
        # Remove existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Add console handler with rich formatting
        console_handler = RichHandler(
            console=Console(stderr=True),
            show_path=False,
            enable_link_path=True,
        )
        console_formatter = logging.Formatter(
            "%(message)s",
            datefmt="[%X]",
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # Add file handler if configured
        if config.config.log_file:
            log_file = Path(config.config.log_file)
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,  # 10 MB
                backupCount=5,
            )
            file_formatter = logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)
        
        # Store the root logger
        self._loggers["root"] = root_logger

    def get_logger(self, name: str) -> logging.Logger:
        """Get a named logger.
        
        Args:
            name: The name of the logger, typically the module name.
            
        Returns:
            A configured logger instance.
        """
        if name not in self._loggers:
            logger = logging.getLogger(name)
            self._loggers[name] = logger
        return self._loggers[name]

    def set_log_level(self, level: Union[int, str]) -> None:
        """Set the log level for all loggers.
        
        Args:
            level: The log level as a string ('DEBUG', 'INFO', etc.) or as a constant
                  from the logging module (logging.DEBUG, logging.INFO, etc.).
        """
        if isinstance(level, str):
            level_str = level.upper()
            level_int = getattr(logging, level_str, logging.INFO)
        else:
            level_int = level
        
        # Update the root logger and all other loggers
        for logger in self._loggers.values():
            logger.setLevel(level_int)
        
        # Update the config
        config.config.log_level = logging.getLevelName(level_int)


# Global logger manager
logger_manager = Logger()


def get_logger(name: str) -> logging.Logger:
    """Convenience function to get a named logger.
    
    Args:
        name: The name of the logger, typically the module name.
        
    Returns:
        A configured logger instance.
    """
    return logger_manager.get_logger(name)


def setup_logging(level: Union[int, str] = "INFO") -> None:
    """Set up the logging system with the specified log level.
    
    Args:
        level: The log level as a string ('DEBUG', 'INFO', etc.) or as a constant
              from the logging module (logging.DEBUG, logging.INFO, etc.).
    """
    logger_manager.set_log_level(level)