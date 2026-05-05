from typing import (
    Any,
    Dict,
    List,
    Literal,
)

from altk.pre_tool.sparc.function_calling.pipeline.types import (
    ToolCall,
    ToolSpec,
)


CompactMode = Literal["auto", "never", "always"]
"""Compact tool-inventory rendering mode.

- ``"auto"`` (default): use compact form (description + parameter name list only)
  whenever the inventory has ``>= compact_threshold`` tools, otherwise full
  summary (description + {param_name: type}). Helps when the function-selection
  prompt would otherwise balloon past the context window.
- ``"never"``: always use full summary (description + {param_name: type}).
- ``"always"``: always use compact form regardless of tool count.
"""


# ────────────────────────────────────────────────────────────────────────────────
# Adapter definitions
# ────────────────────────────────────────────────────────────────────────────────


class BaseAdapter:
    """Abstract adapter to unify different API spec and call representations."""

    def get_tools_inventory(self) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def get_tools_inventory_summary(self) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def get_tool_spec(self, tool_name: str) -> Dict[str, Any]:
        raise NotImplementedError

    def get_call_dict(self) -> Dict[str, Any]:
        raise NotImplementedError

    def get_function_name(self) -> str:
        raise NotImplementedError

    def get_parameters(self) -> Dict[str, Any]:
        raise NotImplementedError

    def get_param_spec_snippet(self, param_name: str) -> Dict[str, Any]:
        raise NotImplementedError


class OpenAIAdapter(BaseAdapter):
    """Adapter for ToolSpec + ToolCall inputs.

    Args:
        specs: the full tool inventory for the current turn.
        call: the tool call being judged.
        compact_tool_schema: how to render the function-selection inventory.
            ``"auto"`` (default) falls back to the compact form once the
            inventory has ``>= compact_tool_threshold`` tools so the prompt
            stays tractable when hundreds of tools are available. Single-tool
            prompts (``get_tool_spec``) and the full dump (``get_tools_inventory``)
            are unaffected.
        compact_tool_threshold: tool-count threshold for ``"auto"`` mode
            (default 20, matching SPARCReflectionConfig default).
    """

    def __init__(
        self,
        specs: List[ToolSpec],
        call: ToolCall,
        compact_tool_schema: CompactMode = "auto",
        compact_tool_threshold: int = 20,
    ):
        self.specs = specs
        self.call = call
        self.compact_tool_schema: CompactMode = compact_tool_schema
        self.compact_tool_threshold = compact_tool_threshold

    def _use_compact_summary(self) -> bool:
        if self.compact_tool_schema == "always":
            return True
        if self.compact_tool_schema == "never":
            return False
        return len(self.specs) >= self.compact_tool_threshold

    def get_tools_inventory(self) -> List[Dict[str, Any]]:
        return [spec.model_dump() for spec in self.specs]

    def get_tools_inventory_summary(self) -> List[Dict[str, Any]]:
        # Compact form: tool_description + parameter name list only.
        # Drops type annotations to save tokens when many tools are present.
        if self._use_compact_summary():
            return [
                {
                    "tool_name": spec.function.name,
                    "tool_description": spec.function.description,
                    "tool_parameters": list(
                        spec.function.parameters.get("properties", {}).keys()
                    ),
                }
                for spec in self.specs
            ]
        return [
            {
                "tool_name": spec.function.name,
                "tool_description": spec.function.description,
                "tool_parameters": {
                    prop_name: prop_d.get("type", "object")
                    for prop_name, prop_d in spec.function.parameters.get(
                        "properties", {}
                    ).items()
                },
            }
            for spec in self.specs
        ]

    def get_tool_spec(self, tool_name: str) -> Dict[str, Any]:
        tool = next((t for t in self.specs if t.function.name == tool_name), None)
        return tool.function.model_dump() if tool else {}

    def get_call_dict(self) -> Dict[str, Any]:
        call_dict = {
            "id": self.call.id,
            "type": "function",
            "function": {
                "name": self.call.function.name,
                "arguments": self.call.function.arguments,
            },
        }
        return call_dict

    def get_function_name(self) -> str:
        return self.call.function.name

    def get_parameters(self) -> Dict[str, Any]:
        return self.call.function.parsed_arguments

    def get_param_spec_snippet(self, param_name: str) -> Dict[str, Any]:
        spec = next(
            (s for s in self.specs if s.function.name == self.get_function_name()), None
        )
        if not spec:
            return {"type": "object", "properties": {}, "required": []}
        props = spec.function.parameters.get("properties", spec.function.parameters)
        if param_name not in props:
            return {"type": "object", "properties": {}, "required": []}
        return {
            "type": "object",
            "properties": {param_name: props[param_name]},
            "required": [param_name],
        }
