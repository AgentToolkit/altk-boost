"""Mock presets for pre-response components."""

from tests.fixtures.response_builders import ResponseBuilder
from tests.fixtures.presets.base import BasePresets


class PolicyGuardPresets(BasePresets):
    """Presets for Policy Guard component testing."""

    COMPLIANT = ResponseBuilder.json(
        {"compliant": True, "violations": [], "score": 1.0}
    )

    SENSITIVE_DATA_VIOLATION = ResponseBuilder.json(
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

    INAPPROPRIATE_CONTENT = ResponseBuilder.json(
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

    MULTIPLE_VIOLATIONS = ResponseBuilder.json(
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
