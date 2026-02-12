import sys
import os
from unittest.mock import MagicMock, patch
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

import pytest

# Add backend to sys.path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vector_store import SearchResults
from search_tools import ToolManager, CourseSearchTool


# --- SearchResults factory ---

@pytest.fixture
def make_search_results():
    """Factory fixture for creating SearchResults with sample data."""
    def _make(
        documents: Optional[List[str]] = None,
        metadata: Optional[List[Dict[str, Any]]] = None,
        distances: Optional[List[float]] = None,
        error: Optional[str] = None,
    ) -> SearchResults:
        if error:
            return SearchResults.empty(error)
        docs = documents or [
            "Chunk about neural networks and backpropagation.",
            "Chunk about gradient descent optimizers.",
        ]
        meta = metadata or [
            {"course_title": "Deep Learning Fundamentals", "lesson_number": 1, "chunk_index": 0},
            {"course_title": "Deep Learning Fundamentals", "lesson_number": 2, "chunk_index": 1},
        ]
        dists = distances or [0.25, 0.40]
        return SearchResults(documents=docs, metadata=meta, distances=dists)
    return _make


# --- Mock VectorStore ---

@pytest.fixture
def mock_vector_store(make_search_results):
    """A mocked VectorStore with search(), get_lesson_link(), _resolve_course_name(), and course_catalog."""
    store = MagicMock()
    store.search.return_value = make_search_results()
    store.get_lesson_link.return_value = "https://example.com/lesson/1"
    store._resolve_course_name.return_value = "Deep Learning Fundamentals"
    store.course_catalog = MagicMock()
    return store


# --- Mock Anthropic client helpers ---

def _make_text_block(text: str):
    """Create a mock TextBlock."""
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def _make_tool_use_block(tool_id: str, name: str, input_data: dict):
    """Create a mock ToolUseBlock."""
    block = MagicMock()
    block.type = "tool_use"
    block.id = tool_id
    block.name = name
    block.input = input_data
    return block


def _make_response(stop_reason: str, content_blocks: list):
    """Create a mock Anthropic messages.create() response."""
    response = MagicMock()
    response.stop_reason = stop_reason
    response.content = content_blocks
    return response


@pytest.fixture
def mock_anthropic_direct():
    """Mock Anthropic client that returns a direct text response (no tool use)."""
    client = MagicMock()
    response = _make_response("end_turn", [_make_text_block("Paris is the capital of France.")])
    client.messages.create.return_value = response
    return client


@pytest.fixture
def mock_anthropic_tool_use():
    """Mock Anthropic client that first returns tool_use, then a final text response."""
    client = MagicMock()

    tool_use_block = _make_tool_use_block(
        tool_id="toolu_01ABC",
        name="search_course_content",
        input_data={"query": "neural networks"},
    )
    first_response = _make_response("tool_use", [tool_use_block])

    final_response = _make_response(
        "end_turn",
        [_make_text_block("Neural networks are computational models inspired by the brain.")],
    )

    client.messages.create.side_effect = [first_response, final_response]
    return client


@pytest.fixture
def mock_anthropic_two_round_tool_use():
    """Mock Anthropic client that returns two sequential tool_use responses, then a final text response."""
    client = MagicMock()

    # Round 1: get_course_outline
    first_tool_block = _make_tool_use_block(
        tool_id="toolu_01OUTLINE",
        name="get_course_outline",
        input_data={"course_name": "Deep Learning Fundamentals"},
    )
    first_response = _make_response("tool_use", [first_tool_block])

    # Round 2: search_course_content
    second_tool_block = _make_tool_use_block(
        tool_id="toolu_02SEARCH",
        name="search_course_content",
        input_data={"query": "backpropagation"},
    )
    second_response = _make_response("tool_use", [second_tool_block])

    # Final synthesis
    final_response = _make_response(
        "end_turn",
        [_make_text_block("Lesson 3 covers backpropagation in detail.")],
    )

    client.messages.create.side_effect = [first_response, second_response, final_response]
    return client


# --- Mock ToolManager ---

@pytest.fixture
def mock_tool_manager(mock_vector_store):
    """A real ToolManager with a CourseSearchTool backed by the mock store."""
    tm = ToolManager()
    search_tool = CourseSearchTool(mock_vector_store)
    tm.register_tool(search_tool)
    return tm


# --- Mock RAG System for API tests ---

@pytest.fixture
def mock_rag_system():
    """A fully mocked RAGSystem suitable for API endpoint testing."""
    rag = MagicMock()
    rag.query.return_value = (
        "Neural networks are computational models.",
        [{"label": "Deep Learning - Lesson 1", "url": "https://example.com/1"}],
    )
    rag.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": ["Deep Learning Fundamentals", "ML Engineering"],
    }
    rag.session_manager.create_session.return_value = "session_1"
    rag.session_manager.clear_session.return_value = None
    return rag


# --- Test FastAPI app ---

@pytest.fixture
def test_app(mock_rag_system):
    """A FastAPI test app that mirrors production endpoints but skips static file mounts.

    This avoids the import-time side effects in app.py (RAGSystem init, static file mount
    requiring ../frontend to exist) by defining the endpoints inline with a mocked RAGSystem.
    """
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    from typing import List, Optional

    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class SourceItem(BaseModel):
        label: str
        url: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[SourceItem]
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]

    app = FastAPI()

    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = mock_rag_system.session_manager.create_session()
            answer, sources = mock_rag_system.query(request.query, session_id)
            return QueryResponse(answer=answer, sources=sources, session_id=session_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.delete("/api/session/{session_id}")
    async def clear_session(session_id: str):
        mock_rag_system.session_manager.clear_session(session_id)
        return {"status": "ok"}

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = mock_rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"],
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return app


@pytest.fixture
def client(test_app):
    """A synchronous test client for the test FastAPI app."""
    from starlette.testclient import TestClient
    return TestClient(test_app)
