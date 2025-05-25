"""
Unit tests for the database models.

These tests verify the functionality of the SQLAlchemy models.
"""
import pytest
from datetime import datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from mfai_db_repos.lib.database.base import Base
from mfai_db_repos.lib.database.models import Repository, RepositoryFile


@pytest.fixture
def test_engine():
    """Create a test database engine."""
    # Use SQLite in-memory database for testing
    return create_engine("sqlite:///:memory:")


@pytest.fixture
def test_session(test_engine):
    """Create a test database session."""
    # Create all tables in the test database
    Base.metadata.create_all(test_engine)
    
    # Create a session factory
    TestSessionLocal = sessionmaker(bind=test_engine)
    
    # Create a test session
    session = TestSessionLocal()
    
    try:
        yield session
    finally:
        session.close()


def test_repository_model(test_session):
    """Test the Repository model."""
    # Create a repository
    repo = Repository(
        url="https://github.com/test/test-repo.git",
        name="test-repo",
        default_branch="main",
        clone_path="/tmp/test-repo",
        status="ready",
        repo_metadata={"owner": "test", "description": "Test repository"},
    )
    test_session.add(repo)
    test_session.commit()
    
    # Get the repository from the database
    stmt = select(Repository).where(Repository.id == repo.id)
    db_repo = test_session.execute(stmt).scalar_one()
    
    # Check attributes
    assert db_repo.url == "https://github.com/test/test-repo.git"
    assert db_repo.name == "test-repo"
    assert db_repo.default_branch == "main"
    assert db_repo.clone_path == "/tmp/test-repo"
    assert db_repo.status == "ready"
    assert db_repo.repo_metadata == {"owner": "test", "description": "Test repository"}
    
    # Check timestamps
    assert db_repo.created_at is not None
    assert db_repo.updated_at is not None


def test_repository_file_model(test_session):
    """Test the RepositoryFile model."""
    # Create a repository
    repo = Repository(
        url="https://github.com/test/test-repo.git",
        name="test-repo",
        default_branch="main",
    )
    test_session.add(repo)
    test_session.commit()
    
    # Create a repository file
    repo_file = RepositoryFile(
        repo_id=repo.id,
        repo_url=repo.url,
        repo_name=repo.name,
        repo_branch=repo.default_branch,
        filepath="src/main.py",
        filename="main.py",
        extension=".py",
        file_size=1024,
        last_modified=datetime.utcnow(),
        git_status="added",
        content="print('Hello, world!')",
        file_type="python",
        tags="python,main",  # Using string instead of array for SQLite
    )
    test_session.add(repo_file)
    test_session.commit()
    
    # Get the repository file from the database
    stmt = select(RepositoryFile).where(RepositoryFile.id == repo_file.id)
    db_file = test_session.execute(stmt).scalar_one()
    
    # Check attributes
    assert db_file.repo_id == repo.id
    assert db_file.repo_url == repo.url
    assert db_file.repo_name == repo.name
    assert db_file.filepath == "src/main.py"
    assert db_file.filename == "main.py"
    assert db_file.extension == ".py"
    assert db_file.file_size == 1024
    assert db_file.git_status == "added"
    assert db_file.content == "print('Hello, world!')"
    assert db_file.file_type == "python"
    assert db_file.tags == "python,main"