import asyncio
import json
import logging
import os
from os.path import join
from typing import Callable, List, Literal, Optional, cast

import mellea

import altk.pre_tool.toolguard.toolguard.gen_py.consts as consts
from altk.pre_tool.toolguard.toolguard.gen_py.domain_from_funcs import (
    generate_domain_from_functions,
)
from altk.pre_tool.toolguard.toolguard.data_types import RuntimeDomain, ToolPolicy
from altk.pre_tool.toolguard.toolguard.gen_py.domain_from_openapi import (
    generate_domain_from_openapi,
)
from altk.pre_tool.toolguard.toolguard.runtime import ToolGuardsCodeGenerationResult
from altk.pre_tool.toolguard.toolguard.gen_py.tool_guard_generator import (
    ToolGuardGenerator,
)
import altk.pre_tool.toolguard.toolguard.gen_py.utils.pytest as pytest
import altk.pre_tool.toolguard.toolguard.gen_py.utils.venv as venv
import altk.pre_tool.toolguard.toolguard.gen_py.utils.pyright as pyright
from altk.pre_tool.toolguard.toolguard.common.py import unwrap_fn

logger = logging.getLogger(__name__)

ENV_GENPY_BACKEND_NAME = "TOOLGUARD_GENPY_BACKEND_NAME"
ENV_GENPY_MODEL_ID = "TOOLGUARD_GENPY_MODEL_ID"
ENV_GENPY_ARGS = "TOOLGUARD_GENPY_ARGS"


async def generate_toolguards_from_functions(
    app_name: str,
    tool_policies: List[ToolPolicy],
    py_root: str,
    funcs: List[Callable],
    module_roots: Optional[List[str]] = None,
) -> ToolGuardsCodeGenerationResult:
    assert funcs, "Funcs cannot be empty"
    logger.debug(f"Starting... will save into {py_root}")

    if not module_roots:
        if len(funcs) > 0:
            module_roots = list(
                {unwrap_fn(func).__module__.split(".")[0] for func in funcs}
            )
    assert module_roots

    # Domain from functions
    domain = generate_domain_from_functions(py_root, app_name, funcs, module_roots)
    return await generate_toolguards_from_domain(
        app_name, tool_policies, py_root, domain
    )


async def generate_toolguards_from_openapi(
    app_name: str, tool_policies: List[ToolPolicy], py_root: str, openapi_file: str
) -> ToolGuardsCodeGenerationResult:
    logger.debug(f"Starting... will save into {py_root}")

    # Domain from OpenAPI
    domain = generate_domain_from_openapi(py_root, app_name, openapi_file)
    return await generate_toolguards_from_domain(
        app_name, tool_policies, py_root, domain
    )


def start_melea_session() -> mellea.MelleaSession:
    backend_name = cast(
        Literal["ollama", "hf", "openai", "watsonx", "litellm"],
        os.getenv(ENV_GENPY_BACKEND_NAME, "openai"),
    )

    model_id = os.getenv(ENV_GENPY_MODEL_ID)
    assert model_id, f"'{ENV_GENPY_MODEL_ID}' environment variable not set"

    kw_args_val = os.getenv(ENV_GENPY_ARGS)
    kw_args = {}
    if kw_args_val:
        try:
            kw_args = json.loads(kw_args_val)
        except Exception as e:
            logger.warning(
                f"Failed to parse {ENV_GENPY_ARGS}: {e}. Using empty dict instead."
            )

    print(kw_args)

    return mellea.start_session(backend_name=backend_name, model_id=model_id, **kw_args)


async def generate_toolguards_from_domain(
    app_name: str, tool_policies: List[ToolPolicy], py_root: str, domain: RuntimeDomain
) -> ToolGuardsCodeGenerationResult:
    # Setup env
    venv.run(join(py_root, consts.PY_ENV), consts.PY_PACKAGES)
    pyright.config(py_root)
    pytest.configure(py_root)

    with start_melea_session():
        # tools
        tools_w_poilicies = [
            tool_policy
            for tool_policy in tool_policies
            if len(tool_policy.policy_items) > 0
        ]
        tool_results = await asyncio.gather(
            *[
                ToolGuardGenerator(
                    app_name, tool_policy, py_root, domain, consts.PY_ENV
                ).generate()
                for tool_policy in tools_w_poilicies
            ]
        )

    tools_result = {
        tool.tool_name: res for tool, res in zip(tools_w_poilicies, tool_results)
    }
    return ToolGuardsCodeGenerationResult(
        root_dir=py_root, domain=domain, tools=tools_result
    ).save(py_root)
