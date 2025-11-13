# Tool Enrichment Component

This component performs python tool enrichment using the metadata information in the tool definition for improved tool calling and tool input formation.

This component enriches python tool docstrings using the metadata information in the tool definition. This toolkit is designed to enhance the tool docstrings for improved tool learning - i.e., tool selection and tool calling by the LLM.

## Features
This component accepts as input the tool definition python file as string (consisting of @tool decorator) and outputs the enriched python tool string with modified docstring which consists of the following enrichments:
- Enriched tool description using metadata like tool signature, tool method body, current tool description, etc
- Improved tool parameter descriptions using metadata like existing parameter descriptions, declarations of global variables and class definitions and other metadata.
- New examples corresponding to each parameter of the tool based on parameter descriptions, tool body details, etc.
- Enriched tool return descriptions using existing return descriptions, tool body, global variable declarations and other metadata in the tool file.

## Architecture

The figure below shows the flow of tool enrichment.

![img_tool_enrich_arch.png](../../assets/img_tool_enrich_arch.png)

### Interface
This component expects the following input and generates the following output.

#### Input
1. `python_tool_str`: Python langchain Tool loaded as string that follows google docstring format.

### Output
`enriched_python_tool_str`: Python langchain Tool in string format with enriched docstring that follows google docstring format.

## Benchmarking
Tool Enrichment is extensively benchmarked on WxO tools. Following is the benchmarking results on ServiceNow tools. When tool descriptions are of poor quality (see tool_name as desc), enrichment increases the number of correct agent and tool calls (~30 pts).

![img_tool_enrich_result.png](../../assets/img_tool_enrich_result.png)


## Getting Started
Refer to this [README](https://github.com/AgentToolkit/agent-lifecycle-toolkit/blob/main/altk/post_request/tool_enrichment_toolkit/README.md) for instructions on how to get started with the code.
See an example in action [here](https://github.com/AgentToolkit/agent-lifecycle-toolkit/blob/main/examples/tool_enrichment_example.py).
