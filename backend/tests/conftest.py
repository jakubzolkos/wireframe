import pytest
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_llm_client():
    return AsyncMock()

@pytest.fixture
def mock_e2b_client():
    return AsyncMock()

@pytest.fixture
def mock_storage_client():
    return AsyncMock()

@pytest.fixture
def mock_db_session():
    return AsyncMock()
