# ToolGuards for Enforcing Agentic Policy Adherence
An agent lifecycle solution for enforcing business policy adherence in agentic workflows. Enabling this component has demonstrated up to a **20‑point improvement** in end‑to‑end agent accuracy when invoking tools.

## Table of Contents
- [Overview](#overview)
- [When to Use This Component](#when-it-is-recommended-to-use-this-component)
- [LLM Configuration Requirements](#llm-configuration-requirements)
- [Quick Start](#quick-start)
- [Parameters](#parameters)
  - [Constructor Parameters](#constructor-parameters)
  - [Build Phase Input Format](#build-phase-input-format)
  - [Run Phase Input Format](#run-phase-input-format)
  - [Run Phase Output Format](#run-phase-output-format)



## Overview

Business policies (or guidelines) are normally detailed in company documents, and have traditionally been hard-coded into automatic assistant platforms. Contemporary agentic approaches take the "best-effort" strategy, where the policies are appended to the agent's system prompt, an inherently non-deterministic approach, that does not scale effectively. Here we propose a deterministic, predictable and interpretable two-phase solution for agentic policy adherence at the tool-level: guards are executed prior to function invocation and raise alerts in case a tool-related policy deem violated.

### Key Components

The solution enforces policy adherence through a two-phase process:

(1) **Buildtime**: an offline two-step pipeline that automatically maps policy fragments to the relevant tools and generates policy validation code - ToolGuards.

(2) **Runtime**: ToolGuards are deployed within the agent's ReAct flow, and are executed after "reason" and just before "act" (agent's tool invocation). If a planned action violates a policy, the agent is prompted to self-reflect and revise its plan before proceeding. Ultimately, the deployed ToolGuards will prevent the agent from taking an action violating a policy.

![two-phase-solution](buildtime-runtime.png)


## When it is Recommended to Use This Component
This component enforces **pre‑tool activation policy constraints**, ensuring that agent decisions comply with business rules **before** modifying system state. This prevents policy violations such as unauthorized tool calls or unsafe parameter values.

## LLM Configuration Requirements
The **build phase** uses **two LLMs**:

### 1. Reasoning LLM (Build Step 1)
Used to interpret, restructure, and classify policy text.

This model can be any LLM registered through:
```python
from altk.core.llm import get_llm  # def get_llm(name: str) -> Type["LLMClient"]

OPENAILiteLLMClientOutputVal = get_llm("litellm.output_val")

```
#### Azure example for gpt-4o:

Environment variables:
```bash
export AZURE_OPENAI_API_KEY="<your key>"
export AZURE_API_BASE="https://your.azure.endpoint"
export AZURE_API_VERSION="2024-08-01-preview"
```
code:
```python
from altk.core.llm import get_llm  # def get_llm(name: str) -> Type["LLMClient"]

OPENAILiteLLMClientOutputVal = get_llm("litellm.output_val")
validating_llm_client = OPENAILiteLLMClientOutputVal(
    model_name="gpt-4o-2024-08-06",
    custom_llm_provider="azure",
)

```

### 2. Code Generation LLM (Build Step 2)
Used only in the code generation phase to produce Python enforcement logic.
Backed by Mellea, which requires parameters aligning to:
```python
mellea.MelleaSession.start_session(
    backend_name=...,
    model_id=...,
    backend_kwargs=...    # any additional arguments
)
```

These map directly to environment variables:

| Environment Variable           | Mellea Parameter | Description                                                        |
| ------------------------------ | ---------------- | ------------------------------------------------------------------ |
| `TOOLGUARD_GENPY_BACKEND_NAME` | `backend_name`   | Which backend to use (e.g., `openai`, `anthropic`, `vertex`, etc.) |
| `TOOLGUARD_GENPY_MODEL_ID`     | `model_id`       | Model name / deployment id                                         |
| `TOOLGUARD_GENPY_ARGS`         | `backend_kwargs` | JSON dict of any additional connection/LLM parameters              |

Example (Claude-4 Sonnet through OpenAI-compatible endpoint):
```bash
export TOOLGUARD_GENPY_BACKEND_NAME="openai"
export TOOLGUARD_GENPY_MODEL_ID="GCP/claude-4-sonnet"
export TOOLGUARD_GENPY_ARGS='{"base_url":"https://your-litellm-endpoint","api_key":"<your key>"}'
```

## Quick Start
See runnable example:
```
pre-tool-guard-toolkit/examples/calculator_example
```

```python
import asyncio
from altk.pre_tool.toolguard.core import (
    ToolGuardBuildInput, ToolGuardBuildInputMetaData,
    ToolGuardRunInput, ToolGuardRunInputMetaData,
)
from altk.pre_tool.toolguard.pre_tool_guard import PreToolGuardComponent

class ToolGuardExample:
    def __init__(self, tools, workdir, policy_text, validating_llm_client, short=True):
        self.middleware = PreToolGuardComponent(tools=tools, workdir=workdir, app_name="calculator")
        build_input = ToolGuardBuildInput(metadata=ToolGuardBuildInputMetaData(
            policy_text=policy_text,
            short1=short,
            validating_llm_client=validating_llm_client,
        ))
        asyncio.run(self.middleware._build(build_input))

    def run_example(self, tool_name, tool_params):
        run_input = ToolGuardRunInput(
            metadata=ToolGuardRunInputMetaData(tool_name=tool_name, tool_parms=tool_params),
        )
        return self.middleware._run(run_input)
```


## Parameters

### Constructor Parameters
```python
PreToolGuardComponent(tools, workdir)
```

| Parameter | Type             | Description |
|----------|------------------|-------------|
| `tools`   | `list[Callable]` | List of functions or LangChain tools to safeguard.
| `workdir` | `str` or `Path`  | Writable working directory for storing build artifacts.

### Build Phase Input Format
```python
ToolGuardBuildInput(
    metadata=ToolGuardBuildInputMetaData(
        policy_text="<Markdown or HTML policy>",
        short1=True,
        validating_llm_client=<LLMClient>
    )
)
```

### Run Phase Input Format
```python
ToolGuardRunInput(
    metadata=ToolGuardRunInputMetaData(
        tool_name="divide_tool",
        tool_parms={"g": 3, "h": 4},
    ),
    messages=[{"role": "user", "content": "Calculate 3/4"}]
)
```

### Run Phase Output Format
```python
ToolGuardRunOutput(output=ToolGuardRunOutputMetaData(error_message=False))
```
`error_message` is either `False` (valid) or a descriptive violation message.
