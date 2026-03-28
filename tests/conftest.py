"""Shared test fixtures for the AI service."""
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_ollama_client():
    """Mock OllamaClient for tests that don't need real LLM calls."""
    client = MagicMock()
    client.generate = AsyncMock(return_value="Mock LLM response")
    client.chat = AsyncMock(return_value="Mock chat response")
    client.is_available = AsyncMock(return_value=True)
    return client


@pytest.fixture
def mock_rag_service():
    """Mock RAGService for tests that don't need real ChromaDB."""
    service = MagicMock()
    service.initialize = MagicMock()
    service.is_available = MagicMock(return_value=True)
    service.get_document_count = MagicMock(return_value=0)
    service.search = MagicMock(return_value=[])
    service.add_document = MagicMock(return_value="mock-doc-id")
    return service


@pytest.fixture
def mock_db_query(monkeypatch):
    """Mock database queries for tests that don't need real DB."""
    mock = MagicMock(return_value=[])
    monkeypatch.setattr("database.execute_read_query", mock)
    return mock
