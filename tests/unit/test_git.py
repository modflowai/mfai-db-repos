"""
Unit tests for Git operations.

These tests verify the functionality of Git repository management.
"""
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union
import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, Mock, patch

import pytest
from git import Repo

from mfai_db_repos.lib.git.repository import GitRepository, RepoStatus


class TestGitRepository:
    """Test cases for GitRepository class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def mock_repo(self):
        """Create a mock Git repository."""
        repo = Mock(spec=Repo)
        repo.head.commit.hexsha = "abcdef1234567890"
        repo.head.commit.committed_date = int(datetime.now().timestamp())
        repo.working_dir = "/fake/path"
        
        # Setup remotes
        remote = Mock()
        remote.fetch = Mock()
        remote.pull = Mock()
        repo.remotes.origin = remote
        
        return repo

    def test_init(self):
        """Test GitRepository initialization."""
        # Test with URL only
        repo = GitRepository("https://github.com/user/repo.git")
        assert repo.url == "https://github.com/user/repo.git"
        assert repo.name == "repo"
        assert repo.branch is not None
        assert repo.status == RepoStatus.CREATED
        
        # Test with all parameters
        clone_path = Path("/tmp/test_repo")
        repo = GitRepository(
            "https://github.com/user/repo.git",
            clone_path=clone_path,
            branch="develop",
            depth=10,
        )
        assert repo.url == "https://github.com/user/repo.git"
        assert repo.clone_path == clone_path
        assert repo.branch == "develop"
        assert repo.depth == 10

    def test_extract_repo_name(self):
        """Test repository name extraction from URL."""
        repo = GitRepository("https://github.com/user/repo.git")
        
        # Test different URL formats
        assert repo._extract_repo_name("https://github.com/user/repo.git") == "repo"
        assert repo._extract_repo_name("https://github.com/user/repo") == "repo"
        assert repo._extract_repo_name("git@github.com:user/repo.git") == "repo"
        assert repo._extract_repo_name("git@github.com:user/repo") == "repo"
        assert repo._extract_repo_name("https://github.com/user/repo/") == "repo"

    @patch("git.Repo.clone_from")
    def test_clone(self, mock_clone_from, temp_dir):
        """Test repository cloning."""
        # Setup
        clone_path = Path(temp_dir) / "test_repo"
        repo = GitRepository(
            "https://github.com/user/repo.git",
            clone_path=clone_path,
            branch="main",
        )
        
        # Create a mock for the cloned repo
        mock_cloned_repo = Mock(spec=Repo)
        mock_clone_from.return_value = mock_cloned_repo
        
        # Test successful clone
        result = repo.clone()
        assert result is True
        assert repo.status == RepoStatus.READY
        mock_clone_from.assert_called_once()
        
        # Test clone when already cloned
        repo._repo = mock_cloned_repo
        result = repo.clone()
        assert result is True  # Still returns True when already cloned
        assert repo.status == RepoStatus.READY
        
        # Test clone failure
        repo._repo = None
        mock_clone_from.side_effect = Exception("Clone failed")
        result = repo.clone()
        assert result is False
        assert repo.status == RepoStatus.ERROR

    @patch.object(GitRepository, "is_cloned")
    def test_update(self, mock_is_cloned, mock_repo):
        """Test repository update."""
        # Setup
        repo = GitRepository("https://github.com/user/repo.git")
        mock_is_cloned.return_value = True
        repo._repo = mock_repo
        
        # Mock old and new commit
        old_commit = Mock()
        new_commit = Mock()
        repo._repo.head.commit = old_commit
        
        # Mock fetch and pull
        repo._repo.remotes.origin.fetch = Mock()
        repo._repo.remotes.origin.pull = Mock()
        
        # Test no changes
        old_commit.diff.return_value = []
        repo._repo.head.commit = old_commit  # No change after pull
        success, changed_files = repo.update()
        assert success is True
        assert changed_files == []
        assert repo.status == RepoStatus.READY
        
        # Test with changes
        repo._repo.head.commit = new_commit  # Change after pull
        diff_a = Mock()
        diff_a.a_path = "file1.py"
        diff_a.b_path = "file1.py"
        diff_b = Mock()
        diff_b.a_path = "file2.py"
        diff_b.b_path = "file3.py"  # Renamed file
        old_commit.diff.return_value = [diff_a, diff_b]
        
        success, changed_files = repo.update()
        assert success is True
        assert sorted(changed_files) == sorted(["file1.py", "file2.py", "file3.py"])
        assert repo.status == RepoStatus.READY
        
        # Test update failure
        repo._repo.remotes.origin.pull.side_effect = Exception("Pull failed")
        success, changed_files = repo.update()
        assert success is False
        assert changed_files is None
        assert repo.status == RepoStatus.ERROR
        
        # Test update when not cloned
        mock_is_cloned.return_value = False
        success, changed_files = repo.update()
        assert success is False
        assert changed_files is None

    @patch.object(GitRepository, "is_cloned")
    def test_get_last_commit(self, mock_is_cloned, mock_repo):
        """Test getting the last commit hash."""
        # Setup
        repo = GitRepository("https://github.com/user/repo.git")
        
        # Test when not cloned
        mock_is_cloned.return_value = False
        assert repo.get_last_commit() is None
        
        # Test when cloned
        mock_is_cloned.return_value = True
        repo._repo = mock_repo
        assert repo.get_last_commit() == "abcdef1234567890"

    @patch.object(GitRepository, "is_cloned")
    def test_get_commit_time(self, mock_is_cloned, mock_repo):
        """Test getting commit timestamp."""
        # Setup
        repo = GitRepository("https://github.com/user/repo.git")
        
        # Test when not cloned
        mock_is_cloned.return_value = False
        assert repo.get_commit_time() is None
        
        # Test when cloned
        mock_is_cloned.return_value = True
        repo._repo = mock_repo
        commit_time = repo.get_commit_time()
        assert isinstance(commit_time, datetime)
        
        # Test with specific commit hash
        commit = Mock()
        commit.committed_date = int(datetime.now().timestamp())
        repo._repo.commit.return_value = commit
        
        commit_time = repo.get_commit_time("specific_hash")
        assert isinstance(commit_time, datetime)
        repo._repo.commit.assert_called_with("specific_hash")
        
        # Test with invalid commit hash
        repo._repo.commit.side_effect = Exception("Invalid commit")
        assert repo.get_commit_time("invalid_hash") is None

    @patch.object(GitRepository, "is_cloned")
    def test_get_file_content(self, mock_is_cloned, mock_repo):
        """Test getting file content at a specific revision."""
        # Setup
        repo = GitRepository("https://github.com/user/repo.git")
        
        # Test when not cloned
        mock_is_cloned.return_value = False
        assert repo.get_file_content("file.py") is None
        
        # Test when cloned
        mock_is_cloned.return_value = True
        repo._repo = mock_repo
        repo._repo.git.show.return_value = "file content"
        
        content = repo.get_file_content("file.py")
        assert content == "file content"
        repo._repo.git.show.assert_called_with("HEAD:file.py")
        
        # Test with specific revision
        content = repo.get_file_content("file.py", "abcdef")
        assert content == "file content"
        repo._repo.git.show.assert_called_with("abcdef:file.py")
        
        # Test when file doesn't exist
        repo._repo.git.show.side_effect = Exception("File not found")
        assert repo.get_file_content("nonexistent.py") is None

    @patch.object(GitRepository, "is_cloned")
    def test_get_repo_stats(self, mock_is_cloned, mock_repo):
        """Test getting repository statistics."""
        # Setup
        repo = GitRepository("https://github.com/user/repo.git")
        
        # Test when not cloned
        mock_is_cloned.return_value = False
        stats = repo.get_repo_stats()
        assert stats["status"] == str(RepoStatus.CREATED)
        assert stats["commit_count"] == 0
        
        # Test when cloned
        mock_is_cloned.return_value = True
        repo._repo = mock_repo
        
        # Mock repository data
        commits = [Mock(), Mock(), Mock()]
        branches = [Mock(), Mock()]
        repo._repo.iter_commits.return_value = commits
        repo._repo.branches = branches
        
        # Mock commit authors
        author1 = Mock()
        author1.name = "Author 1"
        author1.email = "author1@example.com"
        author2 = Mock()
        author2.name = "Author 2"
        author2.email = "author2@example.com"
        
        commits[0].author = author1
        commits[1].author = author2
        commits[2].author = author1
        
        # Set up active branch
        active_branch = Mock()
        active_branch.name = "main"
        repo._repo.active_branch = active_branch
        
        # Mock Path.glob and Path.stat
        with patch("pathlib.Path.glob") as mock_glob, patch("pathlib.Path.stat") as mock_stat:
            # Set up mock files
            mock_files = [Mock(), Mock(), Mock()]
            mock_glob.return_value = mock_files
            
            # Set up file sizes
            file_stat = Mock()
            file_stat.st_size = 1024  # 1KB
            mock_stat.return_value = file_stat
            
            # Get stats
            stats = repo.get_repo_stats()
            
            # Verify results
            assert stats["status"] == str(RepoStatus.CREATED)
            assert stats["commit_count"] == 3
            assert stats["branch_count"] == 2
            assert stats["contributor_count"] == 2
            assert stats["current_branch"] == "main"
            assert stats["last_commit"] == "abcdef1234567890"
            
            # Test error handling
            repo._repo.iter_commits.side_effect = Exception("Failed to get commits")
            stats = repo.get_repo_stats()
            assert stats["status"] == str(RepoStatus.CREATED)
            assert "error" in stats

    @patch.object(GitRepository, "is_cloned")
    def test_cleanup(self, mock_is_cloned, temp_dir):
        """Test repository cleanup."""
        # Setup
        clone_path = Path(temp_dir) / "test_repo"
        clone_path.mkdir(parents=True, exist_ok=True)
        
        repo = GitRepository(
            "https://github.com/user/repo.git",
            clone_path=clone_path,
        )
        
        # Create a dummy file to make sure directory is not empty
        dummy_file = clone_path / "dummy.txt"
        with open(dummy_file, "w") as f:
            f.write("test")
        
        # Test successful cleanup
        mock_repo = Mock(spec=Repo)
        repo._repo = mock_repo
        
        result = repo.cleanup()
        assert result is True
        assert not clone_path.exists()
        
        # Test cleanup when path doesn't exist
        repo.clone_path = Path(temp_dir) / "nonexistent"
        result = repo.cleanup()
        assert result is True  # Still returns True when path doesn't exist
        
        # Test cleanup failure
        clone_path.mkdir(parents=True, exist_ok=True)
        with open(dummy_file, "w") as f:
            f.write("test")
        
        with patch("shutil.rmtree") as mock_rmtree:
            mock_rmtree.side_effect = Exception("Cleanup failed")
            result = repo.cleanup()
            assert result is False