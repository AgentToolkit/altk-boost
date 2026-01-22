"""Mock presets for build-time components."""

from tests.fixtures.response_builders import ResponseBuilder
from tests.fixtures.presets.base import BasePresets


class ToolEnrichmentPresets(BasePresets):
    """Presets for Tool Enrichment component testing."""

    ENRICHED_DESCRIPTION = ResponseBuilder.json(
        {
            "tool_name": "get_weather",
            "description": "Retrieves current weather information for a specified location",
            "parameters": {
                "city": {
                    "type": "string",
                    "description": "The name of the city to get weather for",
                    "required": True,
                },
                "state": {
                    "type": "string",
                    "description": "The state or province (optional for international cities)",
                    "required": False,
                },
                "units": {
                    "type": "string",
                    "description": "Temperature units: 'celsius' or 'fahrenheit'",
                    "required": False,
                    "default": "fahrenheit",
                },
            },
            "returns": {
                "type": "object",
                "description": "Weather data including temperature, condition, humidity, and wind speed",
            },
        }
    )


class TestCaseGenerationPresets(BasePresets):
    """Presets for Test Case Generation component testing."""

    GENERATED_TEST_CASES = ResponseBuilder.json(
        {
            "test_cases": [
                {
                    "utterance": "What's the weather like in San Francisco?",
                    "expected_tool": "get_weather",
                    "expected_arguments": {"city": "San Francisco", "state": "CA"},
                },
                {
                    "utterance": "Tell me the temperature in New York",
                    "expected_tool": "get_weather",
                    "expected_arguments": {"city": "New York", "state": "NY"},
                },
                {
                    "utterance": "Is it raining in Seattle?",
                    "expected_tool": "get_weather",
                    "expected_arguments": {"city": "Seattle", "state": "WA"},
                },
            ]
        }
    )


class ToolValidationPresets(BasePresets):
    """Presets for Tool Validation component testing."""

    VALIDATION_SUCCESS = ResponseBuilder.json(
        {
            "valid": True,
            "tool_name": "get_weather",
            "test_cases_passed": 10,
            "test_cases_failed": 0,
            "issues": [],
        }
    )

    VALIDATION_FAILURE = ResponseBuilder.json(
        {
            "valid": False,
            "tool_name": "get_weather",
            "test_cases_passed": 7,
            "test_cases_failed": 3,
            "issues": [
                {
                    "test_case": "What's the weather?",
                    "error": "Missing required argument: city",
                }
            ],
        }
    )
