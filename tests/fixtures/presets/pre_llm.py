"""Mock presets for pre-LLM components."""

from tests.fixtures.response_builders import ResponseBuilder
from tests.fixtures.presets.base import BasePresets


class SpotlightPresets(BasePresets):
    """Presets for Spotlight component testing."""

    EMPHASIZED_RESPONSE = ResponseBuilder.simple(
        "Based on the emphasized instructions, I will focus on the key "
        "requirements and provide a detailed response."
    )

    STANDARD_RESPONSE = ResponseBuilder.simple(
        "I will process your request and provide a response."
    )


class RoutingPresets(BasePresets):
    """Presets for Routing/RAT component testing."""

    TOOL_HINT_WEATHER = ResponseBuilder.json(
        {
            "suggested_tool": "get_weather",
            "confidence": 0.95,
            "reasoning": "User query mentions weather information for a location",
        }
    )

    TOOL_HINT_CALCULATOR = ResponseBuilder.json(
        {
            "suggested_tool": "calculator",
            "confidence": 0.88,
            "reasoning": "User query involves mathematical calculation",
        }
    )

    NO_CLEAR_TOOL = ResponseBuilder.json(
        {
            "suggested_tool": None,
            "confidence": 0.3,
            "reasoning": "Query is ambiguous or doesn't match available tools",
        }
    )
