import json
from altk.build_time.test_case_generation_toolkit.src.toolops.generation.nl_utterance_generation.nl_utterance_generation_utils import (
    nlg_util,
)

import time
import logging

logger = logging.getLogger(
    "toolops.generation.nl_utterance_generation.nl_utterance_generation"
)


# parent_dir = os.path.dirname(os.path.join(os.getcwd(),"src"))
# sys.path.append(parent_dir)
class NlUtteranceGeneration:
    def __init__(
        self, client, gen_mode, clean_nl_utterances=False, max_nl_utterances=3
    ):
        self.clean_nl_utterances = clean_nl_utterances
        self.max_nl_utterances = max_nl_utterances
        self.client = client
        self.gen_mode = gen_mode

    def generate_nl(self, test_scenarios):
        logger.info(
            "NL utterance generation started with the following params: ",
            extra={
                "details": json.dumps(
                    {
                        "clean_nl_utterances": self.clean_nl_utterances,
                        "max_no_of_nl_utterances_per_testcase": self.max_nl_utterances,
                    }
                )
            },
        )
        try:
            test_scenarios["llm_model_details"]["nlg-model-id"] = self.client.model_name
        except Exception:
            test_scenarios["llm_model_details"]["nlg-model-id"] = None
        test_scenarios["llm_platform_details"]["nlg-platform"] = None
        tool_definition = test_scenarios["tool_definition"]
        # print('Tool Definition: ', tool_definition)
        for parameter in test_scenarios["Test_scenarios"]:
            # print('Input parameters: ', parameter['input_parameters'])
            nl_query = nlg_util.get_nl_query(
                tool_definition,
                parameter["input_parameters"],
            )
            refined_nl_query = nlg_util.rephrase_nl_query(
                nl_query,
                tool_definition,
                parameter["input_parameters"],
                self.client,
                self.gen_mode,
                self.clean_nl_utterances,
                self.max_nl_utterances,
            )
            parameter["nl_utterance"] = refined_nl_query
            # print('NL Utterance: ', refined_nl_query)
        logger.info(
            "NL utterance generation completed: ",
            extra={"details": json.dumps({"end_time": str(time.time())})},
        )

        return test_scenarios
