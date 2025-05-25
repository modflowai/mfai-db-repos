"""
Basic test to ensure the testing setup works correctly.
"""
import pytest


def test_pytest_working():
    """Test that pytest is working correctly."""
    assert True


def test_import_mfai_db_repos():
    """Test that the mfai_db_repos package can be imported."""
    try:
        import mfai_db_repos
        assert True
    except ImportError:
        pytest.fail("Failed to import mfai_db_repos package")