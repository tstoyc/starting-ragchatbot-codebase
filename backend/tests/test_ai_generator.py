"""Tests for AIGenerator to validate direct responses and the tool-use loop."""

from unittest.mock import MagicMock, patch, call
from ai_generator import AIGenerator


FAKE_API_KEY = "sk-ant-test-key"
FAKE_MODEL = "claude-sonnet-4-20250514"


class TestAIGeneratorDirect:
    """Tests for direct (non-tool-use) responses."""

    @patch("ai_generator.anthropic.Anthropic")
    def test_direct_response_without_tools(self, MockAnthropic, mock_anthropic_direct):
        """When stop_reason != 'tool_use', returns response.content[0].text directly."""
        MockAnthropic.return_value = mock_anthropic_direct

        gen = AIGenerator(FAKE_API_KEY, FAKE_MODEL)
        result = gen.generate_response(query="What is the capital of France?")

        assert result == "Paris is the capital of France."
        mock_anthropic_direct.messages.create.assert_called_once()

    @patch("ai_generator.anthropic.Anthropic")
    def test_direct_response_with_tools_but_no_tool_use(self, MockAnthropic, mock_anthropic_direct):
        """When tools are provided but Claude doesn't use them, returns direct response."""
        MockAnthropic.return_value = mock_anthropic_direct

        gen = AIGenerator(FAKE_API_KEY, FAKE_MODEL)
        tools = [{"name": "search_course_content", "description": "Search", "input_schema": {}}]
        tool_manager = MagicMock()

        result = gen.generate_response(query="Hello", tools=tools, tool_manager=tool_manager)

        assert result == "Paris is the capital of France."
        tool_manager.execute_tool.assert_not_called()


class TestAIGeneratorToolUse:
    """Tests for the tool-use execution flow."""

    @patch("ai_generator.anthropic.Anthropic")
    def test_tool_use_calls_tool_manager(self, MockAnthropic, mock_anthropic_tool_use):
        """When stop_reason == 'tool_use', tool_manager.execute_tool() is called with correct name and kwargs."""
        MockAnthropic.return_value = mock_anthropic_tool_use

        gen = AIGenerator(FAKE_API_KEY, FAKE_MODEL)
        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "Search results about neural networks."
        tools = [{"name": "search_course_content", "description": "Search", "input_schema": {}}]

        gen.generate_response(query="Tell me about neural networks", tools=tools, tool_manager=tool_manager)

        tool_manager.execute_tool.assert_called_once_with(
            "search_course_content", query="neural networks"
        )

    @patch("ai_generator.anthropic.Anthropic")
    def test_tool_result_sent_in_second_call(self, MockAnthropic, mock_anthropic_tool_use):
        """After tool execution, second messages.create() call includes the tool result in messages."""
        MockAnthropic.return_value = mock_anthropic_tool_use

        gen = AIGenerator(FAKE_API_KEY, FAKE_MODEL)
        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "Found: neural network basics."
        tools = [{"name": "search_course_content", "description": "Search", "input_schema": {}}]

        gen.generate_response(query="neural networks", tools=tools, tool_manager=tool_manager)

        # Should have been called twice (initial + follow-up)
        assert mock_anthropic_tool_use.messages.create.call_count == 2

        # Inspect the second call's messages argument
        second_call_kwargs = mock_anthropic_tool_use.messages.create.call_args_list[1]
        messages = second_call_kwargs.kwargs.get("messages") or second_call_kwargs[1].get("messages")
        if messages is None:
            # Try positional via **params
            messages = second_call_kwargs.kwargs["messages"]

        # The last message should contain tool_result
        last_msg = messages[-1]
        assert last_msg["role"] == "user"
        tool_results = last_msg["content"]
        assert any(tr["type"] == "tool_result" for tr in tool_results)
        assert any("Found: neural network basics." in tr.get("content", "") for tr in tool_results)

    @patch("ai_generator.anthropic.Anthropic")
    def test_second_call_includes_tools_when_rounds_remain(self, MockAnthropic, mock_anthropic_tool_use):
        """In-loop follow-up calls include 'tools' so Claude can make another tool call if needed."""
        MockAnthropic.return_value = mock_anthropic_tool_use

        gen = AIGenerator(FAKE_API_KEY, FAKE_MODEL)
        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "Search results."
        tools = [{"name": "search_course_content", "description": "Search", "input_schema": {}}]

        gen.generate_response(query="neural networks", tools=tools, tool_manager=tool_manager)

        second_call_kwargs = mock_anthropic_tool_use.messages.create.call_args_list[1].kwargs
        assert "tools" in second_call_kwargs, (
            f"Second API call should include 'tools' while rounds remain, but got: {list(second_call_kwargs.keys())}"
        )

    @patch("ai_generator.anthropic.Anthropic")
    def test_returns_final_response_text(self, MockAnthropic, mock_anthropic_tool_use):
        """After tool-use loop, returns final_response.content[0].text."""
        MockAnthropic.return_value = mock_anthropic_tool_use

        gen = AIGenerator(FAKE_API_KEY, FAKE_MODEL)
        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "Search results."
        tools = [{"name": "search_course_content", "description": "Search", "input_schema": {}}]

        result = gen.generate_response(query="neural networks", tools=tools, tool_manager=tool_manager)

        assert result == "Neural networks are computational models inspired by the brain."


