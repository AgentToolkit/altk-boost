import logging
import os
from pathlib import Path
from typing import Callable, List, Set, cast
from langchain_core.tools import BaseTool
from pydantic import Field

from altk.pre_tool.toolguard.llm_client import TG_LLMClient
from altk.pre_tool.toolguard.tool_converter import to_tools

from altk.core.toolkit import AgentPhase, ComponentBase, ComponentConfig, ComponentInput
from toolguard.buildtime import ToolGuardSpec, generate_guard_specs

logger = logging.getLogger(__name__)


class ToolGuardSpecComponentConfig(ComponentConfig):
    """Configuration for ToolGuardSpecComponent.

    This component generates ToolGuard specifications from policy documents and tool definitions.
    It requires an LLM client configuration for analyzing policies and generating guard specifications.

    Inherits all configuration from ComponentConfig, including llm_client settings.
    """

    pass


class ToolGuardSpecBuildInput(ComponentInput):
    """Input data for building ToolGuard specifications.

    Attributes:
        policy_text: Text of the policy document file that defines the constraints
            and rules for tool usage.
        tools: List of callable functions, BaseTool instances, or a string path
            to OpenAPI tool specification that will be analyzed against the policy.
        out_dir: Output directory path where generated guard specifications will be saved.
    """

    policy_text: str = Field(description="Text of the policy document file")
    tools: List[Callable] | List[BaseTool] | str
    out_dir: str | Path


ToolGuardSpecs = List[ToolGuardSpec]


class ToolGuardSpecComponent(ComponentBase):
    """Component for generating ToolGuard specifications from policy documents.

    This component analyzes policy documents and tool definitions to generate
    ToolGuard specifications that define constraints and validation rules.
    It operates in the buildtime phase to create specifications that can later
    be used to generate executable guard code.

    The component uses an LLM to interpret policy text and map it to specific
    tool parameters and constraints, producing structured ToolGuardSpec objects.
    """

    def __init__(self, config: ToolGuardSpecComponentConfig):
        super().__init__(config=config)

    @classmethod
    def supported_phases(cls) -> Set[AgentPhase]:
        return {AgentPhase.BUILDTIME, AgentPhase.RUNTIME}

    def _build(self, data: ToolGuardSpecBuildInput) -> ToolGuardSpecs:
        raise NotImplementedError(
            "Please use the aprocess() function in an async context"
        )

    async def _abuild(self, data: ToolGuardSpecBuildInput) -> ToolGuardSpecs:
        os.makedirs(data.out_dir, exist_ok=True)
        config = cast(ToolGuardSpecComponentConfig, self.config)
        llm = TG_LLMClient(config.llm_client)
        return await generate_guard_specs(
            policy_text=data.policy_text,
            tools=to_tools(data.tools),
            work_dir=data.out_dir,
            llm=llm,
            short=True,
        )
