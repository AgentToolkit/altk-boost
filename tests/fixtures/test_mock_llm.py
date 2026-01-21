"""Tests for the MockLLMClient implementation."""

import asyncio
import pytest
import time

from tests.fixtures.mock_llm import (
    MockLLMClient,
    StaticResponseStrategy,
    CallbackResponseStrategy,
    EchoResponseStrategy,
    CallRecord,
)
from tests.fixtures.response_builders import ResponseBuilder
from altk.core.llm.types import GenerationMode, LLMResponse


class TestStaticResponseStrategy:
    """Tests for StaticResponseStrategy."""

    def test_returns_responses_in_order(self):
        """Test that responses are returned in sequence."""
        strategy = StaticResponseStrategy(["Response 1", "Response 2", "Response 3"])

        assert strategy.get_response("prompt", GenerationMode.CHAT) == "Response 1"
        assert strategy.get_response("prompt", GenerationMode.CHAT) == "Response 2"
        assert strategy.get_response("prompt", GenerationMode.CHAT) == "Response 3"

    def test_raises_error_when_exhausted(self):
        """Test that error is raised when all responses are consumed."""
        strategy = StaticResponseStrategy(["Only response"])

        strategy.get_response("prompt", GenerationMode.CHAT)

        with pytest.raises(ValueError, match="No more responses configured"):
            strategy.get_response("prompt", GenerationMode.CHAT)

    def test_reset_restarts_sequence(self):
        """Test that reset allows reusing responses."""
        strategy = StaticResponseStrategy(["Response 1", "Response 2"])

        assert strategy.get_response("prompt", GenerationMode.CHAT) == "Response 1"
        assert strategy.get_response("prompt", GenerationMode.CHAT) == "Response 2"

        strategy.reset()

        assert strategy.get_response("prompt", GenerationMode.CHAT) == "Response 1"

    def test_empty_responses_raises_error(self):
        """Test that empty responses list raises error."""
        with pytest.raises(ValueError, match="responses list cannot be empty"):
            StaticResponseStrategy([])


class TestCallbackResponseStrategy:
    """Tests for CallbackResponseStrategy."""

    def test_uses_callback_function(self):
        """Test that callback is called to generate responses."""

        def callback(prompt, mode, kwargs):
            return f"Callback received: {prompt}"

        strategy = CallbackResponseStrategy(callback)
        result = strategy.get_response("Test prompt", GenerationMode.CHAT)

        assert result == "Callback received: Test prompt"

    def test_callback_receives_all_arguments(self):
        """Test that callback receives prompt, mode, and kwargs."""
        received_args = {}

        def callback(prompt, mode, kwargs):
            received_args["prompt"] = prompt
            received_args["mode"] = mode
            received_args["kwargs"] = kwargs
            return "Response"

        strategy = CallbackResponseStrategy(callback)
        strategy.get_response("Test", GenerationMode.CHAT, temperature=0.7)

        assert received_args["prompt"] == "Test"
        assert received_args["mode"] == GenerationMode.CHAT
        assert received_args["kwargs"]["temperature"] == 0.7


class TestEchoResponseStrategy:
    """Tests for EchoResponseStrategy."""

    def test_echoes_string_prompt(self):
        """Test echoing a string prompt."""
        strategy = EchoResponseStrategy()
        result = strategy.get_response("Hello world", GenerationMode.TEXT)

        assert result == "Echo: Hello world"

    def test_echoes_chat_messages(self):
        """Test echoing chat messages."""
        strategy = EchoResponseStrategy()
        messages = [{"role": "user", "content": "What is the weather?"}]
        result = strategy.get_response(messages, GenerationMode.CHAT)

        assert result == "Echo: What is the weather?"

    def test_custom_prefix(self):
        """Test using a custom prefix."""
        strategy = EchoResponseStrategy(prefix="MOCK: ")
        result = strategy.get_response("Test", GenerationMode.TEXT)

        assert result == "MOCK: Test"


