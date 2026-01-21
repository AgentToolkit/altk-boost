"""Common mock response presets for testing ALTK components."""

from tests.fixtures.response_builders import ResponseBuilder


class MockPresets:
    """Pre-configured mock responses for common testing scenarios."""

    # ==================== Silent Review Presets ====================

    SILENT_REVIEW_SUCCESS = ResponseBuilder.json(
        {
            "relevance": {"score": "high", "reason": "<one line reasoning>"},
            "accuracy": {"score": "high", "reason": "<one line reasoning>"},
            "completeness": {"score": "high", "reason": "<one line reasoning>"},
            "error_handling": {"error_code": "", "error_message": ""},
            "issues_detected": [],
            "suggested_corrections": [],
            "overall_assessment": "Accomplished",
        }
    )

    SILENT_REVIEW_FAILURE = ResponseBuilder.json(
        {
            "relevance": {"score": "low", "reason": "<one line reasoning>"},
            "accuracy": {"score": "low", "reason": "<one line reasoning>"},
            "completeness": {"score": "low", "reason": "<one line reasoning>"},
            "error_handling": {"error_code": "", "error_message": ""},
            "issues_detected": [],
            "suggested_corrections": [],
            "overall_assessment": "Not Accomplished",
        }
    )

    SILENT_REVIEW_PARTIAL = ResponseBuilder.json(
        {
            "relevance": {"score": "medium", "reason": "<one line reasoning>"},
            "accuracy": {"score": "medium", "reason": "<one line reasoning>"},
            "completeness": {"score": "medium", "reason": "<one line reasoning>"},
            "error_handling": {"error_code": "", "error_message": ""},
            "issues_detected": [],
            "suggested_corrections": [],
            "overall_assessment": "Partially Accomplished",
        }
    )

    # ==================== Tool Calling Presets ====================

    WEATHER_TOOL_CALL = ResponseBuilder.tool_call(
        tool_name="get_weather", arguments={"city": "San Francisco", "state": "CA"}
    )

    WEATHER_TOOL_CALL_WITH_UNITS = ResponseBuilder.tool_call(
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

    DATABASE_QUERY_TOOL_CALL = ResponseBuilder.tool_call(
        tool_name="query_database",
        arguments={"table": "users", "filter": {"status": "active"}, "limit": 100},
    )

    MULTIPLE_TOOL_CALLS = ResponseBuilder.multiple_tool_calls(
        [
            {"name": "get_weather", "arguments": {"city": "San Francisco"}},
            {"name": "get_time", "arguments": {"timezone": "America/Los_Angeles"}},
        ]
    )

    # ==================== Tool Response Presets ====================

    WEATHER_RESPONSE_SUCCESS = ResponseBuilder.json(
        {"temperature": 72, "condition": "sunny", "humidity": 45, "wind_speed": 8}
    )

    WEATHER_RESPONSE_ERROR = ResponseBuilder.json(
        {"error": "Weather service is under maintenance", "retry_after": 300}
    )

    CALCULATOR_RESPONSE = ResponseBuilder.json({"result": 8, "operation": "add"})

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

    # ==================== Large JSON Payloads ====================

    LARGE_JSON_RESPONSE = ResponseBuilder.json(
        {
            "data": [
                {"id": i, "value": f"item_{i}", "metadata": {"index": i}}
                for i in range(100)
            ],
            "metadata": {"total": 100, "page": 1, "page_size": 100},
            "timestamp": "2024-01-01T00:00:00Z",
        }
    )

    NESTED_JSON_RESPONSE = ResponseBuilder.json(
        {
            "users": [
                {
                    "id": 1,
                    "name": "Alice",
                    "profile": {
                        "age": 30,
                        "city": "SF",
                        "interests": ["coding", "hiking"],
                    },
                },
                {
                    "id": 2,
                    "name": "Bob",
                    "profile": {
                        "age": 25,
                        "city": "NYC",
                        "interests": ["music", "art"],
                    },
                },
            ],
            "pagination": {"current_page": 1, "total_pages": 10, "items_per_page": 2},
        }
    )

    # ==================== Policy Guard Presets ====================

    POLICY_COMPLIANT = ResponseBuilder.json(
        {"compliant": True, "violations": [], "score": 1.0}
    )

    POLICY_VIOLATION_SENSITIVE_DATA = ResponseBuilder.json(
        {
            "compliant": False,
            "violations": [
                {
                    "type": "sensitive_data",
                    "description": "Response contains PII (email address)",
                    "severity": "high",
                }
            ],
            "score": 0.3,
        }
    )

    POLICY_VIOLATION_INAPPROPRIATE = ResponseBuilder.json(
        {
            "compliant": False,
            "violations": [
                {
                    "type": "inappropriate_content",
                    "description": "Response contains inappropriate language",
                    "severity": "medium",
                }
            ],
            "score": 0.5,
        }
    )

    POLICY_MULTIPLE_VIOLATIONS = ResponseBuilder.json(
        {
            "compliant": False,
            "violations": [
                {
                    "type": "sensitive_data",
                    "description": "Contains SSN",
                    "severity": "critical",
                },
                {
                    "type": "off_topic",
                    "description": "Response is off-topic",
                    "severity": "low",
                },
            ],
            "score": 0.2,
        }
    )

    # ==================== SPARC Presets ====================

    SPARC_VALID_TOOL_CALL = ResponseBuilder.json(
        {
            "valid": True,
            "tool_name": "get_weather",
            "arguments": {"city": "San Francisco"},
            "issues": [],
        }
    )

    SPARC_INVALID_ARGUMENTS = ResponseBuilder.json(
        {
            "valid": False,
            "tool_name": "get_weather",
            "arguments": {"location": "San Francisco"},  # Wrong parameter name
            "issues": [
                {
                    "type": "missing_required_argument",
                    "argument": "city",
                    "message": "Required argument 'city' is missing",
                }
            ],
        }
    )

    SPARC_HALLUCINATED_TOOL = ResponseBuilder.json(
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

    # ==================== Refraction Presets ====================

    REFRACTION_VALID_SEQUENCE = ResponseBuilder.json(
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

    REFRACTION_SYNTAX_ERROR = ResponseBuilder.json(
        {
            "valid": False,
            "sequence": [{"tool": "invalid_json", "arguments": "not a dict"}],
            "issues": [
                {"type": "syntax_error", "message": "Arguments must be a dictionary"}
            ],
        }
    )

    # ==================== RAG Repair Presets ====================

    RAG_REPAIR_SUCCESS = ResponseBuilder.json(
        {
            "repaired": True,
            "original_call": {"tool": "get_weather", "arguments": {"location": "SF"}},
            "repaired_call": {
                "tool": "get_weather",
                "arguments": {"city": "San Francisco", "state": "CA"},
            },
            "confidence": 0.95,
        }
    )

    RAG_REPAIR_NO_FIX = ResponseBuilder.json(
        {
            "repaired": False,
            "original_call": {"tool": "unknown_tool", "arguments": {}},
            "reason": "No similar tool found in documentation",
            "confidence": 0.1,
        }
    )

    # ==================== Spotlight Presets ====================

    SPOTLIGHT_RESPONSE = ResponseBuilder.simple(
        "Based on the emphasized instructions, I will focus on the key requirements and provide a detailed response."
    )

    # ==================== Tool Enrichment Presets ====================

    TOOL_ENRICHMENT_DESCRIPTION = ResponseBuilder.json(
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

    # ==================== Test Case Generation Presets ====================

    TEST_CASE_GENERATION = ResponseBuilder.json(
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

    # ==================== Generic Responses ====================

    SIMPLE_SUCCESS = ResponseBuilder.simple("Task completed successfully")

    SIMPLE_FAILURE = ResponseBuilder.simple("Task failed due to an error")

    SIMPLE_ACKNOWLEDGMENT = ResponseBuilder.simple(
        "Understood. I will proceed with the task."
    )

    SIMPLE_CLARIFICATION = ResponseBuilder.simple(
        "I need more information to complete this task. Could you please provide additional details?"
    )

    # ==================== Error Responses ====================

    ERROR_RATE_LIMIT = ResponseBuilder.error_response(
        "Rate limit exceeded. Please try again later.", error_type="RateLimitError"
    )

    ERROR_TIMEOUT = ResponseBuilder.error_response(
        "Request timed out after 30 seconds", error_type="TimeoutError"
    )

    ERROR_INVALID_INPUT = ResponseBuilder.error_response(
        "Invalid input format", error_type="ValidationError"
    )

    ERROR_SERVICE_UNAVAILABLE = ResponseBuilder.error_response(
        "Service temporarily unavailable", error_type="ServiceError"
    )

    # ==================== Code Generation Presets ====================

    CODE_GENERATION_PYTHON = ResponseBuilder.code_block(
        """def process_data(data):
    \"\"\"Process the input data and return results.\"\"\"
    results = []
    for item in data:
        if item['status'] == 'active':
            results.append(item)
    return results""",
        language="python",
    )

    CODE_GENERATION_JSON_PROCESSOR = ResponseBuilder.code_block(
        """import json

def extract_relevant_data(json_data):
    \"\"\"Extract only the relevant fields from large JSON.\"\"\"
    relevant_fields = ['id', 'name', 'status']
    return [{k: item[k] for k in relevant_fields if k in item}
            for item in json_data.get('data', [])]""",
        language="python",
    )

    # ==================== Multi-turn Conversation Presets ====================

    MULTI_TURN_GREETING = ResponseBuilder.multi_turn(
        [
            "Hello! How can I assist you today?",
            "I understand you need help with weather information.",
            "Let me fetch that data for you.",
        ]
    )

    MULTI_TURN_TROUBLESHOOTING = ResponseBuilder.multi_turn(
        [
            "I see there's an issue with the tool call.",
            "Let me try a different approach.",
            "Success! Here are the results you requested.",
        ]
    )
