import os
from os.path import join
from typing import Callable, List, Optional

import json
import logging

from altk.pre_tool.toolguard.toolguard.gen_py.gen_toolguards import (
    generate_toolguards_from_openapi,
    generate_toolguards_from_functions,
)
from altk.pre_tool.toolguard.toolguard.llm.i_tg_llm import I_TG_LLM
from altk.pre_tool.toolguard.toolguard.runtime import ToolGuardsCodeGenerationResult
from altk.pre_tool.toolguard.toolguard.data_types import ToolPolicy, load_tool_policy
from altk.pre_tool.toolguard.toolguard.tool_policy_extractor.create_oas_summary import (
    OASSummarizer,
)
from altk.pre_tool.toolguard.toolguard.tool_policy_extractor.text_tool_policy_generator import (
    ToolInfo,
    extract_policies,
)


logger = logging.getLogger(__name__)


async def build_toolguards(
    policy_text: str,
    tools: List[Callable] | str,
    step1_out_dir: str,
    step2_out_dir: str,
    step1_llm: I_TG_LLM,
    app_name: str = "my_app",
    tools2run: List[str] | None = None,
    short1=True,
) -> ToolGuardsCodeGenerationResult:
    if isinstance(tools, list):  # supports list of functions or list of langgraph tools
        tools_info = [ToolInfo.from_function(tool) for tool in tools]
        tool_policies = await extract_policies(
            policy_text, tools_info, step1_out_dir, step1_llm, tools2run, short1
        )
        return await generate_guards_from_tool_policies(
            tools, tool_policies, step2_out_dir, app_name, None, tools2run
        )

    if isinstance(tools, str):  # Backward compatibility to support OpenAPI specs
        oas_path = tools
        with open(oas_path, "r", encoding="utf-8") as file:
            oas = json.load(file)
        summarizer = OASSummarizer(oas)
        tools_info = summarizer.summarize()
        tool_policies = await extract_policies(
            policy_text, tools_info, step1_out_dir, step1_llm, tools2run, short1
        )
        return await generate_guards_from_tool_policies_oas(
            oas_path, tool_policies, step2_out_dir, app_name, tools2run
        )

    raise ValueError("Unknown tools")


async def generate_guards_from_tool_policies(
    funcs: List[Callable],
    tool_policies: List[ToolPolicy],
    to_step2_path: str,
    app_name: str,
    lib_names: Optional[List[str]] = None,
    tool_names: Optional[List[str]] = None,
) -> ToolGuardsCodeGenerationResult:
    os.makedirs(to_step2_path, exist_ok=True)

    tool_policies = [
        policy
        for policy in tool_policies
        if (not tool_names) or (policy.tool_name in tool_names)
    ]
    return await generate_toolguards_from_functions(
        app_name, tool_policies, to_step2_path, funcs=funcs, module_roots=lib_names
    )


async def generate_guards_from_tool_policies_oas(
    oas_path: str,
    tool_policies: List[ToolPolicy],
    to_step2_path: str,
    app_name: str,
    tool_names: Optional[List[str]] = None,
) -> ToolGuardsCodeGenerationResult:
    os.makedirs(to_step2_path, exist_ok=True)

    tool_policies = [
        policy
        for policy in tool_policies
        if (not tool_names) or (policy.tool_name in tool_names)
    ]
    return await generate_toolguards_from_openapi(
        app_name, tool_policies, to_step2_path, oas_path
    )


def load_policies_in_folder(
    folder: str,
) -> List[ToolPolicy]:
    files = [
        f
        for f in os.listdir(folder)
        if os.path.isfile(join(folder, f)) and f.endswith(".json")
    ]
    tool_policies = []
    for file in files:
        tool_name = file[: -len(".json")]
        policy = load_tool_policy(join(folder, file), tool_name)
        if policy.policy_items:
            tool_policies.append(policy)
    return tool_policies
