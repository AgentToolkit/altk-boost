from pydantic import Field
from altk.core.toolkit import ComponentConfig


class ToolValidationConfig(ComponentConfig):
    """Configuration for the Tool Validation Middleware."""

    report_level: str = Field(
        default="detailed",
        description="Tool validation report level , accepted values - detailed , short",
    )

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        extra = "forbid"
