import asyncio
import dotenv


from altk.pre_tool.toolguard.core import (
    ToolGuardBuildInput,
    ToolGuardBuildInputMetaData,
    ToolGuardRunInput,
    ToolGuardRunInputMetaData,
)
from altk.pre_tool.toolguard.pre_tool_guard import PreToolGuardComponent

# Load environment variables
dotenv.load_dotenv()


class ToolGuardExample:
    """
    Runs examples with a ToolGuard component and validates tool invocation against policy.
    """

    def __init__(
        self, tools, workdir, policy_text, validating_llm_client, app_name, short=True
    ):
        self.tools = tools
        self.middleware = PreToolGuardComponent(
            tools=tools, workdir=workdir, app_name=app_name
        )

        build_input = ToolGuardBuildInput(
            metadata=ToolGuardBuildInputMetaData(
                policy_text=policy_text,
                short1=short,
                validating_llm_client=validating_llm_client,
            )
        )
        self.output = asyncio.run(self.middleware._build(build_input))

    def run_example(self, tool_name: str, tool_params: dict):
        """
        Runs a single example through ToolGuard and checks if the result matches the expectation.
        """

        run_input = ToolGuardRunInput(
            metadata=ToolGuardRunInputMetaData(
                tool_name=tool_name,
                tool_parms=tool_params,
            ),
        )

        run_output = self.middleware._run(run_input)
        return run_output
