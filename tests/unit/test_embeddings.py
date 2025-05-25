"""
Tests for embedding generation functionality.
"""
import asyncio
import os
import unittest
from unittest import mock
from typing import List

import pytest

from mfai_db_repos.lib.embeddings import (
    BatchProcessor,
    BatchProcessingResult,
    EmbeddingConfig,
    EmbeddingVector,
    EmbeddingManager,
    ProviderType,
    OpenAIEmbeddingConfig,
    OpenAIEmbeddingProvider,
    GoogleGenAIEmbeddingConfig,
    GoogleGenAIEmbeddingProvider,
)


class TestEmbeddingVector(unittest.TestCase):
    """Tests for the EmbeddingVector class."""
    
    def test_creation(self):
        """Test creating an embedding vector."""
        vector = [0.1, 0.2, 0.3, 0.4, 0.5]
        model = "test-model"
        
        emb = EmbeddingVector(vector=vector, model=model)
        
        self.assertEqual(emb.vector, vector)
        self.assertEqual(emb.model, model)
        self.assertEqual(emb.dimensions, len(vector))
    
    def test_to_numpy(self):
        """Test converting to a numpy array."""
        vector = [0.1, 0.2, 0.3, 0.4, 0.5]
        model = "test-model"
        
        emb = EmbeddingVector(vector=vector, model=model)
        np_vec = emb.to_numpy()
        
        self.assertEqual(np_vec.shape, (len(vector),))
        self.assertEqual(np_vec.dtype, 'float32')
        self.assertEqual(np_vec[0], vector[0])


