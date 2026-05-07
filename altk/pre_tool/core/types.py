from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

from altk.core.toolkit import ComponentInput, ComponentOutput


class SPARCReflectionDecision(str, Enum):
    """Decision made by the reflection pipeline."""

    APPROVE = "approve"
    REJECT = "reject"
    ERROR = "error"


class SPARCReflectionIssueType(str, Enum):
    """Types of issues that can be identified by reflection."""

    STATIC = "static"
    SEMANTIC_GENERAL = "semantic_general"
    SEMANTIC_FUNCTION = "semantic_function"
    SEMANTIC_PARAMETER = "semantic_parameter"
    TRANSFORM = "transform"
    ERROR = "error"


class SPARCRecommendationTarget(str, Enum):
    """Artifact a recommendation is meant to be applied to."""

    SYSTEM_PROMPT = "system_prompt"
    TOOL_DESCRIPTION = "tool_description"
    PARAMETER_DESCRIPTION = "parameter_description"
    PARAMETER_EXAMPLES = "parameter_examples"


class SPARCRecommendation(BaseModel):
    """Actionable recommendation for improving an agent's prompts or tool specs.

    Emitted ONLY in evaluation-time mode (``runtime_pipeline=False``).
    Runtime mode omits recommendations to keep prompts short and latency low.
    """

    target: SPARCRecommendationTarget = Field(
        description="Which artifact the diff applies to.",
    )
    tool_name: Optional[str] = Field(
        default=None,
        description=(
            "Required when target is TOOL_DESCRIPTION, PARAMETER_DESCRIPTION, "
            "or PARAMETER_EXAMPLES; None for SYSTEM_PROMPT."
        ),
    )
    parameter_name: Optional[str] = Field(
        default=None,
        description=(
            "Required when target is PARAMETER_DESCRIPTION or "
            "PARAMETER_EXAMPLES; None otherwise."
        ),
    )
    diff: str = Field(
        description=(
            "Unified git-diff-format patch of the proposed change. "
            "Example: '--- a/system_prompt\\n+++ b/system_prompt\\n@@\\n"
            "-old line\\n+new line'."
        ),
    )
    rationale: str = Field(
        description="Brief reason why this change addresses the observed issue.",
    )
    importance: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "How impactful this recommendation is at preventing similar "
            "issues (0=cosmetic, 1=critical)."
        ),
    )


class SPARCReflectionIssue(BaseModel):
    """Represents an issue identified during reflection."""

    issue_type: SPARCReflectionIssueType
    metric_name: str
    explanation: str
    correction: Optional[Dict[str, Any]] = None
    # Per-metric rubric rating (integer 1-5) for semantic metrics; None for
    # static/transform/error issues that don't produce a rubric output.
    output_value: Optional[float] = Field(
        default=None,
        description=(
            "Raw rubric rating returned by the metric's LLM judge (int 1-5 for "
            "semantic metrics). None for static / transform / error issues."
        ),
    )
    # Model's self-reported confidence in its judgment, in [0, 1].
    confidence: Optional[float] = Field(
        default=None,
        description="Model-reported confidence in the assessment (0.0-1.0).",
    )
    # Recommendations returned by the metric's LLM judge (evaluation-time
    # mode only). Empty list in runtime mode.
    recommendations: List[SPARCRecommendation] = Field(
        default_factory=list,
        description=(
            "Actionable recommendations emitted by this metric's evaluation-"
            "time prompt. Empty in runtime_pipeline=True mode."
        ),
    )


class SPARCReflectionResult(BaseModel):
    """Result of reflecting on a single tool call."""

    decision: SPARCReflectionDecision
    issues: List[SPARCReflectionIssue] = Field(default_factory=list)
    # Aggregated rubric score across all semantic metrics that produced a
    # rating (mean of output_value's). Scale: 1-5 (same as per-metric). ``None``
    # when no semantic metric ran (e.g. static-only or transform-only track).
    score: Optional[float] = Field(
        default=None,
        description=(
            "Aggregated 1-5 rubric score: mean of the per-metric output_value "
            "ratings across every semantic metric that produced a rating. "
            "None if no semantic metrics contributed a rating."
        ),
    )
    # Flat view of every recommendation emitted across all issues — handy
    # for downstream CLEAR aggregation which rolls up by tool / system
    # prompt. Empty in runtime_pipeline=True mode.
    all_recommendations: List[SPARCRecommendation] = Field(
        default_factory=list,
        description=(
            "Flat list of every SPARCRecommendation emitted by any metric "
            "in this reflection. Empty in runtime_pipeline=True mode."
        ),
    )

    @property
    def has_issues(self) -> bool:
        """Check if any issues were found."""
        return len(self.issues) > 0

    @property
    def approved(self) -> bool:
        """Boolean convenience form of the APPROVE decision."""
        return self.decision == SPARCReflectionDecision.APPROVE

    @property
    def normalized_score(self) -> Optional[float]:
        """``score`` mapped from 1-5 into 0.0-1.0 (None when ``score`` is None)."""
        if self.score is None:
            return None
        return max(0.0, min(1.0, (self.score - 1.0) / 4.0))


class PreToolReflectionRunInput(ComponentInput):
    tool_specs: list[dict[str, Any]] = Field(
        description="List of available tool specifications"
    )
    tool_calls: list[dict[str, Any]] = Field(
        description="List of tool calls to reflect upon"
    )


class PreToolReflectionRunOutput(ComponentOutput):
    pass


class PreToolReflectionBuildInput(ComponentInput):
    pass


class PreToolReflectionBuildOutput(ComponentOutput):
    pass


class SPARCReflectionRunInput(PreToolReflectionRunInput):
    """Input for running SPARC reflection."""

    pass


class SPARCReflectionRunOutputSchema(BaseModel):
    """Output from SPARC reflection."""

    reflection_result: SPARCReflectionResult
    execution_time_ms: float
    raw_pipeline_result: Optional[Dict[str, Any]] = None

    def should_proceed_with_tool_call(self) -> bool:
        """Determine if the tool call should proceed based on reflection."""
        return self.reflection_result.decision == SPARCReflectionDecision.APPROVE


class SPARCReflectionRunOutput(PreToolReflectionRunOutput):
    """Output for running SPARC reflection."""

    output: SPARCReflectionRunOutputSchema = Field(
        default_factory=lambda: SPARCReflectionRunOutputSchema()
    )
