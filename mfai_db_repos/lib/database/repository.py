"""
Repository database operations module.

This module provides CRUD operations and queries for the Repository model.
"""
from typing import List, Optional, Union
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from mfai_db_repos.lib.database.models import Repository
from mfai_db_repos.utils.logger import get_logger

logger = get_logger(__name__)


class RepositoryRepository:
    """Repository pattern for Repository database operations."""
    
    def __init__(self, session: AsyncSession):
        """Initialize repository with session.
        
        Args:
            session: SQLAlchemy async session
        """
        self.session = session
    
    async def create(
        self,
        url: str,
        name: str,
        default_branch: Optional[str] = None,
        clone_path: Optional[Union[str, Path]] = None,
        metadata: Optional[dict] = None,
    ) -> Optional[Repository]:
        """Create a new repository record.
        
        Args:
            url: Repository URL
            name: Repository name
            default_branch: Default branch name
            clone_path: Path where the repository is cloned
            metadata: Additional metadata for the repository
            
        Returns:
            Newly created Repository object or None if creation failed
        """
        try:
            repository = Repository(
                url=url,
                name=name,
                default_branch=default_branch,
                clone_path=str(clone_path) if clone_path else None,
                status="created",
                metadata=metadata or {},
            )
            self.session.add(repository)
            await self.session.commit()
            
            logger.info(f"Created repository record: {repository.name} ({repository.url})")
            return repository
        except IntegrityError:
            logger.warning(f"Repository with URL {url} already exists")
            await self.session.rollback()
            return None
        except SQLAlchemyError as e:
            logger.error(f"Failed to create repository: {e}")
            await self.session.rollback()
            return None
    
    async def get_by_id(self, repository_id: int) -> Optional[Repository]:
        """Get a repository by ID.
        
        Args:
            repository_id: Repository ID
            
        Returns:
            Repository object or None if not found
        """
        stmt = select(Repository).where(Repository.id == repository_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_url(self, url: str) -> Optional[Repository]:
        """Get a repository by URL.
        
        Args:
            url: Repository URL
            
        Returns:
            Repository object or None if not found
        """
        stmt = select(Repository).where(Repository.url == url)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_name(self, name: str) -> Optional[Repository]:
        """Get a repository by name.
        
        Args:
            name: Repository name
            
        Returns:
            Repository object or None if not found
        """
        stmt = select(Repository).where(Repository.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_all(self) -> List[Repository]:
        """Get all repositories.
        
        Returns:
            List of all Repository objects
        """
        stmt = select(Repository).order_by(Repository.name)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def update(self, repository: Repository) -> Optional[Repository]:
        """Update a repository.
        
        Args:
            repository: Repository object to update
            
        Returns:
            Updated Repository object or None if update failed
        """
        try:
            # Update the updated_at timestamp
            repository.updated_at = datetime.utcnow()
            
            self.session.add(repository)
            await self.session.commit()
            
            logger.info(f"Updated repository: {repository.name} (ID: {repository.id})")
            return repository
        except SQLAlchemyError as e:
            logger.error(f"Failed to update repository: {e}")
            await self.session.rollback()
            return None
    
    async def delete(self, repository_id: int) -> bool:
        """Delete a repository.
        
        Args:
            repository_id: Repository ID
            
        Returns:
            True if delete succeeded, False otherwise
        """
        try:
            repository = await self.get_by_id(repository_id)
            if not repository:
                logger.warning(f"Repository with ID {repository_id} not found")
                return False
            
            await self.session.delete(repository)
            await self.session.commit()
            
            logger.info(f"Deleted repository: {repository.name} (ID: {repository.id})")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Failed to delete repository: {e}")
            await self.session.rollback()
            return False
    
    async def update_status(self, repository_id: int, status: str) -> bool:
        """Update repository status.
        
        Args:
            repository_id: Repository ID
            status: New status
            
        Returns:
            True if update succeeded, False otherwise
        """
        try:
            repository = await self.get_by_id(repository_id)
            if not repository:
                logger.warning(f"Repository with ID {repository_id} not found")
                return False
            
            repository.status = status
            repository.updated_at = datetime.utcnow()
            
            await self.session.commit()
            
            logger.info(f"Updated repository status: {repository.name} -> {status}")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Failed to update repository status: {e}")
            await self.session.rollback()
            return False
    
    async def update_last_commit(self, repository_id: int, commit_hash: str) -> bool:
        """Update repository last commit hash.
        
        Args:
            repository_id: Repository ID
            commit_hash: New commit hash
            
        Returns:
            True if update succeeded, False otherwise
        """
        try:
            repository = await self.get_by_id(repository_id)
            if not repository:
                logger.warning(f"Repository with ID {repository_id} not found")
                return False
            
            repository.last_commit_hash = commit_hash
            repository.updated_at = datetime.utcnow()
            
            await self.session.commit()
            
            logger.info(f"Updated repository last commit: {repository.name} -> {commit_hash}")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Failed to update repository last commit: {e}")
            await self.session.rollback()
            return False
    
    async def increment_file_count(self, repository_id: int, count: int = 1) -> bool:
        """Increment repository file count.
        
        Args:
            repository_id: Repository ID
            count: Count to increment by
            
        Returns:
            True if update succeeded, False otherwise
        """
        try:
            repository = await self.get_by_id(repository_id)
            if not repository:
                logger.warning(f"Repository with ID {repository_id} not found")
                return False
            
            if repository.file_count is not None:
                repository.file_count += count
            else:
                repository.file_count = count
            
            repository.updated_at = datetime.utcnow()
            
            await self.session.commit()
            
            logger.debug(f"Incremented repository file count: {repository.name} -> {repository.file_count}")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Failed to increment repository file count: {e}")
            await self.session.rollback()
            return False