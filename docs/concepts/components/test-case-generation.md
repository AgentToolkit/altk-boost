# Test Case Generation Toolkit

This component performs Test Case Generation. It first generates the test case values and then generates an NL Utterance that formulates the test case values into a user query for validating robustness of tools and agents.


This toolkit generates testcases for the parameters present in the python tool adhering to data types, data
formats and any internal parameter dependencies. This component is designed to perform robust testing of tools.

## Features
- Generates a test case with all mandatory and all optional parameters.
- Generates a test case with all mandatory parameters.
- Generates remaining test cases with all mandatory and some optional parameters.
- Enables user to provide test case values which is then used by the system to generate testcases in the above order.

## Architecture
The figure below shows the flow of test case generation.

![img_tc_gen_arch.png](../../assets/img_tc_gen_arch.png)

### Interface
This component expects the following inputs and generates the following output.

#### Input
1. `python_tool_str`: Python langchain Tool loaded as string that follows google docstring format.
2. `test_case_values`: The tool parameter values with which test cases will be generated.

### Output
`nl_test_cases`: Generated test cases with NL utterances in a dictionary format.

## Benchmarking
Test Case generation is evaluated using LLM (llama-3.1-405b) as a judge and scored the generated utterances on two metrics:

1. **Accuracy (range 1 to 5)**: Missing or incorrect parameters lead to a reduction in score.
2. **Fluency (range 1 to 5)**: Fluency describes how human-like the NL test case is.

The evaluation was performed on 400 simple APIs from BFCLv3, with an additional 120 human-curated domain-specific API invocations.

The distribution of these metrics are as follows:

![img_tc_gen_acc.png](../../assets/img_tc_gen_acc.png)
![img_tc_gen_fluency.png](../../assets/img_tc_gen_fluency.png)

## Getting Started
Refer to this [README](https://github.com/AgentToolkit/agent-lifecycle-toolkit/blob/main/altk/post_request/test_case_generation_toolkit/README.md) for instructions on how to get started with the code.
See an example in action [here](https://github.com/AgentToolkit/agent-lifecycle-toolkit/blob/main/examples/testcase_generation_example.py).
