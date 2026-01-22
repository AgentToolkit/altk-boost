"""Pytest configuration and fixtures for ALTK tests."""

import pytest
from typing import List, Union

from tests.fixtures.mock_llm import (
    MockLLMClient,
    EchoResponseStrategy,
    CallbackResponseStrategy,
)
from tests.fixtures.presets import (
    SilentReviewPresets,
    PolicyGuardPresets,
    ToolCallPresets,
)
from tests.fixtures.response_builders import ResponseBuilder
from altk.core.llm.types import LLMResponse


@pytest.fixture
def mock_llm():
    """
    Basic mock LLM client with echo strategy.

    Returns a MockLLMClient that echoes prompts back.
    Useful for basic testing where response content doesn't matter.

    Example:
        def test_component(mock_llm):
            result = mock_llm.generate("Test prompt")
            assert "Test prompt" in result
    """
    return MockLLMClient()


@pytest.fixture
def mock_llm_with_responses():
    """
    Factory fixture for creating mock LLM with specific responses.

    Returns a function that creates a MockLLMClient with predefined responses.

    Example:
        def test_component(mock_llm_with_responses):
            mock = mock_llm_with_responses(["Response 1", "Response 2"])
            assert mock.generate("Prompt 1") == "Response 1"
            assert mock.generate("Prompt 2") == "Response 2"
    """

    def _create(responses: List[Union[str, LLMResponse]]) -> MockLLMClient:
        return MockLLMClient(responses=responses)

    return _create


@pytest.fixture
def mock_llm_echo():
    """
    Mock LLM that echoes prompts back with a prefix.

    Useful for debugging and verifying that prompts are being passed correctly.

    Example:
        def test_prompt_formatting(mock_llm_echo):
            result = mock_llm_echo.generate("Hello")
            assert result == "Echo: Hello"
    """
    return MockLLMClient(strategy=EchoResponseStrategy())


@pytest.fixture
def mock_llm_with_delay():
    """
    Mock LLM with simulated latency.

    Useful for testing timeout handling and async behavior.

    Example:
        def test_timeout(mock_llm_with_delay):
            import time
            start = time.time()
            mock_llm_with_delay.generate("Test")
            duration = time.time() - start
            assert duration >= 0.1
    """
    return MockLLMClient(simulate_delay=0.1)


@pytest.fixture
def mock_llm_with_error():
    """
    Mock LLM that raises error on second call.

    Useful for testing error handling and retry logic.

    Example:
        def test_error_handling(mock_llm_with_error):
            mock_llm_with_error.generate("First")  # Succeeds
            with pytest.raises(RuntimeError):
                mock_llm_with_error.generate("Second")  # Fails
    """
    return MockLLMClient(
        responses=["First response"],
        error_on_call=1,
        error_type=RuntimeError,
        error_message="Simulated API error",
    )


@pytest.fixture
def mock_llm_custom():
    """
    Factory fixture for creating mock LLM with custom callback.

    Returns a function that creates a MockLLMClient with custom response logic.

    Example:
        def test_custom_logic(mock_llm_custom):
            def custom_response(prompt, mode, kwargs):
                if "weather" in str(prompt).lower():
                    return '{"temperature": 72}'
                return "I don't understand"

            mock = mock_llm_custom(custom_response)
            result = mock.generate("What's the weather?")
            assert "temperature" in result
    """

    def _create(callback) -> MockLLMClient:
        return MockLLMClient(strategy=CallbackResponseStrategy(callback))

    return _create


# Note: mock_presets fixture removed - import specific preset classes instead
# Example: from tests.fixtures.presets import SilentReviewPresets, PolicyGuardPresets


@pytest.fixture
def response_builder():
    """
    Access to ResponseBuilder utilities.

    Provides helper methods for building various types of responses.

    Example:
        def test_tool_call(mock_llm_with_responses, response_builder):
            tool_response = response_builder.tool_call(
                "get_weather",
                {"city": "SF"}
            )
            mock = mock_llm_with_responses([tool_response])
            result = mock.generate("Get weather")
            assert result.tool_calls[0]["function"]["name"] == "get_weather"
    """
    return ResponseBuilder


