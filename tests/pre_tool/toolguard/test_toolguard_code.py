"""
End-to-end test for ToolGuard code generation & runtime evaluation
using a set of arithmetic tools.

This test:
1. Loads tool policies
2. Generates guard code
3. Runs the guards in runtime mode
4. Verifies correct functionality and violations
"""

from datetime import datetime
import os
from pathlib import Path
import shutil
from typing import Dict, cast
import asyncio
import dotenv
import pytest

from altk.core.llm.base import BaseLLMClient
from altk.pre_tool.toolguard import (
    ToolGuardCodeComponent,
    ToolGuardCodeBuildInput,
    ToolGuardSpec,
)
from toolguard.runtime import ToolFunctionsInvoker, ToolGuardsCodeGenerationResult
from altk.pre_tool.toolguard.toolguard_code_component import (
    ToolGuardCodeComponentConfig,
    ToolGuardCodeRunInput,
    ToolGuardCodeRunOutput,
    ViolationLevel,
)
from altk.core.toolkit import AgentPhase

# The calculator tools under test
from .inputs.tool_functions import (
    divide_tool,
    add_tool,
    multiply_tool,
    subtract_tool,
    map_kdi_number,
)

# Load environment variables
dotenv.load_dotenv()

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def work_dir():
    """Creates a temporary folder for test output and cleans it afterward."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dir_path = Path(__file__).parent / "outputs" / f"work_{timestamp}"
    print("Temporary work dir created:", dir_path)

    yield dir_path

    shutil.rmtree(dir_path)
    # print("Temporary work dir removed:", dir_path)


def get_llm() -> BaseLLMClient:
    from altk.core.llm.providers.ibm_watsonx_ai.ibm_watsonx_ai import WatsonxLLMClient

    return WatsonxLLMClient(
        model_name="meta-llama/llama-4-maverick-17b-128e-instruct-fp8",
        api_key=os.getenv("WX_API_KEY"),
        project_id=os.getenv("WX_PROJECT_ID"),
        url=os.getenv("WX_URL"),
    )

    # from altk.core.llm.providers.openai.openai import AsyncAzureOpenAIClient
    # return AsyncAzureOpenAIClient(
    #     model="gpt-4o-2024-08-06",
    #     api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    #     azure_endpoint=os.getenv("AZURE_API_BASE"),
    #     api_version="2024-08-01-preview"
    # )

    # from altk.core.llm.providers.litellm.litellm import LiteLLMClient
    # return LiteLLMClient(
    #     model_name=os.getenv("TOOLGUARD_GENPY_MODEL_ID"),
    #     api_key=os.getenv("TOOLGUARD_GENPY_MODEL_API_KEY"),
    #     base_url=os.getenv("TOOLGUARD_GENPY_MODEL_BASE_URL"),
    # )

    # from altk.core.llm.providers.openai.openai import AsyncOpenAIClient
    # return AsyncOpenAIClient(
    #     model=os.getenv("TOOLGUARD_GENPY_MODEL_ID"),
    #     api_key=os.getenv("TOOLGUARD_GENPY_MODEL_API_KEY"),
    #     url=os.getenv("TOOLGUARD_GENPY_MODEL_BASE_URL"),
    # )

    # from altk.core.llm.providers.openai.openai import AsyncOpenAIClientOutputVal
    # return AsyncOpenAIClientOutputVal(
    #     model=os.getenv("TOOLGUARD_GENPY_MODEL_ID"),
    #     api_key=os.getenv("TOOLGUARD_GENPY_MODEL_API_KEY"),
    #     url=os.getenv("TOOLGUARD_GENPY_MODEL_BASE_URL"),
    # )


# ---------------------------------------------------------------------------
# Test: ToolGuard verification for the calculator tool set
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tool_guard_calculator_policy(work_dir: str):
    # Tools to be guarded
    funcs = [divide_tool, add_tool, multiply_tool, subtract_tool, map_kdi_number]

    # Build ToolGuard component
    toolguard_code = ToolGuardCodeComponent(
        ToolGuardCodeComponentConfig(llm_client=get_llm())
    )

    # Load policy JSON files from /step1
    policy_dir = Path(__file__).parent / "inputs" / "step1"
    specs = [ToolGuardSpec.load(policy_dir / f"{tool.__name__}.json") for tool in funcs]

    # Prepare build input for guard code generation
    build_input = ToolGuardCodeBuildInput(
        tools=funcs, out_dir=work_dir, toolguard_specs=specs, app_name="calc"
    )

    # Toolguarg code generation
    build_output = cast(
        ToolGuardsCodeGenerationResult,
        await toolguard_code.aprocess(build_input, AgentPhase.BUILDTIME),
    )
    # build_output = load_toolguard_code_result("tests/pre_tool/toolguard/outputs/work_XXX")

    # Expected guarded tools
    expected_tools = ["multiply_tool", "divide_tool", "add_tool"]

    # Basic structure assertions
    assert build_output.out_dir
    assert build_output.domain
    assert len(build_output.tools) == len(expected_tools)

    # Validate guard components for each tool
    for tool_name in expected_tools:
        result = build_output.tools[tool_name]

        assert len(result.tool.policy_items) == 1
        assert result.guard_fn_name
        assert result.guard_file
        assert len(result.item_guard_files) == 1
        assert result.item_guard_files[0].content  # Generated guard code
        assert len(result.test_files) == 1
        assert result.test_files[0].content

    # -----------------------------------------------------------------------
    # Runtime Testing
    # -----------------------------------------------------------------------

    tool_invoker = ToolFunctionsInvoker(funcs)

    async def call(tool_name: str, args: Dict) -> ToolGuardCodeRunOutput:
        """Executes a tool through its guard code."""
        return cast(
            ToolGuardCodeRunOutput,
            await toolguard_code.aprocess(
                ToolGuardCodeRunInput(
                    generated_guard_dir=build_output.out_dir,
                    tool_name=tool_name,
                    tool_args=args,
                    tool_invoker=tool_invoker,
                ),
                AgentPhase.RUNTIME,
            ),
        )

    async def assert_complies(tool_name: str, args: Dict):
        """Asserts that no violation occurs."""
        assert (await call(tool_name, args)).violation is None

    async def assert_violates(tool_name: str, args: Dict):
        """Asserts that a violation occurs with level ERROR."""
        res = await call(tool_name, args)
        assert res.violation
        assert res.violation.violation_level == ViolationLevel.ERROR
        assert res.violation.user_message

    await asyncio.gather(
        *[
            # Valid input cases -----------------------------------------------------
            assert_complies("divide_tool", {"g": 5, "h": 4}),
            assert_complies("add_tool", {"a": 5, "b": 4}),
            assert_complies("subtract_tool", {"a": 5, "b": 4}),
            assert_complies("multiply_tool", {"a": 5, "b": 4}),
            assert_complies("map_kdi_number", {"i": 5}),
            # Violation cases -------------------------------------------------------
            assert_violates("divide_tool", {"g": 5, "h": 0}),
            assert_violates("add_tool", {"a": 5, "b": 73}),
            assert_violates("add_tool", {"a": 73, "b": 5}),
            # Violations for multiply_tool based on custom rules
            assert_violates("multiply_tool", {"a": 2, "b": 73}),
            assert_violates("multiply_tool", {"a": 22, "b": 2}),
        ]
    )


# ---------------------------------------------------------------------------
# Optional: Main entry point for directly running the test without pytest
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import asyncio

    async def main():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        work_dir = str(Path(__file__).parent / "outputs" / f"work_{timestamp}")
        print("[main] work dir created:", work_dir)

        # Call the async test function directly
        await test_tool_guard_calculator_policy(work_dir)
        print("[main] Test completed successfully.")

    asyncio.run(main())
