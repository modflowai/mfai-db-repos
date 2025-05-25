#!/usr/bin/env python3
"""
Initialize database tables.
"""
import asyncio
import os
import sys
import argparse

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mfai_db_repos.lib.database.base import Base
from mfai_db_repos.lib.database.connection import get_engine


async def init_db(drop_tables=False):
    """Initialize database tables.
    
    Args:
        drop_tables: If True, drop existing tables before creating new ones
    """
    try:
        engine = get_engine()
        async with engine.begin() as conn:
            if drop_tables:
                print("Dropping existing tables...")
                await conn.run_sync(Base.metadata.drop_all)
                print("Tables dropped.")
                
            print("Creating database tables...")
            await conn.run_sync(Base.metadata.create_all)
            print("Database tables created successfully.")
    except Exception as e:
        print(f"Error initializing database: {e}")
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize database tables")
    parser.add_argument("--drop", action="store_true", help="Drop existing tables before creating new ones")
    args = parser.parse_args()
    
    asyncio.run(init_db(drop_tables=args.drop))