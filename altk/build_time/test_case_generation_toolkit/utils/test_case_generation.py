from typing import Set
from altk.core.toolkit import AgentPhase
from altk.build_time.test_case_generation_toolkit.core.toolkit import (
    TestCaseGenComponent,
    TestCaseGenBuildInput,
    TestCaseGenBuildOutput,
)
from altk.build_time.test_case_generation_toolkit.src.toolops.generation.test_case_generation.test_case_generation import (
    TestcaseGeneration,
)
from altk.build_time.test_case_generation_toolkit.src.toolops.generation.nl_utterance_generation.nl_utterance_generation import (
    NlUtteranceGeneration,
)
from altk.build_time.test_case_generation_toolkit.src.toolops.toolspec.generate_toolspec import (
    get_toolspec,
)
from altk.build_time.test_case_generation_toolkit.core.config import TestCaseGenConfig


class NLTestCaseGenComponent(TestCaseGenComponent):
    @classmethod
    def supported_phases(cls) -> Set[AgentPhase]:
        return {AgentPhase.BUILDTIME}

    def _build(
        self, data: TestCaseGenBuildInput, config: TestCaseGenConfig
    ) -> TestCaseGenBuildOutput:  # type: ignore
        llm_client = config.llm_client
        tc_generator = TestcaseGeneration(
            llm_client,
            config.gen_mode,
            max_number_testcases_to_generate=config.max_testcases,
            optional_data_scenario=data.test_case_values,
            generate_negative_testcase_flag=config.negative_test_cases,
        )
        nl_generator = NlUtteranceGeneration(
            llm_client, config.gen_mode, max_nl_utterances=config.max_nl_utterances
        )
        _, toolspec = get_toolspec(data.python_tool_str)
        test_cases, _ = tc_generator.testcase_generation_full_pipeline(toolspec)
        nl_test_cases = nl_generator.generate_nl(test_cases)
        return TestCaseGenBuildOutput(nl_test_cases=nl_test_cases)

    def process(
        self, data: TestCaseGenBuildInput, config: TestCaseGenConfig, phase: AgentPhase
    ) -> dict:
        if phase not in self.supported_phases():
            raise ValueError(
                f"{self.__class__.__name__} does not support phase {phase}"
            )

        if phase == AgentPhase.BUILDTIME:
            return self._build(data, config)
