"""
Package for handling vector embeddings in the GitContext system.
"""

from mfai_db_repos.lib.embeddings.base import EmbeddingConfig, EmbeddingProvider, EmbeddingVector
from mfai_db_repos.lib.embeddings.batch import BatchProcessor, BatchProcessingResult
from mfai_db_repos.lib.embeddings.google_genai import GoogleGenAIEmbeddingConfig, GoogleGenAIEmbeddingProvider
from mfai_db_repos.lib.embeddings.manager import EmbeddingManager, ProviderType
from mfai_db_repos.lib.embeddings.openai import OpenAIEmbeddingConfig, OpenAIEmbeddingProvider

__all__ = [
    'EmbeddingConfig',
    'EmbeddingProvider',
    'EmbeddingVector',
    'EmbeddingManager',
    'ProviderType',
    'OpenAIEmbeddingConfig',
    'OpenAIEmbeddingProvider',
    'GoogleGenAIEmbeddingConfig',
    'GoogleGenAIEmbeddingProvider',
    'BatchProcessor',
    'BatchProcessingResult',
]