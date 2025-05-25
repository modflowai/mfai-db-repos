"""
Repository file database operations module.

This module provides CRUD operations and queries for the RepositoryFile model.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, Tuple

import numpy as np
from sqlalchemy import func, select, and_, or_, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from mfai_db_repos.lib.database.models import Repository, RepositoryFile
from mfai_db_repos.utils.logger import get_logger

logger = get_logger(__name__)


class RepositoryFileRepository:
    """Repository pattern for RepositoryFile database operations."""
    
    def __init__(self, session: AsyncSession):
        """Initialize repository with session.
        
        Args:
            session: SQLAlchemy async session
        """
        self.session = session
    
    async def create(
        self,
        repo_id: int,
        filepath: str,
        filename: str,
        extension: Optional[str] = None,
        content: Optional[str] = None,
        embedding: Optional[Union[List[float], np.ndarray]] = None,
        embedding_model: Optional[str] = None,
        file_size: Optional[int] = None,
        last_modified: Optional[datetime] = None,
        language: Optional[str] = None,
        commit_hash: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        file_type: Optional[str] = None,
        technical_level: Optional[str] = None,
        analysis: Optional[Dict[str, Any]] = None,
    ) -> Optional[RepositoryFile]:
        """Create a new repository file record.
        
        Args:
            repo_id: Repository ID
            filepath: Path to the file within the repository
            filename: Name of the file
            extension: File extension
            content: File content
            embedding: Embedding vector
            embedding_model: Model used to generate the embedding
            file_size: Size of the file in bytes
            last_modified: Last modification time
            language: Programming language of the file
            commit_hash: Git commit hash for the file
            metadata: Additional metadata for the file
            
        Returns:
            Newly created RepositoryFile object or None if creation failed
        """
        try:
            # Get repository to ensure it exists
            repository = await self.session.get(Repository, repo_id)
            if not repository:
                logger.warning(f"Repository with ID {repo_id} not found")
                return None
            
            # Convert embedding to list if it's a numpy array
            embedding_list = None
            if embedding is not None:
                if isinstance(embedding, np.ndarray):
                    embedding_list = embedding.tolist()
                else:
                    embedding_list = list(embedding)
            
            repo_file = RepositoryFile(
                repo_id=repo_id,
                repo_url=repository.url,
                repo_name=repository.name,
                repo_branch=repository.default_branch,
                repo_commit_hash=commit_hash,
                filepath=filepath,
                filename=filename,
                extension=extension,
                content=content,
                embedding=str(embedding_list) if embedding_list else None,
                embedding_string=embedding_model,
                file_size=file_size,
                last_modified=last_modified,
                git_status="added",
                indexed_at=datetime.utcnow(),
                tags=tags,
                file_type=file_type,
                technical_level=technical_level,
                analysis=analysis,
            )
            
            self.session.add(repo_file)
            await self.session.flush()
            
            # Update repository file count
            if repository.file_count is not None:
                repository.file_count += 1
            else:
                repository.file_count = 1
            
            await self.session.commit()
            
            logger.debug(f"Created repository file record: {filepath}")
            return repo_file
            
        except IntegrityError:
            logger.warning(f"Repository file with path {filepath} already exists for repository {repo_id}")
            await self.session.rollback()
            return None
        except SQLAlchemyError as e:
            logger.error(f"Failed to create repository file: {e}")
            await self.session.rollback()
            return None
    
    async def get_by_id(self, file_id: int) -> Optional[RepositoryFile]:
        """Get a repository file by ID.
        
        Args:
            file_id: File ID
            
        Returns:
            RepositoryFile object or None if not found
        """
        stmt = select(RepositoryFile).where(RepositoryFile.id == file_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_path(self, repository_id: int, path: str) -> Optional[RepositoryFile]:
        """Get a repository file by repository ID and path.
        
        Args:
            repository_id: Repository ID
            path: Path to the file within the repository
            
        Returns:
            RepositoryFile object or None if not found
        """
        stmt = select(RepositoryFile).where(
            RepositoryFile.repo_id == repository_id,
            RepositoryFile.filepath == path,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_repository_id(
        self,
        repository_id: int,
        limit: Optional[int] = None
    ) -> List[RepositoryFile]:
        """Get all files for a repository.
        
        Args:
            repository_id: Repository ID
            limit: Maximum number of files to return
            
        Returns:
            List of RepositoryFile objects
        """
        stmt = select(RepositoryFile).where(
            RepositoryFile.repo_id == repository_id
        ).order_by(
            RepositoryFile.filepath
        )
        
        if limit is not None:
            stmt = stmt.limit(limit)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
        
    async def search(
        self,
        repository_id: int,
        limit: int = 100,
        offset: int = 0, 
        path_pattern: Optional[str] = None,
        extension: Optional[str] = None,
        sort_by: str = "filepath",
        sort_order: str = "asc"
    ) -> List[RepositoryFile]:
        """Search for files in a repository.
        
        Args:
            repository_id: Repository ID
            limit: Maximum number of files to return
            offset: Number of files to skip for pagination
            path_pattern: Optional path pattern to filter by (SQL LIKE pattern)
            extension: Optional file extension to filter by
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)
            
        Returns:
            List of RepositoryFile objects matching criteria
        """
        # Start with the basic query
        conditions = [RepositoryFile.repo_id == repository_id]
        
        # Add path pattern filter if provided
        if path_pattern:
            conditions.append(RepositoryFile.filepath.like(f"%{path_pattern}%"))
        
        # Add extension filter if provided
        if extension:
            # Normalize extension (remove leading dot if present)
            ext = extension.lstrip(".")
            conditions.append(RepositoryFile.extension == ext)
        
        # Create the query
        stmt = select(RepositoryFile).where(and_(*conditions))
        
        # Add sorting
        if sort_by == "path":
            sort_field = RepositoryFile.filepath
        elif sort_by == "size":
            sort_field = RepositoryFile.file_size
        elif sort_by == "language":
            sort_field = RepositoryFile.language
        elif sort_by == "created_at":
            sort_field = RepositoryFile.created_at
        elif sort_by == "updated_at":
            sort_field = RepositoryFile.updated_at
        else:
            sort_field = RepositoryFile.filepath
        
        # Apply sort direction
        if sort_order.lower() == "desc":
            stmt = stmt.order_by(sort_field.desc())
        else:
            stmt = stmt.order_by(sort_field)
        
        # Add pagination
        if offset:
            stmt = stmt.offset(offset)
        if limit:
            stmt = stmt.limit(limit)
        
        # Execute query
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
        
    async def count_search_results(
        self,
        repository_id: int,
        path_pattern: Optional[str] = None,
        extension: Optional[str] = None,
        **kwargs  # Ignore other search parameters
    ) -> int:
        """Count files matching search criteria.
        
        Args:
            repository_id: Repository ID
            path_pattern: Optional path pattern to filter by (SQL LIKE pattern)
            extension: Optional file extension to filter by
            
        Returns:
            Count of matching files
        """
        # Start with the basic query
        conditions = [RepositoryFile.repo_id == repository_id]
        
        # Add path pattern filter if provided
        if path_pattern:
            conditions.append(RepositoryFile.filepath.like(f"%{path_pattern}%"))
        
        # Add extension filter if provided
        if extension:
            # Normalize extension (remove leading dot if present)
            ext = extension.lstrip(".")
            conditions.append(RepositoryFile.extension == ext)
        
        # Create the query
        stmt = select(func.count()).select_from(RepositoryFile).where(and_(*conditions))
        
        # Execute query
        result = await self.session.execute(stmt)
        return result.scalar_one() or 0
    
    async def count_by_repository_id(self, repository_id: int) -> int:
        """Get the count of files for a repository.
        
        Args:
            repository_id: Repository ID
            
        Returns:
            Count of files
        """
        stmt = select(func.count()).select_from(RepositoryFile).where(
            RepositoryFile.repo_id == repository_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() or 0
    
    async def get_files_without_embeddings(
        self,
        repository_id: int,
        limit: Optional[int] = None
    ) -> List[RepositoryFile]:
        """Get all files without embeddings for a repository.
        
        Args:
            repository_id: Repository ID
            limit: Maximum number of files to return
            
        Returns:
            List of RepositoryFile objects
        """
        stmt = select(RepositoryFile).where(
            RepositoryFile.repo_id == repository_id,
            or_(
                RepositoryFile.embedding.is_(None),
                RepositoryFile.embedding_string.is_(None)
            )
        ).order_by(
            RepositoryFile.filepath
        )
        
        if limit is not None:
            stmt = stmt.limit(limit)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def count_files_without_embeddings(self, repository_id: int) -> int:
        """Get the count of files without embeddings for a repository.
        
        Args:
            repository_id: Repository ID
            
        Returns:
            Count of files without embeddings
        """
        stmt = select(func.count()).select_from(RepositoryFile).where(
            RepositoryFile.repo_id == repository_id,
            or_(
                RepositoryFile.embedding.is_(None),
                RepositoryFile.embedding_string.is_(None)
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() or 0
    
    async def get_embedding_model_counts(self, repository_id: int) -> Dict[str, int]:
        """Get counts of embedding models used for a repository.
        
        Args:
            repository_id: Repository ID
            
        Returns:
            Dictionary of model names and counts
        """
        stmt = select(
            RepositoryFile.embedding_string,
            func.count(RepositoryFile.id)
        ).where(
            RepositoryFile.repo_id == repository_id,
            RepositoryFile.embedding.is_not(None),
            RepositoryFile.embedding_string.is_not(None)
        ).group_by(
            RepositoryFile.embedding_string
        )
        
        result = await self.session.execute(stmt)
        return {row[0]: row[1] for row in result.all()}
    
    async def get_all_embedding_model_counts(self) -> Dict[str, int]:
        """Get counts of embedding models used across all repositories.
        
        Returns:
            Dictionary of model names and counts
        """
        stmt = select(
            RepositoryFile.embedding_string,
            func.count(RepositoryFile.id)
        ).where(
            RepositoryFile.embedding.is_not(None),
            RepositoryFile.embedding_string.is_not(None)
        ).group_by(
            RepositoryFile.embedding_string
        )
        
        result = await self.session.execute(stmt)
        return {row[0]: row[1] for row in result.all()}
    
    async def update(self, file: RepositoryFile) -> Optional[RepositoryFile]:
        """Update a repository file.
        
        Args:
            file: RepositoryFile to update
            
        Returns:
            Updated RepositoryFile object or None if update failed
        """
        try:
            # Always update the updated_at timestamp
            file.updated_at = datetime.utcnow()
            
            self.session.add(file)
            await self.session.commit()
            
            logger.debug(f"Updated repository file: {file.filepath}")
            return file
        except SQLAlchemyError as e:
            logger.error(f"Failed to update repository file: {e}")
            await self.session.rollback()
            return None
    
    
    async def delete(self, file_id: int) -> bool:
        """Delete a repository file.
        
        Args:
            file_id: File ID
            
        Returns:
            True if delete succeeded, False otherwise
        """
        try:
            file = await self.get_by_id(file_id)
            if not file:
                logger.warning(f"Repository file with ID {file_id} not found")
                return False
            
            repository_id = file.repo_id
            path = file.filepath
            
            await self.session.delete(file)
            
            # Update repository file count
            repository = await self.session.get(Repository, repository_id)
            if repository and repository.file_count:
                repository.file_count = max(0, repository.file_count - 1)
            
            await self.session.commit()
            
            logger.debug(f"Deleted repository file: {path}")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Failed to delete repository file: {e}")
            await self.session.rollback()
            return False
    
