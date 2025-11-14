import asyncio
import re
from typing import Set
from altk.pre_tool.toolguard.toolguard.data_types import Domain, ToolPolicyItem
from mellea.backends.types import ModelOption
from altk.pre_tool.toolguard.toolguard.gen_py.prompts.pseudo_code import (
    tool_policy_pseudo_code,
)

MAX_TRIALS = 3


async def tool_dependencies(
    policy_item: ToolPolicyItem, tool_signature: str, domain: Domain, trial=0
) -> Set[str]:
    model_options = {ModelOption.TEMPERATURE: 0.8}
    pseudo_code = await asyncio.to_thread(  # FIXME when melea will support aysnc
        lambda: tool_policy_pseudo_code(
            policy_item=policy_item,
            fn_to_analyze=tool_signature,
            domain=domain,
            model_options=model_options,
        )  # type: ignore
    )
    fn_names = _extract_api_calls(pseudo_code)
    if all([f"{fn_name}(" in domain.app_api.content for fn_name in fn_names]):
        return fn_names
    if trial <= MAX_TRIALS:
        # as tool_policy_pseudo_code has some temerature, we retry hoping next time the pseudo code will be correct
        return await tool_dependencies(policy_item, tool_signature, domain, trial + 1)
    raise Exception("Failed to analyze api dependencies")


def _extract_api_calls(code: str) -> Set[str]:
    pattern = re.compile(r"\bapi\.(\w+)\s*\(")
    return set(pattern.findall(code))
