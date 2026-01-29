"""Utility module for converting various tool formats to ToolGuard TOOLS type."""

from typing import Callable, List, cast
from langchain_core.tools import BaseTool
from toolguard.buildtime import TOOLS
from toolguard.buildtime.buildtime import OpenAPI
from toolguard.extra.langchain_to_oas import langchain_tools_to_openapi


def to_tools(tools: List[Callable] | List[BaseTool] | str) -> TOOLS:
    """Convert various tool formats to the TOOLS type expected by ToolGuard.

    Args:
        tools: Either a string path to an OpenAPI specification file,
            a list of callable functions, or a list of BaseTool instances.

    Returns:
        TOOLS: The converted tools in the format expected by ToolGuard.
            This can be either a list of callables or an OpenAPI specification dict.

    Raises:
        ValueError: If the tools input is invalid or cannot be converted.
            This includes invalid OpenAPI spec files, mixed tool types in lists,
            or unsupported input types.
    """
    if isinstance(tools, str):
        try:
            return OpenAPI.load_from(tools).model_dump()
        except Exception as e:
            raise ValueError(f"Invalid OpenAPI spec file: {e}") from e

    elif isinstance(tools, list):
        if all(isinstance(tool, Callable) for tool in tools):
            return cast(List[Callable], tools)
        elif all(isinstance(tool, BaseTool) for tool in tools):
            return langchain_tools_to_openapi(cast(List[BaseTool], tools))
        else:
            raise ValueError("Invalid tools list")

    raise ValueError("Invalid tools input")
