import os
from pathlib import Path

import markdown

from altk.pre_tool.toolguard.examples.calculator_example.example_tools import (
    add_tool,
    subtract_tool,
    multiply_tool,
    divide_tool,
    map_kdi_number,
)
from altk.pre_tool.toolguard.examples.tool_guard_example import ToolGuardExample
from altk.core.llm import get_llm


subdir_name = "work_dir_wx"
script_path = os.path.abspath(__file__)
script_directory = os.path.dirname(script_path)
work_dir = Path(os.path.join(script_directory, subdir_name))
policy_doc_path = os.path.join(script_directory, "policy_document.md")
work_dir.mkdir(exist_ok=True)

OPENAILiteLLMClientOutputVal = get_llm("litellm.output_val")
validating_llm_client = OPENAILiteLLMClientOutputVal(
    model_name="gpt-4o-2024-08-06",
    custom_llm_provider="azure",
)


tool_funcs = [add_tool, subtract_tool, multiply_tool, divide_tool, map_kdi_number]
policy_text = open(policy_doc_path, "r", encoding="utf-8").read()
policy_text = markdown.markdown(policy_text)

tool_guard_example = ToolGuardExample(
    tools=tool_funcs,
    workdir=work_dir,
    policy_text=policy_text,
    validating_llm_client=validating_llm_client,
    app_name="calculator",
)
run_output = tool_guard_example.run_example(
    "divide_tool",
    {"g": 3, "h": 4},
)
print(run_output)
passed = not run_output.output.error_message
if passed:
    print("success!")
else:
    print("failure!")

run_output = tool_guard_example.run_example(
    "divide_tool",
    {"g": 5, "h": 0},
)
print(run_output)
passed = not run_output.output.error_message
if not passed:
    print("success!")
else:
    print("failure!")

run_output = tool_guard_example.run_example(
    "add_tool",
    {"a": 5, "b": 44},
)
print(run_output)
passed = not run_output.output.error_message
if passed:
    print("success!")
else:
    print("failure!")

run_output = tool_guard_example.run_example(
    "add_tool",
    {"a": 5, "b": 73},
)
print(run_output)
passed = not run_output.output.error_message
if not passed:
    print("success!")
else:
    print("failure!")

run_output = tool_guard_example.run_example(
    "multiply_tool",
    {"e": 3, "f": 44},
)
print(run_output)
passed = not run_output.output.error_message
if passed:
    print("success!")
else:
    print("failure!")

run_output = tool_guard_example.run_example(
    "multiply_tool",
    {"e": 2, "f": 73},
)
print(run_output)
passed = not run_output.output.error_message
if not passed:
    print("success!")
else:
    print("failure!")
