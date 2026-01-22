"""Mock presets organized by component and lifecycle stage."""

# Post-tool presets
from tests.fixtures.presets.post_tool import (
    SilentReviewPresets,
    CodeGenerationPresets,
    RAGRepairPresets,
)

# Pre-tool presets
from tests.fixtures.presets.pre_tool import (
    SPARCPresets,
    RefractionPresets,
    ToolGuardPresets,
)

# Pre-response presets
from tests.fixtures.presets.pre_response import PolicyGuardPresets

# Pre-LLM presets
from tests.fixtures.presets.pre_llm import (
    SpotlightPresets,
    RoutingPresets,
)

# Build-time presets
from tests.fixtures.presets.build_time import (
    ToolEnrichmentPresets,
    TestCaseGenerationPresets,
    ToolValidationPresets,
)

# Common presets
from tests.fixtures.presets.common import (
    ToolCallPresets,
    ToolResponsePresets,
    GenericPresets,
    ErrorPresets,
    ConversationPresets,
)

__all__ = [
    # Post-tool
    "SilentReviewPresets",
    "CodeGenerationPresets",
    "RAGRepairPresets",
    # Pre-tool
    "SPARCPresets",
    "RefractionPresets",
    "ToolGuardPresets",
    # Pre-response
    "PolicyGuardPresets",
    # Pre-LLM
    "SpotlightPresets",
    "RoutingPresets",
    # Build-time
    "ToolEnrichmentPresets",
    "TestCaseGenerationPresets",
    "ToolValidationPresets",
    # Common
    "ToolCallPresets",
    "ToolResponsePresets",
    "GenericPresets",
    "ErrorPresets",
    "ConversationPresets",
]
