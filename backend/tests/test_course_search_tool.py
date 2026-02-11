"""Tests for CourseSearchTool to validate search execution, result formatting, and source tracking."""

from unittest.mock import MagicMock
from vector_store import SearchResults
from search_tools import CourseSearchTool


class TestCourseSearchToolExecute:
    """Tests for CourseSearchTool.execute()"""

    def test_execute_returns_formatted_results(self, mock_vector_store, make_search_results):
        """execute(query) calls store.search() and returns formatted string with [CourseTitle - Lesson N] headers."""
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="neural networks")

        mock_vector_store.search.assert_called_once_with(
            query="neural networks", course_name=None, lesson_number=None
        )
        assert "[Deep Learning Fundamentals - Lesson 1]" in result
        assert "[Deep Learning Fundamentals - Lesson 2]" in result
        assert "neural networks and backpropagation" in result

    def test_execute_passes_filters_to_store(self, mock_vector_store):
        """course_name and lesson_number args are forwarded to store.search()."""
        tool = CourseSearchTool(mock_vector_store)
        tool.execute(query="optimizers", course_name="DL Basics", lesson_number=3)

        mock_vector_store.search.assert_called_once_with(
            query="optimizers", course_name="DL Basics", lesson_number=3
        )

    def test_execute_empty_results(self, mock_vector_store, make_search_results):
        """Returns 'No relevant content found' message when SearchResults.is_empty()."""
        mock_vector_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[]
        )
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="nonexistent topic")

        assert "No relevant content found" in result

    def test_execute_empty_results_with_filters(self, mock_vector_store):
        """Empty results message includes filter context."""
        mock_vector_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[]
        )
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="xyz", course_name="MCP", lesson_number=5)

        assert "No relevant content found" in result
        assert "MCP" in result
        assert "lesson 5" in result

    def test_execute_error_results(self, mock_vector_store, make_search_results):
        """Returns the error string from SearchResults.error."""
        mock_vector_store.search.return_value = make_search_results(error="Search error: connection failed")
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="anything")

        assert result == "Search error: connection failed"


class TestCourseSearchToolSources:
    """Tests for source tracking in CourseSearchTool."""

    def test_sources_are_dicts_with_label_and_url(self, mock_vector_store):
        """After execute(), last_sources contains dicts with 'label' and 'url' keys."""
        tool = CourseSearchTool(mock_vector_store)
        tool.execute(query="neural networks")

        assert len(tool.last_sources) > 0
        for source in tool.last_sources:
            assert isinstance(source, dict), f"Expected dict, got {type(source)}"
            assert "label" in source, f"Source missing 'label' key: {source}"
            assert "url" in source, f"Source missing 'url' key: {source}"

    def test_sources_deduplicated(self, mock_vector_store):
        """Multiple results from the same course+lesson produce only one source entry."""
        # Two results from the same course and lesson
        mock_vector_store.search.return_value = SearchResults(
            documents=["chunk A", "chunk B"],
            metadata=[
                {"course_title": "AI Course", "lesson_number": 1, "chunk_index": 0},
                {"course_title": "AI Course", "lesson_number": 1, "chunk_index": 1},
            ],
            distances=[0.1, 0.2],
        )
        tool = CourseSearchTool(mock_vector_store)
        tool.execute(query="test")

        labels = [s["label"] for s in tool.last_sources]
        assert labels.count("AI Course - Lesson 1") == 1

    def test_sources_include_lesson_links(self, mock_vector_store):
        """get_lesson_link() is called for sources with lesson numbers."""
        mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson/1"
        tool = CourseSearchTool(mock_vector_store)
        tool.execute(query="neural networks")

        mock_vector_store.get_lesson_link.assert_called()
        urls = [s["url"] for s in tool.last_sources if s["url"] is not None]
        assert len(urls) > 0
        assert "https://example.com/lesson/1" in urls

    def test_sources_no_lesson_number_has_no_url(self, mock_vector_store):
        """Results without a lesson_number should not call get_lesson_link and have url=None."""
        mock_vector_store.search.return_value = SearchResults(
            documents=["intro chunk"],
            metadata=[{"course_title": "AI Course", "lesson_number": None, "chunk_index": 0}],
            distances=[0.1],
        )
        tool = CourseSearchTool(mock_vector_store)
        tool.execute(query="intro")

        mock_vector_store.get_lesson_link.assert_not_called()
        assert tool.last_sources[0]["url"] is None
