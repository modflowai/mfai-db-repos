"""
Command modules for the GitContext CLI.
"""

from mfai_db_repos.cli.commands.embeddings import embeddings_group
from mfai_db_repos.cli.commands.repositories import repositories_group
from mfai_db_repos.cli.commands.files import files_group
from mfai_db_repos.cli.commands.process import process as process_group
from mfai_db_repos.cli.commands.database import database_group

__all__ = [
    'embeddings_group',
    'repositories_group',
    'files_group',
    'process_group',
    'database_group',
]