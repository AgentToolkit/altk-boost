import json
import logging
import os
from typing import Set


from altk.pre_tool.toolguard.toolguard.core import (
    generate_guards_from_tool_policies,
)
from altk.pre_tool.toolguard.toolguard.llm.tg_llmevalkit import TG_LLMEval
from altk.pre_tool.toolguard.toolguard.runtime import ToolFunctionsInvoker
from altk.pre_tool.toolguard.toolguard.tool_policy_extractor.text_tool_policy_generator import (
    ToolInfo,
    extract_policies,
)

from altk.core.toolkit import AgentPhase, ComponentBase


from altk.pre_tool.toolguard.core.types import (
    ToolGuardBuildInput,
    ToolGuardRunInput,
    ToolGuardRunOutput,
    ToolGuardRunOutputMetaData,
    ToolGuardBuildOutput,
    ToolGuardBuildOutputMetaData,
)

logger = logging.getLogger(__name__)


class PreToolGuardComponent(ComponentBase):
    def __init__(self, tools, workdir, app_name):
        super().__init__()
        self._tools = tools
        self._tool_registry = {tool.__name__: tool for tool in self._tools}
        self._workdir = workdir
        self._step1_dir = os.path.join(self._workdir, "Step_1")
        self._step2_dir = os.path.join(self._workdir, "Step_2")
        self._app_name = app_name
        self._tool_policies = None
        self._gen_result = None

    @classmethod
    def supported_phases(cls) -> Set[AgentPhase]:
        """Return the supported agent phases."""
        return {AgentPhase.BUILDTIME, AgentPhase.RUNTIME}

    async def _build(self, data: ToolGuardBuildInput) -> ToolGuardBuildOutput:
        llm = TG_LLMEval(data.metadata.validating_llm_client)
        tools_info = [ToolInfo.from_function(tool) for tool in self._tools]

        self._tool_policies = await extract_policies(
            data.metadata.policy_text, tools_info, self._step1_dir, llm, short=True
        )
        self._gen_result = await generate_guards_from_tool_policies(
            self._tools,
            self._tool_policies,
            to_step2_path=self._step2_dir,
            app_name=self._app_name,
        )
        output = ToolGuardBuildOutputMetaData(
            tool_policies=self._tool_policies, generated_code_object=self._gen_result
        )
        return ToolGuardBuildOutput(output=output)

    def _run(self, data: ToolGuardRunInput) -> ToolGuardRunOutput:
        import sys

        code_root_dir = self._gen_result.root_dir
        sys.path.insert(0, code_root_dir)
        tool_name = data.metadata.tool_name
        tool_params = data.metadata.tool_parms
        from rt_toolguard import load_toolguards

        app_guards = load_toolguards(code_root_dir)

        try:
            app_guards.check_toolcall(
                tool_name,
                tool_params,
                ToolFunctionsInvoker(list(self._tool_registry.values())),
            )
            error_message = False
        except Exception as e:
            error_message = (
                f"It is against the policy to invoke tool: {tool_name}({json.dumps(tool_params)}) Error: "
                + str(e)
            )
        output = ToolGuardRunOutputMetaData(error_message=error_message)
        return ToolGuardRunOutput(output=output)
