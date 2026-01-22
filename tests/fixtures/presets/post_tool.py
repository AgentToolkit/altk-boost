"""Mock presets for post-tool components."""

from tests.fixtures.response_builders import ResponseBuilder
from tests.fixtures.presets.base import BasePresets


class SilentReviewPresets(BasePresets):
    """Presets for Silent Review component testing."""

    SUCCESS = ResponseBuilder.json(
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

    FAILURE = ResponseBuilder.json(
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

    PARTIAL = ResponseBuilder.json(
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


class CodeGenerationPresets(BasePresets):
    """Presets for JSON Processor/Code Generation component."""

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

    PYTHON_PROCESSOR = ResponseBuilder.code_block(
        """import json

def extract_relevant_data(json_data):
    \"\"\"Extract only the relevant fields from large JSON.\"\"\"
    relevant_fields = ['id', 'name', 'status']
    return [{k: item[k] for k in relevant_fields if k in item}
            for item in json_data.get('data', [])]""",
        language="python",
    )


class RAGRepairPresets(BasePresets):
    """Presets for RAG Repair component."""

    SUCCESS = ResponseBuilder.json(
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

    NO_FIX = ResponseBuilder.json(
        {
            "repaired": False,
            "original_call": {"tool": "unknown_tool", "arguments": {}},
            "reason": "No similar tool found in documentation",
            "confidence": 0.1,
        }
    )
