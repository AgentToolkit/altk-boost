import os
import sys
import json
from altk.build_time.test_case_generation_toolkit.src.toolops.utils.llm_util import (
    execute_prompt,
)
import numpy as np
import logging
import re

logger = logging.getLogger(
    "toolops.generation.test_case_generation.test_case_generation_utils.prompt_execution"
)
parent_dir = os.path.dirname(os.path.join(os.getcwd(), "src"))
sys.path.append(parent_dir)


def data_using_LLM(prompt, client, gen_mode):
    parameters = {
        "seed": np.random.randint(1, 50),
        "min_tokens": 0,
        "max_tokens": 1000,
        "decoding_method": "greedy",
        "repetition_penalty": 1,
        "stop_sequences": [],
        "temperature": 0.7,
        "top_k": 50,
        "top_p": 1,
    }

    response_trimmed = execute_prompt(prompt, client, gen_mode, parameters=parameters)
    response_portion = response_trimmed
    if "```" in response_trimmed:
        response_portion = response_trimmed.split("```")[1]
    if "python" in response_portion:
        if "testcases =" in response_portion.split("python")[1]:
            response_from_LLM = response_portion.split("python")[1].split(
                "testcases ="
            )[1]
        else:
            response_from_LLM = response_portion.split("python")[1]
    elif "json" in response_portion:
        if "testcases =" in response_portion.split("json")[1]:
            response_from_LLM = response_portion.split("json")[1].split("testcases =")[
                1
            ]
        else:
            response_from_LLM = response_portion.split("json")[1]
    else:
        response_from_LLM = response_portion
    try:
        json.loads(response_from_LLM)
    except Exception:
        valid_jsons = []
        stack = 0
        start = None
        num_testcase = 0
        for i, ch in enumerate(response_from_LLM):
            if ch == "{":
                if stack == 0:
                    start = i
                stack += 1
            elif ch == "}":
                stack -= 1
                if stack in [0, 1] and start is not None:
                    snippet = response_from_LLM[start : i + 1]
                    try:
                        num_testcase = num_testcase + 1
                        if stack == 1:
                            snippet = snippet + "}"
                        if "testcase_" not in snippet:
                            snippet = {
                                "testcase_" + str(num_testcase): json.loads(snippet)
                            }
                        if isinstance(snippet, str):
                            data = json.loads(snippet)
                        else:
                            data = snippet
                        valid_jsons.append(data)
                    except json.JSONDecodeError:
                        pass
                    start = None
                    stack = 0

        merged = {}
        for item in valid_jsons:
            if isinstance(item, dict):
                merged.update(item)
        if len(merged) > 0:
            response_from_LLM = merged
        else:
            response_from_LLM = "No json found"
    return response_from_LLM


def post_process_testcase(response_from_LLM):
    if isinstance(response_from_LLM, dict):
        response_from_LLM = json.dumps(response_from_LLM)
    response_from_LLM = response_from_LLM.replace("\_", "_")
    response_from_LLM = response_from_LLM.replace("\n", "")
    response_from_LLM = response_from_LLM.replace("\t", "")
    response_from_LLM = re.sub(r"\s+", " ", response_from_LLM).strip()
    response_from_LLM = response_from_LLM.replace(": { ", ":{")
    response_from_LLM = response_from_LLM.replace("}, ", "},")
    response_from_LLM = response_from_LLM.replace("{ ", "{")
    response_from_LLM = response_from_LLM.replace(" }", "}")
    response_from_LLM = response_from_LLM.split("testcase")
    processed_response_from_LLM = dict()
    count = 0
    for case in response_from_LLM:
        try:
            changes_done = False
            if "Testcase" in case:
                case = case.split("}Testcase")[0]
                case = '{"testcase' + case
                case = case + "}"
                changes_done = True
            if "TestCase" in case:
                case = case.split("TestCase")[0]
                case = case[:-3]
                case = '{"testcase' + case
                changes_done = True
            if "}}" == case[-2:] and not changes_done:
                case = '{"testcase' + case
            if ")" in case[-3:]:
                case = case[:-4]
                case = '{"testcase' + case
            if "," in case[-2:]:
                case = case[:-2]
                case = '{"testcase' + case
                case = case + "}"
            elif "{" in case[-2:]:
                case = case[:-3]
                if "}}" == case[-2:]:
                    case = '{"testcase' + case
                else:
                    case = '{"testcase' + case
                    case = case + "}"
            case = case.replace("False", "false").replace("True", "true")
            case_json = json.loads(case)
            count = count + 1
            key = list(case_json.keys())[0]
            processed_response_from_LLM[key] = case_json[key]
        except Exception:
            pass
    return processed_response_from_LLM
