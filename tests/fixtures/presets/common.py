"""Common mock presets used across multiple components."""

from tests.fixtures.response_builders import ResponseBuilder
from tests.fixtures.presets.base import BasePresets


class ToolCallPresets(BasePresets):
    """Common tool call presets."""

    WEATHER_TOOL_CALL = ResponseBuilder.tool_call(
        tool_name="get_weather", arguments={"city": "San Francisco", "state": "CA"}
    )

    WEATHER_WITH_UNITS = ResponseBuilder.tool_call(
        tool_name="get_weather",
        arguments={"city": "New York", "state": "NY", "units": "fahrenheit"},
    )

    CALCULATOR_TOOL_CALL = ResponseBuilder.tool_call(
        tool_name="calculator", arguments={"operation": "add", "a": 5, "b": 3}
    )

    SEARCH_TOOL_CALL = ResponseBuilder.tool_call(
        tool_name="web_search",
        arguments={"query": "Python programming", "max_results": 10},
    )

    DATABASE_QUERY = ResponseBuilder.tool_call(
        tool_name="query_database",
        arguments={"table": "users", "filter": {"status": "active"}, "limit": 100},
    )

    MULTIPLE_TOOLS = ResponseBuilder.multiple_tool_calls(
        [
            {"name": "get_weather", "arguments": {"city": "San Francisco"}},
            {"name": "get_time", "arguments": {"timezone": "America/Los_Angeles"}},
        ]
    )


class ToolResponsePresets(BasePresets):
    """Common tool response presets."""

    WEATHER_SUCCESS = ResponseBuilder.json(
        {"temperature": 72, "condition": "sunny", "humidity": 45, "wind_speed": 8}
    )

    WEATHER_ERROR = ResponseBuilder.json(
        {"error": "Weather service is under maintenance", "retry_after": 300}
    )

    CALCULATOR_RESULT = ResponseBuilder.json({"result": 8, "operation": "add"})

    SEARCH_RESULTS = ResponseBuilder.json(
        {
            "results": [
                {
                    "title": "Python Tutorial",
                    "url": "https://example.com/1",
                    "snippet": "Learn Python...",
                },
                {
                    "title": "Python Docs",
                    "url": "https://example.com/2",
                    "snippet": "Official docs...",
                },
            ],
            "total": 2,
        }
    )


class GenericPresets(BasePresets):
    """Generic responses for general testing."""

    SIMPLE_SUCCESS = ResponseBuilder.simple("Task completed successfully")
    SIMPLE_FAILURE = ResponseBuilder.simple("Task failed due to an error")
    SIMPLE_ACKNOWLEDGMENT = ResponseBuilder.simple(
        "Understood. I will proceed with the task."
    )
    SIMPLE_CLARIFICATION = ResponseBuilder.simple(
        "I need more information to complete this task. "
        "Could you please provide additional details?"
    )


class ErrorPresets(BasePresets):
    """Common error response presets."""

    RATE_LIMIT = ResponseBuilder.error_response(
        "Rate limit exceeded. Please try again later.", error_type="RateLimitError"
    )

    TIMEOUT = ResponseBuilder.error_response(
        "Request timed out after 30 seconds", error_type="TimeoutError"
    )

    INVALID_INPUT = ResponseBuilder.error_response(
        "Invalid input format", error_type="ValidationError"
    )

    SERVICE_UNAVAILABLE = ResponseBuilder.error_response(
        "Service temporarily unavailable", error_type="ServiceError"
    )


class ConversationPresets(BasePresets):
    """Multi-turn conversation presets."""

    GREETING_SEQUENCE = ResponseBuilder.multi_turn(
        [
            "Hello! How can I assist you today?",
            "I understand you need help with weather information.",
            "Let me fetch that data for you.",
        ]
    )

    TROUBLESHOOTING_SEQUENCE = ResponseBuilder.multi_turn(
        [
            "I see there's an issue with the tool call.",
            "Let me try a different approach.",
            "Success! Here are the results you requested.",
        ]
    )
