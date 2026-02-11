"""Tests for RAGSystem.query() to validate the orchestration flow and source compatibility."""

import sys
import os
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

# Ensure backend is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rag_system import RAGSystem
from search_tools import ToolManager, CourseSearchTool


# We need a SourceItem import to validate API contract compatibility.
# It lives in app.py but has no heavy deps beyond pydantic.
from pydantic import BaseModel
from typing import Optional


class SourceItem(BaseModel):
    """Mirror of the SourceItem in app.py for contract testing."""
    label: str
    url: Optional[str] = None


def _make_rag_system(ai_generate_return="Mocked AI response", sources=None):
    """Create a RAGSystem with mocked internals, avoiding real ChromaDB/Anthropic."""
    if sources is None:
        sources = [{"label": "DL Course - Lesson 1", "url": "https://example.com/1"}]

    with patch("rag_system.DocumentProcessor"), \
         patch("rag_system.VectorStore"), \
         patch("rag_system.AIGenerator") as MockAIGen, \
         patch("rag_system.SessionManager") as MockSession:

        mock_config = MagicMock()
        mock_config.CHUNK_SIZE = 800
        mock_config.CHUNK_OVERLAP = 100
        mock_config.CHROMA_PATH = "./test_chroma"
        mock_config.EMBEDDING_MODEL = "test-model"
        mock_config.MAX_RESULTS = 5
        mock_config.ANTHROPIC_API_KEY = "sk-test"
        mock_config.ANTHROPIC_MODEL = "claude-test"
        mock_config.MAX_HISTORY = 2

        rag = RAGSystem(mock_config)

        # Configure ai_generator mock
        rag.ai_generator.generate_response.return_value = ai_generate_return

        # Configure tool_manager to return our sources
        rag.tool_manager = MagicMock(spec=ToolManager)
        rag.tool_manager.get_tool_definitions.return_value = [{"name": "search_course_content"}]
        rag.tool_manager.get_last_sources.return_value = sources
        rag.tool_manager.reset_sources.return_value = None

        # Configure session manager
        rag.session_manager.get_conversation_history.return_value = None

        return rag


class TestRAGSystemQuery:
    """Tests for RAGSystem.query() orchestration."""

    def test_query_returns_response_and_sources(self):
        """query() returns a (str, list) tuple."""
        rag = _make_rag_system()
        result = rag.query("What are neural networks?")

        assert isinstance(result, tuple)
        assert len(result) == 2
        response, sources = result
        assert isinstance(response, str)
        assert isinstance(sources, list)

    def test_query_passes_tools_to_generator(self):
        """ai_generator.generate_response() receives tool definitions and tool_manager."""
        rag = _make_rag_system()
        rag.query("test query")

        call_kwargs = rag.ai_generator.generate_response.call_args.kwargs
        assert "tools" in call_kwargs
        assert call_kwargs["tools"] == [{"name": "search_course_content"}]
        assert "tool_manager" in call_kwargs
        assert call_kwargs["tool_manager"] is rag.tool_manager

    def test_sources_compatible_with_source_item_model(self):
        """Sources from query() can be validated by the SourceItem Pydantic model (the API contract)."""
        sources = [
            {"label": "DL Course - Lesson 1", "url": "https://example.com/1"},
            {"label": "ML Course - Lesson 3", "url": None},
        ]
        rag = _make_rag_system(sources=sources)
        _, returned_sources = rag.query("test query")

        for source in returned_sources:
            # This will raise ValidationError if the source doesn't match the contract
            item = SourceItem(**source)
            assert item.label
            assert isinstance(item.url, (str, type(None)))

    def test_sources_reset_between_queries(self):
        """tool_manager.reset_sources() is called so sources don't leak between queries."""
        rag = _make_rag_system()
        rag.query("first query")

        rag.tool_manager.reset_sources.assert_called_once()

    def test_session_history_forwarded(self):
        """Conversation history from session_manager is passed to generate_response()."""
        rag = _make_rag_system()
        rag.session_manager.get_conversation_history.return_value = "User: hi\nAssistant: hello"

        rag.query("follow up question", session_id="session_1")

        call_kwargs = rag.ai_generator.generate_response.call_args.kwargs
        assert call_kwargs["conversation_history"] == "User: hi\nAssistant: hello"

    def test_session_history_none_without_session_id(self):
        """When no session_id provided, conversation_history is None."""
        rag = _make_rag_system()
        rag.query("question without session")

        call_kwargs = rag.ai_generator.generate_response.call_args.kwargs
        assert call_kwargs["conversation_history"] is None

    def test_query_adds_exchange_to_session(self):
        """After query, the exchange is added to session history."""
        rag = _make_rag_system(ai_generate_return="The answer is 42.")
        rag.query("What is the answer?", session_id="session_1")

        rag.session_manager.add_exchange.assert_called_once()
        args = rag.session_manager.add_exchange.call_args
        assert args[0][0] == "session_1"  # session_id
        assert "answer" in args[0][1].lower() or "answer" in args[0][2].lower()  # query or response
