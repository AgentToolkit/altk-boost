import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, cast
from enum import Enum
from pydantic import BaseModel, Field
from typing import Set
from langchain_core.tools import BaseTool

from altk.core.toolkit import ComponentConfig, ComponentInput, AgentPhase, ComponentBase
from toolguard.buildtime import (
    generate_guards_from_specs,
    ToolGuardSpec,
    ToolGuardsCodeGenerationResult,
)
from toolguard.runtime import IToolInvoker, load_toolguards, PolicyViolationException

from altk.pre_tool.toolguard.llm_client import TG_LLMClient

logger = logging.getLogger(__name__)


class ToolGuardCodeComponentConfig(ComponentConfig):
    pass


class ToolGuardCodeBuildInput(ComponentInput):
    tools: List[Callable] | List[BaseTool] | str
    toolguard_specs: List[ToolGuardSpec]
    out_dir: str | Path


ToolGuardBuildOutput = ToolGuardsCodeGenerationResult


class ToolGuardCodeRunInput(ComponentInput):
    generated_guard_dir: str | Path
    tool_name: str = Field(description="Tool name")
    tool_args: Dict[str, Any] = Field(default={}, description="Tool arguments")
    tool_invoker: IToolInvoker

    model_config = {"arbitrary_types_allowed": True}


class ViolationLevel(Enum):
    """Severity level of a safety violation.

    :cvar INFO: Informational level violation that does not require action
    :cvar WARN: Warning level violation that suggests caution but allows continuation
    :cvar ERROR: Error level violation that requires blocking or intervention
    """

    INFO = "info"
    WARN = "warn"
    ERROR = "error"


class PolicyViolation(BaseModel):
    """Details of a safety violation detected by content moderation.

    :param violation_level: Severity level of the violation
    :param user_message: (Optional) Message to convey to the user about the violation
    """

    violation_level: ViolationLevel

    # what message should you convey to the user
    user_message: str | None = None


class ToolGuardCodeRunOutput(BaseModel):
    violation: PolicyViolation | None = None


class ToolGuardCodeComponent(ComponentBase):
    def __init__(self, config: ToolGuardCodeComponentConfig):
        super().__init__(config=config)

    @classmethod
    def supported_phases(cls) -> Set[AgentPhase]:
        """Return the supported agent phases."""
        return {AgentPhase.BUILDTIME, AgentPhase.RUNTIME}

    def _build(self, data: ToolGuardCodeBuildInput) -> ToolGuardsCodeGenerationResult:
        raise NotImplementedError(
            "Please use the aprocess() function in an async context"
        )

    async def _abuild(
        self, data: ToolGuardCodeBuildInput
    ) -> ToolGuardsCodeGenerationResult:
        config = cast(ToolGuardCodeComponentConfig, self.config)
        llm = TG_LLMClient(config.llm_client)
        return await generate_guards_from_specs(
            tools=data.tools,
            tool_specs=data.toolguard_specs,
            work_dir=data.out_dir,
            llm=llm,
        )

    def _run(self, data: ToolGuardCodeRunInput) -> ToolGuardCodeRunOutput:
        code_root_dir = data.generated_guard_dir
        tool_name = data.tool_name
        tool_params = data.tool_args
        with load_toolguards(code_root_dir) as toolguards:
            try:
                toolguards.check_toolcall(tool_name, tool_params, data.tool_invoker)
                return ToolGuardCodeRunOutput()
            except PolicyViolationException as e:
                return ToolGuardCodeRunOutput(
                    violation=PolicyViolation(
                        violation_level=ViolationLevel.ERROR, user_message=str(e)
                    )
                )

    def _arun(self, data: ToolGuardCodeRunInput) -> ToolGuardCodeRunOutput:
        return self._run(data)
