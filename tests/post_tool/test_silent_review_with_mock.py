"""Test Silent Review component using MockLLMClient (proof of concept)."""

import pytest
import json
from altk.core.toolkit import AgentPhase, ComponentConfig
from altk.post_tool.core.toolkit import SilentReviewRunInput, Outcome
from altk.post_tool.silent_review.silent_review import SilentReviewForJSONDataComponent


def build_test_input() -> SilentReviewRunInput:
    """Build test input for silent review component."""
    return SilentReviewRunInput(
        messages=[
            {"role": "user", "content": "Tell me the weather"},
            {"role": "assistant", "content": "Calling the weather tool now"},
        ],
        tool_spec={
            "name": "get_weather",
            "description": "Gets weather for a city",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        },
        tool_response={
            "name": "get_weather",
            "result": {"city": "NYC", "temperature": "75F", "condition": "Sunny"},
        },
    )


def test_silent_review_success_with_mock(mock_llm_with_responses, mock_presets):
    """Test silent review with successful outcome using mock LLM."""
    # Arrange
    mock_llm = mock_llm_with_responses([mock_presets.SILENT_REVIEW_SUCCESS])
    config = ComponentConfig(llm_client=mock_llm)
    data = build_test_input()
    middleware = SilentReviewForJSONDataComponent(config=config)

    # Act
    result = middleware.process(data=data, phase=AgentPhase.RUNTIME)

    # Assert
    assert result.outcome == Outcome.ACCOMPLISHED
    assert result.details == json.loads(mock_presets.SILENT_REVIEW_SUCCESS)
    mock_llm.assert_called_once()


def test_silent_review_failure_with_mock(mock_llm_with_responses, mock_presets):
    """Test silent review with failure outcome using mock LLM."""
    # Arrange
    mock_llm = mock_llm_with_responses([mock_presets.SILENT_REVIEW_FAILURE])
    config = ComponentConfig(llm_client=mock_llm)
    data = build_test_input()
    middleware = SilentReviewForJSONDataComponent(config=config)

    # Act
    result = middleware.process(data=data, phase=AgentPhase.RUNTIME)

    # Assert
    assert result.outcome == Outcome.NOT_ACCOMPLISHED
    assert result.details == json.loads(mock_presets.SILENT_REVIEW_FAILURE)
    mock_llm.assert_called_once()


def test_silent_review_partial_with_mock(mock_llm_with_responses, mock_presets):
    """Test silent review with partial outcome using mock LLM."""
    # Arrange
    mock_llm = mock_llm_with_responses([mock_presets.SILENT_REVIEW_PARTIAL])
    config = ComponentConfig(llm_client=mock_llm)
    data = build_test_input()
    middleware = SilentReviewForJSONDataComponent(config=config)

    # Act
    result = middleware.process(data=data, phase=AgentPhase.RUNTIME)

    # Assert
    assert result.outcome == Outcome.PARTIAL_ACCOMPLISH
    assert result.details == json.loads(mock_presets.SILENT_REVIEW_PARTIAL)
    mock_llm.assert_called_once()


def test_silent_review_verifies_prompt_content(mock_llm, mock_presets):
    """Test that silent review passes correct prompt to LLM."""
    # Arrange
    mock_llm.strategy.responses = [mock_presets.SILENT_REVIEW_SUCCESS]
    config = ComponentConfig(llm_client=mock_llm)
    data = build_test_input()
    middleware = SilentReviewForJSONDataComponent(config=config)

    # Act
    middleware.process(data=data, phase=AgentPhase.RUNTIME)

    # Assert
    mock_llm.assert_called_once()
    call = mock_llm.get_last_call()

    # Verify the prompt contains the user's original message
    prompt_str = str(call.prompt)
    assert "Tell me the weather" in prompt_str


@pytest.mark.asyncio
async def test_silent_review_async_with_mock(mock_llm_with_responses, mock_presets):
    """Test async silent review using mock LLM."""
    # Arrange
    mock_llm = mock_llm_with_responses([mock_presets.SILENT_REVIEW_SUCCESS])
    config = ComponentConfig(llm_client=mock_llm)
    data = build_test_input()
    middleware = SilentReviewForJSONDataComponent(config=config)

    # Act
    result = await middleware.aprocess(data=data, phase=AgentPhase.RUNTIME)

    # Assert
    assert result.outcome == Outcome.ACCOMPLISHED
    mock_llm.assert_called_once()


def test_silent_review_with_error_response(mock_llm_with_responses, mock_presets):
    """Test silent review when tool response contains an error."""
    # Arrange
    error_response = mock_llm_with_responses([mock_presets.SILENT_REVIEW_FAILURE])
    config = ComponentConfig(llm_client=error_response)

    # Create input with error in tool response
    data = SilentReviewRunInput(
        messages=[
            {"role": "user", "content": "What's the weather in San Francisco?"},
        ],
        tool_spec={
            "name": "get_weather",
            "description": "Gets weather for a city",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        },
        tool_response={
            "name": "get_weather",
            "result": {"error": "Weather service is under maintenance"},
        },
    )

    middleware = SilentReviewForJSONDataComponent(config=config)

    # Act
    result = middleware.process(data=data, phase=AgentPhase.RUNTIME)

    # Assert
    assert result.outcome == Outcome.NOT_ACCOMPLISHED


def test_silent_review_multiple_calls(mock_llm_with_responses, mock_presets):
    """Test multiple silent review calls with different outcomes."""
    # Arrange
    mock_llm = mock_llm_with_responses(
        [
            mock_presets.SILENT_REVIEW_SUCCESS,
            mock_presets.SILENT_REVIEW_FAILURE,
            mock_presets.SILENT_REVIEW_SUCCESS,
        ]
    )
    config = ComponentConfig(llm_client=mock_llm)
    data = build_test_input()
    middleware = SilentReviewForJSONDataComponent(config=config)

    # Act & Assert
    result1 = middleware.process(data=data, phase=AgentPhase.RUNTIME)
    assert result1.outcome == Outcome.ACCOMPLISHED

    result2 = middleware.process(data=data, phase=AgentPhase.RUNTIME)
    assert result2.outcome == Outcome.NOT_ACCOMPLISHED

    result3 = middleware.process(data=data, phase=AgentPhase.RUNTIME)
    assert result3.outcome == Outcome.ACCOMPLISHED

    # Verify all calls were made
    mock_llm.assert_called_n_times(3)


def test_silent_review_with_component_specific_fixture(mock_llm_for_silent_review):
    """Test using the component-specific fixture."""
    # Arrange
    mock_llm = mock_llm_for_silent_review("success")
    config = ComponentConfig(llm_client=mock_llm)
    data = build_test_input()
    middleware = SilentReviewForJSONDataComponent(config=config)

    # Act
    result = middleware.process(data=data, phase=AgentPhase.RUNTIME)

    # Assert
    assert result.outcome == Outcome.ACCOMPLISHED
    mock_llm.assert_called_once()
