import logging
import os
from pathlib import Path
from typing import Callable, List, Set, cast
from langchain_core.tools import BaseTool
from pydantic import Field

from altk.pre_tool.toolguard.llm_client import TG_LLMClient

from ...core.toolkit import AgentPhase, ComponentBase, ComponentConfig, ComponentInput
from toolguard.buildtime import ToolGuardSpec, generate_guard_specs

logger = logging.getLogger(__name__)


class ToolGuardSpecComponentConfig(ComponentConfig):
    pass


class ToolGuardSpecBuildInput(ComponentInput):
    policy_text: str = Field(description="Text of the policy document file")
    tools: List[Callable] | List[BaseTool] | str
    out_dir: str | Path


ToolGuardSpecs = List[ToolGuardSpec]


class ToolGuardSpecComponent(ComponentBase):
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
            tools=data.tools,
            work_dir=data.out_dir,
            llm=llm,
            short=True,
        )
