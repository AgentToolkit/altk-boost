"""Mock presets for pre-tool components."""

from tests.fixtures.response_builders import ResponseBuilder
from tests.fixtures.presets.base import BasePresets


class SPARCPresets(BasePresets):
    """Presets for SPARC component testing."""

    VALID_TOOL_CALL = ResponseBuilder.json(
        {
            "valid": True,
            "tool_name": "get_weather",
            "arguments": {"city": "San Francisco"},
            "issues": [],
        }
    )

    INVALID_ARGUMENTS = ResponseBuilder.json(
        {
            "valid": False,
            "tool_name": "get_weather",
            "arguments": {"location": "San Francisco"},  # Wrong parameter
            "issues": [
                {
                    "type": "missing_required_argument",
                    "argument": "city",
                    "message": "Required argument 'city' is missing",
                }
            ],
        }
    )

    HALLUCINATED_TOOL = ResponseBuilder.json(
        {
            "valid": False,
            "tool_name": "get_stock_price",  # Tool doesn't exist
            "arguments": {"symbol": "AAPL"},
            "issues": [
                {
                    "type": "unknown_tool",
                    "message": "Tool 'get_stock_price' is not available",
                }
            ],
        }
    )


class RefractionPresets(BasePresets):
    """Presets for Refraction component testing."""

    VALID_SEQUENCE = ResponseBuilder.json(
        {
            "valid": True,
            "sequence": [
                {"tool": "search_database", "arguments": {"query": "user data"}},
                {
                    "tool": "process_results",
                    "arguments": {"data": "{{previous_result}}"},
                },
            ],
            "issues": [],
        }
    )

    SYNTAX_ERROR = ResponseBuilder.json(
        {
            "valid": False,
            "sequence": [{"tool": "invalid_json", "arguments": "not a dict"}],
            "issues": [
                {"type": "syntax_error", "message": "Arguments must be a dictionary"}
            ],
        }
    )


class ToolGuardPresets(BasePresets):
    """Presets for ToolGuard component testing."""

    POLICY_COMPLIANT = ResponseBuilder.json(
        {
            "compliant": True,
            "violations": [],
            "tool_call": {"tool": "get_weather", "arguments": {"city": "SF"}},
        }
    )

    POLICY_VIOLATION = ResponseBuilder.json(
        {
            "compliant": False,
            "violations": [
                {
                    "type": "unauthorized_access",
                    "message": "Tool attempts to access restricted resource",
                    "severity": "high",
                }
            ],
            "tool_call": {"tool": "delete_user", "arguments": {"user_id": "admin"}},
        }
    )