# Component-specific fixtures


@pytest.fixture
def mock_llm_for_silent_review(mock_llm_with_responses):
    """
    Pre-configured mock for Silent Review component testing.

    Example:
        def test_silent_review_success(mock_llm_for_silent_review):
            mock = mock_llm_for_silent_review("success")
            # Use mock with SilentReviewComponent
    """

    def _create(outcome: str = "success") -> MockLLMClient:
        if outcome == "success":
            return mock_llm_with_responses([SilentReviewPresets.SUCCESS])
        elif outcome == "failure":
            return mock_llm_with_responses([SilentReviewPresets.FAILURE])
        elif outcome == "partial":
            return mock_llm_with_responses([SilentReviewPresets.PARTIAL])
        else:
            raise ValueError(f"Unknown outcome: {outcome}")

    return _create


@pytest.fixture
def mock_llm_for_policy_guard(mock_llm_with_responses):
    """
    Pre-configured mock for Policy Guard component testing.

    Example:
        def test_policy_guard_compliant(mock_llm_for_policy_guard):
            mock = mock_llm_for_policy_guard("compliant")
            # Use mock with PolicyGuardComponent
    """

    def _create(compliance: str = "compliant") -> MockLLMClient:
        if compliance == "compliant":
            return mock_llm_with_responses([PolicyGuardPresets.COMPLIANT])
        elif compliance == "sensitive_data":
            return mock_llm_with_responses(
                [PolicyGuardPresets.SENSITIVE_DATA_VIOLATION]
            )
        elif compliance == "inappropriate":
            return mock_llm_with_responses([PolicyGuardPresets.INAPPROPRIATE_CONTENT])
        elif compliance == "multiple":
            return mock_llm_with_responses([PolicyGuardPresets.MULTIPLE_VIOLATIONS])
        else:
            raise ValueError(f"Unknown compliance: {compliance}")

    return _create


@pytest.fixture
def mock_llm_for_tool_calling(mock_llm_with_responses):
    """
    Pre-configured mock for tool calling tests.

    Example:
        def test_weather_tool(mock_llm_for_tool_calling):
            mock = mock_llm_for_tool_calling("weather")
            result = mock.generate("Get weather")
            assert result.tool_calls[0]["function"]["name"] == "get_weather"
    """

    def _create(tool: str = "weather") -> MockLLMClient:
        tool_map = {
            "weather": ToolCallPresets.WEATHER_TOOL_CALL,
            "calculator": ToolCallPresets.CALCULATOR_TOOL_CALL,
            "search": ToolCallPresets.SEARCH_TOOL_CALL,
            "database": ToolCallPresets.DATABASE_QUERY,
            "multiple": ToolCallPresets.MULTIPLE_TOOLS,
        }
        if tool not in tool_map:
            raise ValueError(f"Unknown tool: {tool}")
        return mock_llm_with_responses([tool_map[tool]])

    return _create


# Async fixtures


@pytest.fixture
async def async_mock_llm():
    """
    Async version of mock_llm fixture.

    Example:
        @pytest.mark.asyncio
        async def test_async_component(async_mock_llm):
            result = await async_mock_llm.generate_async("Test")
            assert "Echo" in result
    """
    return MockLLMClient()


@pytest.fixture
async def async_mock_llm_with_responses():
    """
    Async factory fixture for creating mock LLM with specific responses.

    Example:
        @pytest.mark.asyncio
        async def test_async_component(async_mock_llm_with_responses):
            mock = async_mock_llm_with_responses(["Response 1"])
            result = await mock.generate_async("Test")
            assert result == "Response 1"
    """

    def _create(responses: List[Union[str, LLMResponse]]) -> MockLLMClient:
        return MockLLMClient(responses=responses)

    return _create
