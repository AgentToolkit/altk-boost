from altk.core.toolkit import (
    ComponentBase,
    ComponentInput,
    ComponentOutput,
)
from typing import Union, Dict, List, Optional


class TestCaseGenComponent(ComponentBase):
    pass


class TestCaseGenBuildInput(ComponentInput):
    python_tool_str: str
    test_case_values: Optional[Union[Dict, List[Dict]]] = None


class TestCaseGenBuildOutput(ComponentOutput):
    nl_test_cases: dict
