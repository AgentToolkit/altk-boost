import asyncio
import os
from typing import List, Dict

import dotenv
import markdown

from altk.pre_tool.toolguard.examples.calculator_example.example_tools import (
    divide_tool,
)
from altk.pre_tool.toolguard.toolguard.llm.tg_llmevalkit import TG_LLMEval
from altk.pre_tool.toolguard.toolguard.tool_policy_extractor.text_tool_policy_generator import (
    ToolInfo,
    extract_policies,
)
from altk.pre_tool.toolguard.toolguard.core import (
    generate_guards_from_tool_policies,
)

from altk.core.llm import get_llm


class FullAgent:
    def __init__(
        self,
        app_name,
        tools,
        workdir,
        policy_doc_path,
        llm_model="gpt-4o-2024-08-06",
        tools2run: List[str] | None = None,
        short1=False,
    ):
        self.model = llm_model
        self.tools = tools
        self.workdir = workdir
        self.policy_doc = open(policy_doc_path, "r", encoding="utf-8").read()
        self.policy_doc = markdown.markdown(self.policy_doc)
        self.tools2run = tools2run
        self.short1 = short1
        self.app_name = app_name
        self.step1_out_dir = os.path.join(self.workdir, "step1")
        self.step2_out_dir = os.path.join(self.workdir, "step2")
        # self.tool_registry = {tool.name: tool for tool in tools}
        self.tool_registry = {tool.__name__: tool for tool in tools}

    async def build_time(self):
        OPENAILiteLLMClientOutputVal = get_llm("litellm.output_val")
        validating_llm_client = OPENAILiteLLMClientOutputVal(
            model_name="watsonx/gpt-4o-2024-08-06",
            custom_llm_provider="azure",
        )
        llm = TG_LLMEval(validating_llm_client)
        tools_info = [ToolInfo.from_function(tool) for tool in self.tools]

        tool_policies = await extract_policies(
            self.policy_doc, tools_info, self.step1_out_dir, llm, short=True
        )
        self.gen_result = await generate_guards_from_tool_policies(
            self.tools,
            tool_policies,
            to_step2_path=self.step2_out_dir,
            app_name=self.app_name,
        )

    def guard_tool(self, tool_name: str, tool_params: Dict) -> str:
        print("validate_tool_node")
        import sys

        code_root_dir = self.gen_result.root_dir
        sys.path.insert(0, code_root_dir)
        from rt_toolguard import load_toolguards

        toolguards = load_toolguards(code_root_dir)

        try:
            # app_guards.check_tool_call(tool_name, tool_parms, state["messages"])
            toolguards.check_toolcall(
                tool_name, tool_params, list(self.tool_registry.values())
            )
            print("ok to invoke tool")
        except Exception as e:
            error_message = (
                "it is against the policy to invoke tool: "
                + tool_name
                + " Error: "
                + str(e)
            )
            print(error_message)


if __name__ == "__main__":
    dotenv.load_dotenv()
    work_dir = "examples/calculator_example/output"
    policy_doc_path = "examples/calculator_example/policy_document.md"
    policy_doc_path = os.path.abspath(policy_doc_path)
    work_dir = os.path.abspath(work_dir)

    tools = [divide_tool]  # [add_tool, subtract_tool, multiply_tool, divide_tool]
    fa = FullAgent(
        "calculator",
        tools,
        work_dir,
        policy_doc_path,
        llm_model="gpt-4o-2024-08-06",
        short1=True,
    )
    asyncio.run(fa.build_time())
    fa.guard_tool("divide_tool", {"g": 5, "h": 0})
    fa.guard_tool("divide_tool", {"g": 5, "h": 4})
