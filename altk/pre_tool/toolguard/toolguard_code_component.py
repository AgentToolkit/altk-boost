import logging
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Set, cast

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from toolguard.buildtime import (
    ToolGuardsCodeGenerationResult,
    ToolGuardSpec,
    generate_guards_code,
)
from toolguard.runtime import IToolInvoker, PolicyViolationException, load_toolguards

from altk.core.toolkit import AgentPhase, ComponentBase, ComponentConfig, ComponentInput
from altk.pre_tool.toolguard.llm_client import TG_LLMClient
from altk.pre_tool.toolguard.tool_converter import to_tools

logger = logging.getLogger(__name__)


class ToolGuardCodeComponentConfig(ComponentConfig):
    """Configuration for ToolGuardCodeComponent.

    This component enforces policy adherence through code generation and runtime validation.
    It requires an LLM client configuration for generating ToolGuard code from specifications.

    Inherits all configuration from ComponentConfig, including llm_client settings.
    """

    pass


class ToolGuardCodeBuildInput(ComponentInput):
    """Input configuration for building ToolGuard code generation.

    :param tools: List of callable functions, BaseTool instances, or string path to OpenAPI spec
    :param toolguard_specs: List of ToolGuard specifications to generate guards from. results from `toolguard_spec_component` component.
    :param app_name: Name of the application for which guards are being generated. This will be namespace of the guards generated code.
    :param out_dir: Output directory path where generated guard code will be saved
    """

    tools: List[Callable] | List[BaseTool] | str
    toolguard_specs: List[ToolGuardSpec]
    app_name: str
    out_dir: str | Path


ToolGuardBuildOutput = ToolGuardsCodeGenerationResult


class ToolGuardCodeRunInput(ComponentInput):
    """Input configuration for running ToolGuard code validation at runtime.

    A running agent uses this input to check if a tool call complies with the given policy.

    :param generated_guard_dir: Path in the local file system where the generated guard Python code (generated during build time) is located
    :param tool_name: The name of the tool that the agent is about to call
    :param tool_args: A dictionary of the tool call arguments, by the argument name
    :param tool_invoker: A proxy object that enables the guard to call other read-only tools. This is needed when the policy enforcement logic involves getting data from another tool
    """

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
    """Output from ToolGuard code validation at runtime.

    Contains information about policy violations detected during tool call validation.
    If the tool call complies with the policy, the violation field is None.

    :param violation: Populated only if a violation was identified. Contains violation level and user message
    """

    violation: PolicyViolation | None = None


class ToolGuardCodeComponent(ComponentBase):
    """Component for enforcing policy adherence through a two-phase process.

    This component enforces policy adherence through code generation and runtime validation:

    (1) **Buildtime**: Given a set of ToolGuardSpecs, generates policy validation code - ToolGuards.

    (2) **Runtime**: ToolGuards are deployed within the agent's flow, and are triggered before
        agent's tool invocation. They can be deployed into the agent loop, or in an MCP Gateway.
        The ToolGuards check if a planned action complies with the policy.
    """

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
        return await generate_guards_code(
            tools=to_tools(data.tools),
            tool_specs=data.toolguard_specs,
            work_dir=data.out_dir,
            llm=llm,
            app_name=data.app_name,
        )

    def _run(self, data: ToolGuardCodeRunInput) -> ToolGuardCodeRunOutput:
        raise NotImplementedError("Please use the _arun() function in an async context")

    async def _arun(self, data: ToolGuardCodeRunInput) -> ToolGuardCodeRunOutput:
        code_root_dir = data.generated_guard_dir
        tool_name = data.tool_name
        tool_params = data.tool_args
        with load_toolguards(code_root_dir) as toolguards:
            try:
                await toolguards.guard_toolcall(
                    tool_name, tool_params, data.tool_invoker
                )
                return ToolGuardCodeRunOutput()
            except PolicyViolationException as e:
                return ToolGuardCodeRunOutput(
                    violation=PolicyViolation(
                        violation_level=ViolationLevel.ERROR, user_message=str(e)
                    )
                )
