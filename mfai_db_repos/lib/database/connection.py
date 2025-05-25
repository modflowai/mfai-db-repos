"""
Database connection and session management module.

This module provides functions and classes for establishing and managing
database connections, connection pools, and sessions.
"""
import logging
from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import AsyncGenerator, Optional

from sqlalchemy import URL
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from mfai_db_repos.utils.config import config
from mfai_db_repos.utils.logger import get_logger

logger = get_logger(__name__)

# Context variable to store the current session
_session_context: ContextVar[Optional[AsyncSession]] = ContextVar("_session", default=None)

# Global engine
_engine: Optional[AsyncEngine] = None


def get_connection_url(async_driver: bool = True) -> URL:
    """Create a SQLAlchemy connection URL from the configuration.
    
    Args:
        async_driver: Whether to use the async driver
        
    Returns:
        SQLAlchemy URL object
    """
    db_config = config.config.database
    driver = "postgresql+asyncpg" if async_driver else "postgresql+psycopg2"
    
    # Check if we're using Neon DB by looking at the host
    using_neon = False
    if hasattr(db_config, 'host') and db_config.host and ".neon.tech" in db_config.host:
        using_neon = True
    
    # Check for DATABASE_URL environment variable (Neon DB style)
    import os
    database_url = os.environ.get("DATABASE_URL")
    if database_url and database_url.startswith("postgresql") and using_neon:
        from urllib.parse import urlparse
        parsed_url = urlparse(database_url)
        return URL.create(
            drivername=driver,
            username=parsed_url.username,
            password=parsed_url.password,
            host=parsed_url.hostname,
            port=parsed_url.port or 5432,
            database=parsed_url.path.lstrip('/'),
            query={"ssl": "require"} if "require" in database_url else {}
        )
    
    # Standard connection URL construction
    url = URL.create(
        drivername=driver,
        username=db_config.user,
        password=db_config.password,
        host=db_config.host,
        port=db_config.port,
        database=db_config.database,
    )
    
    # Use connection pooler for Neon if configured
    if db_config.use_connection_pooler and using_neon:
        if ".neon.tech" in db_config.host:
            url = url.set(host=url.host.replace(".neon.tech", "-pooler.neon.tech"))
        else:
            logger.info("Connection pooler enabled but host doesn't contain .neon.tech - skipping modification")
    
    return url


def get_engine() -> AsyncEngine:
    """Get the global SQLAlchemy async engine, creating it if necessary."""
    global _engine
    if _engine is None:
        db_config = config.config.database
        connection_url = get_connection_url(async_driver=True)
        
        # Create async engine with pool configuration
        engine_kwargs = {
            "echo": logger.level <= logging.DEBUG,  # SQL echo for debug level
            "pool_size": db_config.poolsize,
            "pool_timeout": db_config.connect_timeout,
            "pool_pre_ping": True,  # Check connection before using from pool
            "max_overflow": 10,  # Allow up to 10 extra connections
        }
        
        # Add serverless-specific settings
        if db_config.is_serverless:
            engine_kwargs["pool_recycle"] = db_config.pool_recycle
            # Smaller pool size for serverless databases
            engine_kwargs["pool_size"] = min(db_config.poolsize, 10)
            
        # Add SSL mode for asyncpg in connect_args
        # For Neon DB, always use SSL
        if ".neon.tech" in db_config.host:
            engine_kwargs["connect_args"] = {"ssl": True}
        elif db_config.sslmode:
            engine_kwargs["connect_args"] = {"ssl": db_config.sslmode == "require"}
            
        _engine = create_async_engine(connection_url, **engine_kwargs)
        
        # Note: Event listening is different with async engines, see SQLAlchemy docs
    
    return _engine


def get_session_maker() -> sessionmaker:
    """Create a configured async sessionmaker."""
    engine = get_engine()
    return sessionmaker(
        class_=AsyncSession,
        expire_on_commit=False,
        bind=engine,
    )


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a new async session with context manager.
    
    Usage:
        async with get_session() as session:
            # Use session
    """
    session_factory = get_session_maker()
    async with session_factory() as session:
        yield session


@asynccontextmanager
async def session_context(timeout: int = None) -> AsyncGenerator[AsyncSession, None]:
    """Async context manager for database sessions.
    
    Args:
        timeout: Optional timeout in seconds for session operations (used for serverless DBs)
    
    Usage:
        async with session_context() as session:
            # Use session
            # Automatically commits if no exception occurs
            # Automatically rolls back if an exception occurs
    """
    import asyncio
    
    db_config = config.config.database
    session_factory = get_session_maker()
    
    # Use provided timeout or default to 10 seconds for serverless
    if timeout is None and db_config.is_serverless:
        timeout = 10
    
    async with session_factory() as session:
        try:
            yield session
            
            # Apply timeout for commit operation if specified (for serverless DBs)
            if timeout is not None:
                try:
                    await asyncio.wait_for(session.commit(), timeout=timeout)
                except asyncio.TimeoutError:
                    await session.rollback()
                    logger.error(f"Database commit timed out after {timeout} seconds")
                    raise SQLAlchemyError(f"Database commit timed out after {timeout} seconds")
            else:
                await session.commit()
                
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f"Database error: {e}")
            raise
        except Exception:
            await session.rollback()
            raise