class TestMockLLMClient:
    """Tests for MockLLMClient."""

    def test_basic_generation(self):
        """Test basic text generation."""
        mock = MockLLMClient(responses=["Test response"])
        result = mock.generate("Test prompt")

        assert result == "Test response"

    def test_multiple_generations(self):
        """Test multiple sequential generations."""
        mock = MockLLMClient(responses=["Response 1", "Response 2", "Response 3"])

        assert mock.generate("Prompt 1") == "Response 1"
        assert mock.generate("Prompt 2") == "Response 2"
        assert mock.generate("Prompt 3") == "Response 3"

    def test_call_tracking(self):
        """Test that calls are tracked correctly."""
        mock = MockLLMClient(responses=["Response"])

        assert mock.call_count == 0
        assert len(mock.call_history) == 0

        mock.generate("Test prompt", temperature=0.7)

        assert mock.call_count == 1
        assert len(mock.call_history) == 1

    def test_call_record_contents(self):
        """Test that call records contain correct information."""
        mock = MockLLMClient(responses=["Response"])
        mock.generate("Test prompt", mode=GenerationMode.CHAT, temperature=0.7)

        call = mock.get_call(0)

        assert call.prompt == "Test prompt"
        assert call.mode == GenerationMode.CHAT
        assert call.kwargs["temperature"] == 0.7
        assert call.response == "Response"

    def test_echo_strategy_default(self):
        """Test that echo strategy is used by default."""
        mock = MockLLMClient()
        result = mock.generate("Hello")

        assert "Echo: Hello" in result

    def test_custom_strategy(self):
        """Test using a custom response strategy."""

        def custom_callback(prompt, mode, kwargs):
            return f"Custom: {prompt}"

        mock = MockLLMClient(strategy=CallbackResponseStrategy(custom_callback))
        result = mock.generate("Test")

        assert result == "Custom: Test"

    def test_simulated_delay(self):
        """Test that delay is simulated."""
        mock = MockLLMClient(responses=["Response"], simulate_delay=0.1)

        start = time.time()
        mock.generate("Test")
        duration = time.time() - start

        assert duration >= 0.1

    def test_error_injection(self):
        """Test error injection on specific call."""
        mock = MockLLMClient(
            responses=["First"],
            error_on_call=1,
            error_type=ValueError,
            error_message="Test error",
        )

        # First call should succeed
        result = mock.generate("First prompt")
        assert result == "First"

        # Second call should raise error
        with pytest.raises(ValueError, match="Test error"):
            mock.generate("Second prompt")

    def test_assert_called(self):
        """Test assert_called verification."""
        mock = MockLLMClient(responses=["Response"])

        with pytest.raises(AssertionError, match="Mock LLM was never called"):
            mock.assert_called()

        mock.generate("Test")
        mock.assert_called()  # Should not raise

    def test_assert_called_once(self):
        """Test assert_called_once verification."""
        mock = MockLLMClient(responses=["Response 1", "Response 2"])

        mock.generate("Test")
        mock.assert_called_once()  # Should not raise

        mock.generate("Test 2")
        with pytest.raises(AssertionError, match="Expected 1 call, got 2"):
            mock.assert_called_once()

    def test_assert_called_n_times(self):
        """Test assert_called_n_times verification."""
        mock = MockLLMClient(responses=["R1", "R2", "R3"])

        mock.generate("Test 1")
        mock.generate("Test 2")
        mock.generate("Test 3")

        mock.assert_called_n_times(3)  # Should not raise

        with pytest.raises(AssertionError, match="Expected 5 calls, got 3"):
            mock.assert_called_n_times(5)

    def test_assert_called_with(self):
        """Test assert_called_with verification."""
        mock = MockLLMClient(responses=["Response"])
        mock.generate("Test prompt", temperature=0.7, max_tokens=100)

        mock.assert_called_with(prompt="Test prompt")
        mock.assert_called_with(temperature=0.7)
        mock.assert_called_with(prompt="Test prompt", temperature=0.7)

        with pytest.raises(AssertionError):
            mock.assert_called_with(prompt="Wrong prompt")

    def test_assert_any_call_with(self):
        """Test assert_any_call_with verification."""
        mock = MockLLMClient(responses=["R1", "R2", "R3"])

        mock.generate("First", temperature=0.5)
        mock.generate("Second", temperature=0.7)
        mock.generate("Third", temperature=0.9)

        mock.assert_any_call_with(prompt="Second")
        mock.assert_any_call_with(temperature=0.7)
        mock.assert_any_call_with(prompt="Second", temperature=0.7)

        with pytest.raises(AssertionError):
            mock.assert_any_call_with(prompt="Nonexistent")

    def test_get_last_call(self):
        """Test getting the last call record."""
        mock = MockLLMClient(responses=["R1", "R2"])

        with pytest.raises(IndexError, match="No calls have been made"):
            mock.get_last_call()

        mock.generate("First")
        mock.generate("Second")

        last_call = mock.get_last_call()
        assert last_call.prompt == "Second"

    def test_reset(self):
        """Test resetting the mock."""
        mock = MockLLMClient(responses=["R1", "R2"])

        mock.generate("Test 1")
        mock.generate("Test 2")

        assert mock.call_count == 2
        assert len(mock.call_history) == 2

        mock.reset()

        assert mock.call_count == 0
        assert len(mock.call_history) == 0

        # Should be able to use responses again
        assert mock.generate("Test 3") == "R1"

    def test_hooks_are_called(self):
        """Test that hooks are invoked."""
        hook_calls = []

        def test_hook(event, payload):
            hook_calls.append((event, payload))

        mock = MockLLMClient(responses=["Response"], hooks=[test_hook])
        mock.generate("Test")

        assert len(hook_calls) == 2
        assert hook_calls[0][0] == "before_generate"
        assert hook_calls[1][0] == "after_generate"

    def test_structured_response(self):
        """Test with structured LLMResponse."""
        structured_response = ResponseBuilder.structured(content="Test content")

        mock = MockLLMClient(responses=[structured_response])
        result = mock.generate("Test")

        assert isinstance(result, LLMResponse)
        assert result.content == "Test content"

    def test_tool_call_response(self):
        """Test with tool call response."""
        tool_response = ResponseBuilder.tool_call(
            tool_name="get_weather", arguments={"city": "San Francisco"}
        )

        mock = MockLLMClient(responses=[tool_response])
        result = mock.generate("Get weather")

        assert isinstance(result, LLMResponse)
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0]["function"]["name"] == "get_weather"


