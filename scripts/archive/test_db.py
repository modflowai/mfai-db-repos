#!/usr/bin/env python3
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gitcontext.lib.database.connection import get_engine
from gitcontext.lib.database.base import Base


async def test_connection():
    """Test database connection."""
    try:
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(lambda _: print('Database connection successful'))
            
            # Check if tables exist
            await conn.run_sync(lambda conn: print(f"Tables exist: {Base.metadata.tables.keys()}"))
            
        print("Connection test completed successfully")
    except Exception as e:
        print(f"Database connection error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(test_connection())