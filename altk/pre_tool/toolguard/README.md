# ToolGuards for Enforcing Agentic Policy Adherence
Enforces business policy adherence in agentic workflows. Enabling this component has demonstrated up to a **20‑point improvement** in end‑to‑end agent accuracy when invoking tools. This work is described in [EMNLP 2025 Towards Enforcing Company Policy Adherence in Agentic Workflows](https://arxiv.org/pdf/2507.16459), and is published in [this GitHub library](https://github.com/AgentToolkit/toolguard).

## Table of Contents
- [Overview](#overview)
- [ToolGuardSpecComponent](#ToolGuardSpecComponent)
  - [Configuration](#component-configuration)
  - [Inputs and Outputs](#input-and-output)
  - [Usage example](#usage-example)
- [ToolGuardCodeComponent](#ToolGuardCodeComponent)
  - [Configuration](#component-configuration-1)
  - [Inputs and Outputs](#input-and-output-1)
  - [Usage example](#usage-example-1)


## Overview

Business policies (or guidelines) are normally detailed in company documents, and have traditionally been hard-coded into automatic assistant platforms. Contemporary agentic approaches take the "best-effort" strategy, where the policies are appended to the agent's system prompt, an inherently non-deterministic approach, that does not scale effectively. Here we propose a deterministic, predictable and interpretable two-phase solution for agentic policy adherence at the tool-level: guards are executed prior to function invocation and raise alerts in case a tool-related policy deem violated.
This component enforces **pre‑tool activation policy constraints**, ensuring that agent decisions comply with business rules **before** modifying system state. This prevents policy violations such as unauthorized tool calls or unsafe parameter values.

### Installation
```
uv pip install "agent-lifecycle-toolkit[toolguard]"
```

## ToolGuardSpecComponent
This component gets a set of tools and a policy document and generates multiple ToolGuard specifications, known as `ToolGuardSpec`s. Each specification is attached to a tool, and it declares a precondition that must apply before invoking the tool. The specification has a `name`, `description`, list of `references` to the original policy document, a set of declarative `compliance_examples`, describing test cases that the toolGuard should allow the tool invocation, and `violation_examples`, where the toolGuard should raise an exception.

This component supports only a `build` phase. The generated specifications are returned as output, and are also saved to a specified file system directory.
The specifications are aimed to be used as input into our next component - the `ToolGuardCodeComponent` described below.

The two components are not concatenated by design. As the generation involves a non-deterministic language model, the results need to be reviewed by a human. Hence, the output specification files should be reviewed and optionally edited. For example, removing a wrong compliance example.

### Component Configuration
This component expects an LLM client configuration. Here is a concrete example using WatsonX SDK:
```python
from altk.core.llm.providers.ibm_watsonx_ai.ibm_watsonx_ai import WatsonxLLMClient
llm_client = WatsonxLLMClient(
    model_name="meta-llama/llama-4-maverick-17b-128e-instruct-fp8",
    api_key=os.getenv("WX_API_KEY"),
    project_id = os.getenv("WX_PROJECT_ID"),
    url=os.getenv("WX_URL"),
)
```


### Input and Output
The component build input is a `ToolGuardSpecBuildInput` object containing the following fields:
  * `policy_text: str`: Text of the policy document
  * `tools: List[Callable] | List[BaseTool] | str`: List of available tools. Either as Python functions, methods, Langgraph Tools, or a path to an Open API specification file.
  * `out_dir: str`: A directory in the local file system where the specification objects will be saved.

The component build output is a list of `ToolGuardSpec`, as described above.

### Usage example
see [simple calculator test](../../../tests/pre_tool/toolguard/test_toolguard_specs.py)


## ToolGuardCodeComponent

This component enforces policy adherence through a two-phase process:

(1) **Buildtime**: Given a set of `ToolGuardSpec`s, generates policy validation code - `ToolGuard`s.
Similar to ToolGuard Specifications, generated `ToolGuards` are a good start, but they may contain errors. Hence, they should be also reviewed by a human.

(2) **Runtime**: ToolGuards are deployed within the agent's flow, and are triggered before agent's tool invocation. They can be deployed into the agent loop, or in an MCP Gateway.
The ToolGuards check if a planned action complies with the policy. If it violates, the agent is prompted to self-reflect and revise its plan before proceeding.


### Component Configuration

This component expects an LLM client configuration.
Here is an example using a Watsonx LLM client:
```
from altk.core.llm.providers.ibm_watsonx_ai.ibm_watsonx_ai import WatsonxLLMClient
llm = WatsonxLLMClient(
    model_name="meta-llama/llama-4-maverick-17b-128e-instruct-fp8",
    api_key=os.getenv("WX_API_KEY"),
    project_id = os.getenv("WX_PROJECT_ID"),
    url=os.getenv("WX_URL"),
)
config = ToolGuardCodeComponentConfig(llm_client=llm)
toolguard_code_component = ToolGuardCodeComponent(config)
```


### Input and Output
The Component has two phases:
#### Build phase
An agent owner should use this API to generate ToolGuards - Python functions that enforce the given business policy.
The input of the build phase is a `ToolGuardCodeBuildInput` object, containing:
  * `tools: List[Callable] | List[BaseTool] | str`: List of available tools. Either as Python functions, methods, Langgraph Tools, or a path to an Open API specification file.
  * `toolguard_specs: List[ToolGuardSpec]`: List of specifications, optionally generated by `ToolGuardSpecComponent` component and reviewed.
  * `app_name: str`: Name of the application for which guards are being generated. This will be namespace of the guards generated code.
  * `out_dir: str | Path`: A directory in the local file system where the ToolGuard objects will be saved.

The output of the build phase is a `ToolGuardsCodeGenerationResult` object with:
  * `out_dir: Path`: Path to the file system where the results were saved. It is the same as the `input.out_dir`.
  * `domain: RuntimeDomain`: A complex object describing the generated APIs. For example, references to Python file names and class names.
  * `tools: Dict[str, ToolGuardCodeResult]`: A Dictionary of the ToolGuardsResults, by the tool names.
    * Each `ToolGuardCodeResult` details the name of guard Python file name and the guard function name. It also references the generated unit test files.

#### Runtime phase
A running agent should use the runtime async API to check if a tool call complies with the given policy.
The input of the runtime phase is a `ToolGuardCodeRunInput` object:
  * `generated_guard_dir: str | Path`: Path in the local file system where the generated guard Python code (The code that was generated during the build time, described above) is located.
  * `tool_name: str`: The name of the tool that the agent is about to call
  * `tool_args: Dict[str, Any]`: A dictionary of the toolcall arguments, by the argument name.
  * `tool_invoker: IToolInvoker`: A proxy object that enables the guard to call other read-only tools. This is needed when the policy enforcement logic involves getting data from another tool. For example, before booking a flight, you need to check the flight status by calling the "get_flight_status" API.
  The `IToolInvoker` interface contains a single method:
    ```
    def invoke(self, toolname: str, arguments: Dict[str, Any], return_type: Type[T]) -> T
    ```

    ToolGuard library currently ships with three predefined ToolInvokers:
     * `toolguard.runtime.ToolFunctionsInvoker(funcs: List[Callable])` where the tools are defined as plain global Python functions.
     * `toolguard.runtime.ToolMethodsInvoker(obj: object)` where the tools are defined as methods in a given Python object.
     * `toolguard.runtime.LangchainToolInvoker(tools: List[BaseTool])` where the tools are a list of langchain tools.


The output of the runtime phase is a `ToolGuardCodeRunOutput` object with an optional `violation` field.
  * `violation: PolicyViolation | None`: Populated only if a violation was identified. If the toolcall complies with the policy, the violation is None.
    * `violation_level: "info" | "warn" | "error"`: Severity level of a safety violation.
    * `user_message: str | None`: A meaningful error message to the user (this message can be also passed to the agent reasoning phase to find an alternative next action).

### Usage example
see [simple calculator test](../../../tests/pre_tool/toolguard/test_toolguard_code.py)
