from typing import Set
from altk.core.toolkit import AgentPhase
from altk.build_time.tool_validation_toolkit.core.toolkit import (
    ToolValidationComponent,
    ToolValidationInput,
    ToolValidationOutput,
)
from altk.build_time.tool_validation_toolkit.core.config import ToolValidationConfig
from altk.build_time.test_case_generation_toolkit.src.toolops.validation.test_case_execution.run_execution import (
    ToolNLTestCaseExecution,
)
from altk.build_time.test_case_generation_toolkit.src.toolops.validation.tool_analysis.run_analysis import (
    ErrorAnalysis,
)


class PythonToolValidationComponent(ToolValidationComponent):
    @classmethod
    def supported_phases(cls) -> Set[AgentPhase]:
        return {AgentPhase.RUNTIME}

    def _run(
        self, data: ToolValidationInput, config: ToolValidationConfig
    ) -> ToolValidationOutput:  # type: ignore
        tool_test_cases_with_execution = ToolNLTestCaseExecution(
            data.agent_with_tools
        ).run_tool_nl_test_cases(data.tool_test_cases, data.python_tool_name)
        tool_error_analysis = ErrorAnalysis(
            data.python_tool_name, tool_test_cases_with_execution
        )
        tool_test_report = tool_error_analysis.get_tool_report(config.report_level)
        return ToolValidationOutput(test_report=tool_test_report)

    def process(
        self, data: ToolValidationInput, config: ToolValidationConfig, phase: AgentPhase
    ) -> dict:
        if phase not in self.supported_phases():
            raise ValueError(
                f"{self.__class__.__name__} does not support phase {phase}"
            )

        if phase == AgentPhase.RUNTIME:
            return self._run(data, config)