class TestAIGeneratorMultiRoundToolUse:
    """Tests for multi-round sequential tool calling."""

    TOOLS = [
        {"name": "get_course_outline", "description": "Outline", "input_schema": {}},
        {"name": "search_course_content", "description": "Search", "input_schema": {}},
    ]

    def _make_generator(self, MockAnthropic, mock_client):
        MockAnthropic.return_value = mock_client
        return AIGenerator(FAKE_API_KEY, FAKE_MODEL)

    def _make_tool_manager(self, side_effects=None):
        tm = MagicMock()
        if side_effects:
            tm.execute_tool.side_effect = side_effects
        else:
            tm.execute_tool.return_value = "Tool result."
        return tm

    @patch("ai_generator.anthropic.Anthropic")
    def test_two_round_makes_three_api_calls(self, MockAnthropic, mock_anthropic_two_round_tool_use):
        """Two rounds of tool use should produce exactly 3 API calls."""
        gen = self._make_generator(MockAnthropic, mock_anthropic_two_round_tool_use)
        tm = self._make_tool_manager(["Outline data.", "Search data."])

        gen.generate_response(query="What does lesson 3 cover?", tools=self.TOOLS, tool_manager=tm)

        assert mock_anthropic_two_round_tool_use.messages.create.call_count == 3

    @patch("ai_generator.anthropic.Anthropic")
    def test_two_round_executes_both_tools(self, MockAnthropic, mock_anthropic_two_round_tool_use):
        """Both tools should be executed with correct names and kwargs."""
        gen = self._make_generator(MockAnthropic, mock_anthropic_two_round_tool_use)
        tm = self._make_tool_manager(["Outline data.", "Search data."])

        gen.generate_response(query="What does lesson 3 cover?", tools=self.TOOLS, tool_manager=tm)

        assert tm.execute_tool.call_count == 2
        tm.execute_tool.assert_any_call(
            "get_course_outline", course_name="Deep Learning Fundamentals"
        )
        tm.execute_tool.assert_any_call(
            "search_course_content", query="backpropagation"
        )

    @patch("ai_generator.anthropic.Anthropic")
    def test_two_round_returns_final_text(self, MockAnthropic, mock_anthropic_two_round_tool_use):
        """Return value should be the final synthesis text."""
        gen = self._make_generator(MockAnthropic, mock_anthropic_two_round_tool_use)
        tm = self._make_tool_manager(["Outline data.", "Search data."])

        result = gen.generate_response(query="What does lesson 3 cover?", tools=self.TOOLS, tool_manager=tm)

        assert result == "Lesson 3 covers backpropagation in detail."

    @patch("ai_generator.anthropic.Anthropic")
    def test_two_round_intermediate_calls_include_tools(self, MockAnthropic, mock_anthropic_two_round_tool_use):
        """API calls 1 and 2 (in-loop) should include 'tools' in kwargs."""
        gen = self._make_generator(MockAnthropic, mock_anthropic_two_round_tool_use)
        tm = self._make_tool_manager(["Outline data.", "Search data."])

        gen.generate_response(query="What does lesson 3 cover?", tools=self.TOOLS, tool_manager=tm)

        calls = mock_anthropic_two_round_tool_use.messages.create.call_args_list
        assert "tools" in calls[0].kwargs, "First API call should include tools"
        assert "tools" in calls[1].kwargs, "Second API call should include tools"

    @patch("ai_generator.anthropic.Anthropic")
    def test_two_round_final_call_excludes_tools(self, MockAnthropic, mock_anthropic_two_round_tool_use):
        """The final synthesis API call (call 3) should NOT include 'tools'."""
        gen = self._make_generator(MockAnthropic, mock_anthropic_two_round_tool_use)
        tm = self._make_tool_manager(["Outline data.", "Search data."])

        gen.generate_response(query="What does lesson 3 cover?", tools=self.TOOLS, tool_manager=tm)

        calls = mock_anthropic_two_round_tool_use.messages.create.call_args_list
        assert "tools" not in calls[2].kwargs, (
            f"Final API call should not include 'tools', but got: {list(calls[2].kwargs.keys())}"
        )

    @patch("ai_generator.anthropic.Anthropic")
    def test_two_round_messages_accumulate(self, MockAnthropic, mock_anthropic_two_round_tool_use):
        """The final call should have 5 messages: user, assistant, user(tool_result), assistant, user(tool_result)."""
        gen = self._make_generator(MockAnthropic, mock_anthropic_two_round_tool_use)
        tm = self._make_tool_manager(["Outline data.", "Search data."])

        gen.generate_response(query="What does lesson 3 cover?", tools=self.TOOLS, tool_manager=tm)

        calls = mock_anthropic_two_round_tool_use.messages.create.call_args_list
        final_messages = calls[2].kwargs["messages"]

        assert len(final_messages) == 5
        assert [m["role"] for m in final_messages] == [
            "user", "assistant", "user", "assistant", "user"
        ]

    @patch("ai_generator.anthropic.Anthropic")
    def test_tool_error_sends_error_result_to_claude(self, MockAnthropic, mock_anthropic_tool_use):
        """When execute_tool raises, the error string is sent as tool_result and Claude still returns text."""
        MockAnthropic.return_value = mock_anthropic_tool_use

        gen = AIGenerator(FAKE_API_KEY, FAKE_MODEL)
        tm = MagicMock()
        tm.execute_tool.side_effect = RuntimeError("Connection timeout")
        tools = [{"name": "search_course_content", "description": "Search", "input_schema": {}}]

        result = gen.generate_response(query="neural networks", tools=tools, tool_manager=tm)

        # Should still get a response (the second mock response)
        assert result == "Neural networks are computational models inspired by the brain."

        # The tool_result message should contain the error string
        second_call_kwargs = mock_anthropic_tool_use.messages.create.call_args_list[1].kwargs
        messages = second_call_kwargs["messages"]
        tool_result_msg = messages[-1]
        assert tool_result_msg["role"] == "user"
        assert any(
            "Tool execution error: Connection timeout" in tr.get("content", "")
            for tr in tool_result_msg["content"]
        )

    @patch("ai_generator.anthropic.Anthropic")
    def test_one_round_regression(self, MockAnthropic, mock_anthropic_tool_use):
        """Existing single-round tool use still works: 2 API calls, correct result."""
        MockAnthropic.return_value = mock_anthropic_tool_use

        gen = AIGenerator(FAKE_API_KEY, FAKE_MODEL)
        tm = MagicMock()
        tm.execute_tool.return_value = "Search results."
        tools = [{"name": "search_course_content", "description": "Search", "input_schema": {}}]

        result = gen.generate_response(query="neural networks", tools=tools, tool_manager=tm)

        assert mock_anthropic_tool_use.messages.create.call_count == 2
        assert result == "Neural networks are computational models inspired by the brain."
