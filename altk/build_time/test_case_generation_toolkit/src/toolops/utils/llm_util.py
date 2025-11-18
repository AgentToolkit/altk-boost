import os
import json
import logging
from altk.core.llm.types import GenerationArgs

logger = logging.getLogger("toolops.utils.llm_util")
pwd = os.getcwd()


def execute_prompt(
    prompt,
    client,
    gen_mode,
    parameters=None,
    max_new_tokens=600,
    stop_sequences=None,
):
    if stop_sequences is None:
        stop_sequences = ["\n\n", "<|endoftext|>"]
    try:
        if parameters is None:
            parameters = {
                "min_tokens": 0,
                "max_tokens": max_new_tokens,
                "repetition_penalty": 1,
                "stop_sequences": stop_sequences,
                "decoding_method": "greedy",
            }
        if "openai" in str(client.provider_class()):
            if "top_k" in parameters.keys():
                del parameters["top_k"]
            if "repetition_penalty" in parameters.keys():
                del parameters["repetition_penalty"]
                parameters["frequency_penalty"] = 0
                parameters["presence_penalty"] = 0

        altk_params = GenerationArgs(**parameters)
        response = client.generate(
            prompt,
            mode=gen_mode,
            generation_args=altk_params,
        )
        return response
    except Exception as e:
        logger.error(
            "Error in configuring LLM", extra={"details": json.dumps({"Error": str(e)})}
        )
        return ""
