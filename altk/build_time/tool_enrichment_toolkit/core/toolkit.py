from altk.core.toolkit import (
    ComponentBase,
    ComponentInput,
    ComponentOutput,
)
from typing import Any


class ToolEnrichComponent(ComponentBase):
    pass


class PythonToolEnrichBuildInput(ComponentInput):
    python_tool: str


class PythonToolEnrichBuildOutput(ComponentOutput):
    enriched_python_tool: str


class MCPCFToolEnrichBuildInput(ComponentInput):
    mcp_cf_toolspec: dict[str, Any]


class MCPCFToolEnrichBuildOutput(ComponentOutput):
    mcp_cf_toolspec: dict[str, Any]
