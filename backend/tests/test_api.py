"""Tests for FastAPI API endpoints.

Uses a test-specific FastAPI app (from conftest.py) that mirrors production
endpoints but avoids the static file mount and real RAGSystem initialization.
"""

import pytest


class TestQueryEndpoint:
    """Tests for POST /api/query."""

    def test_query_returns_answer_and_sources(self, client, mock_rag_system):
        """Successful query returns answer, sources, and session_id."""
        response = client.post("/api/query", json={"query": "What are neural networks?"})

        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "Neural networks are computational models."
        assert len(data["sources"]) == 1
        assert data["sources"][0]["label"] == "Deep Learning - Lesson 1"
        assert data["session_id"] == "session_1"

    def test_query_with_existing_session_id(self, client, mock_rag_system):
        """Query with an explicit session_id passes it through."""
        response = client.post(
            "/api/query",
            json={"query": "follow up", "session_id": "my_session"},
        )

        assert response.status_code == 200
        assert response.json()["session_id"] == "my_session"
        mock_rag_system.query.assert_called_once_with("follow up", "my_session")

    def test_query_creates_session_when_none_provided(self, client, mock_rag_system):
        """When no session_id is sent, the endpoint creates one."""
        response = client.post("/api/query", json={"query": "hello"})

        assert response.status_code == 200
        mock_rag_system.session_manager.create_session.assert_called_once()

    def test_query_missing_query_field_returns_422(self, client):
        """Request body without 'query' field returns a validation error."""
        response = client.post("/api/query", json={})
        assert response.status_code == 422

    def test_query_empty_body_returns_422(self, client):
        """Empty request body returns a validation error."""
        response = client.post("/api/query", content=b"", headers={"content-type": "application/json"})
        assert response.status_code == 422

    def test_query_internal_error_returns_500(self, client, mock_rag_system):
        """If RAGSystem.query raises, the endpoint returns 500."""
        mock_rag_system.query.side_effect = RuntimeError("Something broke")

        response = client.post("/api/query", json={"query": "boom"})

        assert response.status_code == 500
        assert "Something broke" in response.json()["detail"]

    def test_query_sources_with_null_url(self, client, mock_rag_system):
        """Sources with null URLs are serialized correctly."""
        mock_rag_system.query.return_value = (
            "Answer text",
            [{"label": "Course - Lesson 2", "url": None}],
        )

        response = client.post("/api/query", json={"query": "test"})

        assert response.status_code == 200
        assert response.json()["sources"][0]["url"] is None


class TestCoursesEndpoint:
    """Tests for GET /api/courses."""

    def test_courses_returns_stats(self, client):
        """Returns total_courses and course_titles."""
        response = client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 2
        assert "Deep Learning Fundamentals" in data["course_titles"]
        assert "ML Engineering" in data["course_titles"]

    def test_courses_internal_error_returns_500(self, client, mock_rag_system):
        """If get_course_analytics raises, the endpoint returns 500."""
        mock_rag_system.get_course_analytics.side_effect = RuntimeError("DB down")

        response = client.get("/api/courses")

        assert response.status_code == 500
        assert "DB down" in response.json()["detail"]


class TestSessionEndpoint:
    """Tests for DELETE /api/session/{session_id}."""

    def test_clear_session_returns_ok(self, client, mock_rag_system):
        """Clearing a session returns status ok."""
        response = client.delete("/api/session/session_1")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        mock_rag_system.session_manager.clear_session.assert_called_once_with("session_1")
