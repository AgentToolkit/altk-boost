import asyncio
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import cast

import dotenv
import pytest

from altk.pre_tool.toolguard.toolguard_spec_component import (
    ToolGuardSpecBuildInput,
    ToolGuardSpecComponent,
    ToolGuardSpecComponentConfig,
    ToolGuardSpecs,
)
from altk.core.toolkit import AgentPhase
from altk.core.llm.base import get_llm

from .inputs.tool_functions import (
    divide_tool,
    add_tool,
    subtract_tool,
    map_kdi_number,
    multiply_tool,
)

dotenv.load_dotenv()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def out_dir():
    """
    Create a timestamped directory for test output, then delete it after the test.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dir_path = str(Path(__file__).parent / "outputs" / f"work_{timestamp}")

    print("Temporary work dir created:", dir_path)
    yield dir_path

    shutil.rmtree(dir_path)
    print("Temporary work dir removed:", dir_path)


# ---------------------------------------------------------------------------
# Main Test
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_tool_guard_calculator_policy(out_dir: str):
    funcs = [
        divide_tool,
        add_tool,
        multiply_tool,
        subtract_tool,
        map_kdi_number,
    ]

    policy_text = """
        The calculator must not allow division by zero.
        The calculator must not allow multiplication if any of the operands
        correspond to a number whose KDI value equals 6.28.
    """

    # Example alternative LLM:
    # LLMClient = get_llm("litellm.output_val")
    # llm_client = LLMClient(
    #     model_name="gpt-4o-2024-08-06",
    #     custom_llm_provider="azure",
    # )

    LLMClient = get_llm("watsonx.output_val")
    llm_client = LLMClient(
        model_name="mistralai/mistral-medium-2505",
        api_key=os.getenv("WX_API_KEY"),
        project_id=os.getenv("WX_PROJECT_ID"),
        url=os.getenv("WX_URL", "https://us-south.ml.cloud.ibm.com"),
    )

    toolguard_spec = ToolGuardSpecComponent(
        ToolGuardSpecComponentConfig(llm_client=llm_client)
    )

    input_data = ToolGuardSpecBuildInput(
        policy_text=policy_text,
        tools=funcs,
        out_dir=out_dir,
    )

    specs = cast(
        ToolGuardSpecs,
        await toolguard_spec.aprocess(
            data=input_data,
            phase=AgentPhase.BUILDTIME,
        ),
    )

    # Validate number of results
    assert len(specs) == len(funcs)
    specs_by_name = {spec.tool_name: spec for spec in specs}

    # Tools that should have policy items
    expected_tools = ["multiply_tool", "divide_tool"]

    # Tools that should produce no policy items
    empty_tools = ["add_tool", "subtract_tool", "map_kdi_number"]

    # Validate expected tools have populated spec items
    for tool_name in expected_tools:
        spec = specs_by_name[tool_name]

        assert len(spec.policy_items) == 1
        item = spec.policy_items[0]

        assert item.name
        assert item.description
        assert len(item.references) > 0
        assert item.compliance_examples and len(item.compliance_examples) > 1
        assert item.violation_examples and len(item.violation_examples) > 1

    # Validate tools that should be empty
    for tool_name in empty_tools:
        spec = specs_by_name[tool_name]
        assert len(spec.policy_items) == 0


# ---------------------------------------------------------------------------
# Optional: Run test directly (without pytest)
# ---------------------------------------------------------------------------
if __name__ == "__main__":

    async def main():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        work_dir = str(Path(__file__).parent / "outputs" / f"work_{timestamp}")

        print("[main] work dir created:", work_dir)
        await test_tool_guard_calculator_policy(work_dir)
        print("[main] Test completed successfully.")

    asyncio.run(main())