class TestMockLLMClientAsync:
    """Tests for async functionality of MockLLMClient."""

    @pytest.mark.asyncio
    async def test_async_generation(self):
        """Test async text generation."""
        mock = MockLLMClient(responses=["Async response"])
        result = await mock.generate_async("Test prompt")

        assert result == "Async response"

    @pytest.mark.asyncio
    async def test_async_call_tracking(self):
        """Test that async calls are tracked."""
        mock = MockLLMClient(responses=["Response"])

        await mock.generate_async("Test")

        assert mock.call_count == 1
        assert len(mock.call_history) == 1

    @pytest.mark.asyncio
    async def test_async_simulated_delay(self):
        """Test async delay simulation."""
        mock = MockLLMClient(responses=["Response"], simulate_delay=0.1)

        start = time.time()
        await mock.generate_async("Test")
        duration = time.time() - start

        assert duration >= 0.1

    @pytest.mark.asyncio
    async def test_async_error_injection(self):
        """Test async error injection."""
        mock = MockLLMClient(
            responses=["First"],
            error_on_call=1,
            error_type=RuntimeError,
            error_message="Async error",
        )

        await mock.generate_async("First")

        with pytest.raises(RuntimeError, match="Async error"):
            await mock.generate_async("Second")

    @pytest.mark.asyncio
    async def test_async_hooks(self):
        """Test that async hooks are invoked."""
        hook_calls = []

        def test_hook(event, payload):
            hook_calls.append(event)

        mock = MockLLMClient(responses=["Response"], hooks=[test_hook])
        await mock.generate_async("Test")

        assert "before_generate_async" in hook_calls
        assert "after_generate_async" in hook_calls


class TestMockLLMClientIntegration:
    """Integration tests for MockLLMClient."""

    def test_weather_scenario(self):
        """Test a realistic weather query scenario."""

        def weather_callback(prompt, mode, kwargs):
            prompt_str = str(prompt).lower()
            if "weather" in prompt_str:
                if "san francisco" in prompt_str or "sf" in prompt_str:
                    return ResponseBuilder.json(
                        {
                            "temperature": 72,
                            "condition": "sunny",
                            "city": "San Francisco",
                        }
                    )
                else:
                    return ResponseBuilder.json({"error": "City not found"})
            return "I don't understand the question"

        mock = MockLLMClient(strategy=CallbackResponseStrategy(weather_callback))

        # Test successful query
        result1 = mock.generate("What's the weather in San Francisco?")
        assert "72" in result1
        assert "sunny" in result1

        # Test unknown city
        result2 = mock.generate("What's the weather in Unknown City?")
        assert "error" in result2

        # Test non-weather query
        result3 = mock.generate("What is 2+2?")
        assert "don't understand" in result3

    def test_multi_turn_conversation(self):
        """Test a multi-turn conversation scenario."""
        responses = [
            "Hello! How can I help you?",
            "I can help you with weather information.",
            ResponseBuilder.tool_call("get_weather", {"city": "Boston"}),
            "The weather in Boston is 65°F and cloudy.",
        ]

        mock = MockLLMClient(responses=responses)

        # Turn 1: Greeting
        response1 = mock.generate("Hi")
        assert "Hello" in response1

        # Turn 2: Ask about capabilities
        response2 = mock.generate("What can you do?")
        assert "weather" in response2

        # Turn 3: Request weather (tool call)
        response3 = mock.generate("Get weather for Boston")
        assert isinstance(response3, LLMResponse)
        assert response3.tool_calls[0]["function"]["name"] == "get_weather"

        # Turn 4: Final response
        response4 = mock.generate("Thanks")
        assert "Boston" in response4

        # Verify all calls were tracked
        assert mock.call_count == 4