class TestEmbeddingConfig(unittest.TestCase):
    """Tests for the EmbeddingConfig class."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = EmbeddingConfig(model="test-model", dimensions=128)
        
        self.assertEqual(config.model, "test-model")
        self.assertEqual(config.dimensions, 128)
        self.assertEqual(config.batch_size, 20)
        self.assertEqual(config.max_parallel_requests, 5)
        self.assertEqual(config.retry_attempts, 3)
        self.assertEqual(config.timeout_seconds, 30)
    
    def test_custom_values(self):
        """Test custom configuration values."""
        config = EmbeddingConfig(
            model="custom-model",
            dimensions=256,
            batch_size=10,
            max_parallel_requests=3,
            retry_attempts=5,
            timeout_seconds=60
        )
        
        self.assertEqual(config.model, "custom-model")
        self.assertEqual(config.dimensions, 256)
        self.assertEqual(config.batch_size, 10)
        self.assertEqual(config.max_parallel_requests, 3)
        self.assertEqual(config.retry_attempts, 5)
        self.assertEqual(config.timeout_seconds, 60)


class TestBatchProcessor:
    """Tests for the BatchProcessor class."""
    
    @pytest.mark.asyncio
    async def test_process_batch_async(self):
        """Test processing a batch asynchronously."""
        async def process_func(x):
            await asyncio.sleep(0.01)
            return x * 2
        
        processor = BatchProcessor(
            process_func=process_func,
            max_concurrency=3,
            batch_size=5
        )
        
        items = [1, 2, 3, 4, 5]
        result = await processor.process_batch(items)
        
        assert result.success_count == 5
        assert result.failure_count == 0
        assert set(result.successful) == {2, 4, 6, 8, 10}
        assert result.failed == []
        assert result.errors == {}
    
    @pytest.mark.asyncio
    async def test_process_batch_with_errors(self):
        """Test processing a batch with errors."""
        async def process_func(x):
            await asyncio.sleep(0.01)
            if x % 2 == 0:
                raise ValueError(f"Error for {x}")
            return x * 2
        
        processor = BatchProcessor(
            process_func=process_func,
            max_concurrency=3,
            batch_size=5
        )
        
        items = [1, 2, 3, 4, 5]
        result = await processor.process_batch(items)
        
        assert result.success_count == 3
        assert result.failure_count == 2
        assert set(result.successful) == {2, 6, 10}
        assert set(result.failed) == {2, 4}
        assert len(result.errors) == 2
        assert isinstance(list(result.errors.values())[0], ValueError)


@pytest.mark.asyncio
class TestEmbeddingProviders:
    """Tests for embedding providers using mocks."""
    
    async def test_openai_provider_embed_text(self):
        """Test OpenAI provider embedding text."""
        # Create mock client
        mock_client = mock.AsyncMock()
        mock_response = mock.MagicMock()
        mock_response.data = [mock.MagicMock(embedding=[0.1, 0.2, 0.3])]
        mock_client.embeddings.create.return_value = mock_response
        
        config = OpenAIEmbeddingConfig(model="test-model", dimensions=3)
        provider = OpenAIEmbeddingProvider(config)
        provider.client = mock_client
        
        result = await provider.embed_text("test text")
        
        assert isinstance(result, EmbeddingVector)
        assert result.vector == [0.1, 0.2, 0.3]
        assert result.dimensions == 3
        assert result.model == "test-model"
        
        # Verify client called correctly
        mock_client.embeddings.create.assert_called_once_with(
            model="test-model",
            input="test text"
        )
    
    async def test_google_genai_provider_embed_text(self):
        """Test Google GenAI provider embedding text."""
        # Create mock client
        mock_client = mock.AsyncMock()
        mock_response = mock.MagicMock()
        mock_response.embedding.values = [0.1, 0.2, 0.3]
        mock_client.models.embed_content.return_value = mock_response
        
        config = GoogleGenAIEmbeddingConfig(model="test-model", dimensions=3)
        provider = GoogleGenAIEmbeddingProvider(config)
        provider.async_client = mock_client
        
        result = await provider.embed_text("test text")
        
        assert isinstance(result, EmbeddingVector)
        assert result.vector == [0.1, 0.2, 0.3]
        assert result.dimensions == 3
        assert result.model == "test-model"


@pytest.mark.asyncio
class TestEmbeddingManager:
    """Tests for the EmbeddingManager class."""
    
    async def test_embed_text(self):
        """Test embedding text with the manager."""
        # Create mock provider
        mock_provider = mock.AsyncMock()
        mock_result = EmbeddingVector(vector=[0.1, 0.2, 0.3], model="test-model")
        mock_provider.embed_text.return_value = mock_result
        
        manager = EmbeddingManager(primary_provider=ProviderType.OPENAI)
        manager.primary_provider = mock_provider
        
        result = await manager.embed_text("test text")
        
        assert result == mock_result
        mock_provider.embed_text.assert_called_once_with("test text")
    
    async def test_embed_batch(self):
        """Test embedding a batch with the manager."""
        # Create mock provider
        mock_provider = mock.AsyncMock()
        mock_results = [
            EmbeddingVector(vector=[0.1, 0.2, 0.3], model="test-model"),
            EmbeddingVector(vector=[0.4, 0.5, 0.6], model="test-model")
        ]
        mock_provider.embed_batch.return_value = mock_results
        
        manager = EmbeddingManager(primary_provider=ProviderType.OPENAI)
        manager.primary_provider = mock_provider
        
        texts = ["text 1", "text 2"]
        result = await manager.embed_batch(texts)
        
        assert result == mock_results
        mock_provider.embed_batch.assert_called_once_with(texts)
    
    async def test_secondary_provider(self):
        """Test using the secondary provider."""
        # Create mock providers
        mock_primary = mock.AsyncMock()
        mock_secondary = mock.AsyncMock()
        
        mock_primary_result = EmbeddingVector(vector=[0.1, 0.2, 0.3], model="primary-model")
        mock_secondary_result = EmbeddingVector(vector=[0.4, 0.5, 0.6], model="secondary-model")
        
        mock_primary.embed_text.return_value = mock_primary_result
        mock_secondary.embed_text.return_value = mock_secondary_result
        
        manager = EmbeddingManager(
            primary_provider=ProviderType.OPENAI,
            secondary_provider=ProviderType.GOOGLE_GENAI
        )
        manager.primary_provider = mock_primary
        manager.secondary_provider = mock_secondary
        
        # Test primary provider (default)
        result1 = await manager.embed_text("test text")
        assert result1 == mock_primary_result
        
        # Test secondary provider
        result2 = await manager.embed_text("test text", use_secondary=True)
        assert result2 == mock_secondary_result


if __name__ == "__main__":
    unittest.main()