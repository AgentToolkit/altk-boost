from typing import Optional, Any

from altk.pre_tool.core.types import (
    PreToolReflectionRunInput,
    PreToolReflectionRunOutput,
    PreToolReflectionBuildInput,
)
from altk.pre_tool.refraction.src.schemas.results import (
    DebuggingResult,
)
from altk.pre_tool.refraction.src.schemas.mappings import Mapping

try:
    from nestful.schemas.api import Catalog
except ImportError:
    Catalog = None


class RefractionRunInput(PreToolReflectionRunInput):
    """Input for running Refraction reflection."""

    mappings: Optional[list[Mapping]] = None
    memory_objects: Optional[dict[str, Any]] = None
    use_given_operators_only: bool = False


class RefractionBuildInput(PreToolReflectionBuildInput):
    """Input for building Refraction component."""

    tool_specs: list[dict[str, Any]] | Catalog
    top_k: int = 5
    threshold: float = 0.8
    compute_maps: bool = True


class RefractionRunOutput(PreToolReflectionRunOutput):
    """Output from running Refraction reflection."""

    result: Optional[DebuggingResult] = None


__all__ = [
    "RefractionRunInput",
    "RefractionRunOutput",
    "RefractionBuildInput",
]
