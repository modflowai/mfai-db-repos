"""
Base module for SQLAlchemy models and database connectivity.

This module provides the base SQLAlchemy model and core database functionality
that will be used across the application.
"""
from datetime import datetime
from typing import Any, ClassVar, Dict, TypeVar

from sqlalchemy import Column, DateTime, Integer, MetaData
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase

# Convention for SQLAlchemy constraint naming
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""

    metadata = metadata

    # Type hints to aid development
    __tablename__: ClassVar[str]
    
    # Common columns
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    @declared_attr
    def __tablename__(cls) -> str:
        """Generate table name automatically based on class name."""
        # Convert CamelCase to snake_case
        name = cls.__name__
        return "".join(["_" + c.lower() if c.isupper() else c for c in name]).lstrip("_")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Base":
        """Create a new instance from a dictionary."""
        return cls(**{
            k: v for k, v in data.items() 
            if k in cls.__table__.columns.keys()
        })


# Type variable for model classes
ModelType = TypeVar("ModelType", bound=Base)