from altk.core.toolkit import (
    ComponentBase,
    ComponentInput,
    ComponentOutput,
)
from typing import List, Dict, Any


class ToolValidationComponent(ComponentBase):
    pass


# from langgraph.prebuilt import create_react_agent
class ToolValidationInput(ComponentInput):
    python_tool_name: str
    tool_test_cases: List[dict]
    agent_with_tools: Any


class ToolValidationOutput(ComponentOutput):
    test_report: Dict
