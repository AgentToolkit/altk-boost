# Lifecycle Stages
A typical agent flow consists of three main stages: reasoning, acting, and interacting with the user (input and output processing).
This introduces multiple points (see blue boxes in the figure below) to inject additional components that can address limitations in existing agents and boost their performance.

![lifecycle.png](../assets/lifecycle.png)

## Post-Request
This stage comes immediately after a user request is received. It prepares the input for the agent and can include components like jail-breaking or other input guardrails.

## Pre-LLM
This stage occurs before the prompt is sent to the language model (LLM). It allows for prompt optimization, augmentation, or injection of additional context, etc.
Unlike the post-request stage, the pre-llm stage can happen multiple times in the agent loop.

ALTK includes one component in this stage: [Spotlight](components/spotlight.md).

## Reason (Call LLMs)
In this stage we often call LLMs to "think" or reason about the task or request they have received via a prompt.

## Post-LLM
This stage occurs after the LLM returns a response. This may include the tool the LLM wants to call or generated text that includes the final answer (for non-tool call queries).

Components in this stage can address format inconsistencies, response parsing or transformation before tool invocation or final output.

## Pre-Tool
This stage is triggered before a tool is called by the agent. Its purpose is to validates tool parameters, enforces policies (e.g., rate limits), and optionally intercepts or redirects tool calls.

Failure classes components in this stage may address include invalid tool arguments, redundant or expensive calls, etc.

ALTK includes two components in this stage: [Refraction](components/refraction.md) and [SPARC](components/sparc.md).

## Act (Call tools)
In this stage a tool or tools that the LLM has formulated to address the user's query is being invoked.

## Post-Tool
This stage occurs after a tool is called (whether the tool call was successful or not).
This allows for result validation, processing, caching, logging, and integration into the agent’s response.

Failure classes components in this stage may address include tool execution errors, response processing errors, etc.

ALTK includes the following components for this stage: [Silent Review](components/silent-review.md), [JSON Processor](components/json-processor.md), [RAG Repair](components/rag-repair.md).

## Pre-Response
This is the final stage before the agent sends a response back to the user. Its purpose is to assemble the final output, apply formatting, and ensure compliance with response policies. Similar to the post-request stage, this stage occurs once outside the agent loop.

Failure classes components in this stage may address include output formatting errors, missing information, response safety, violated policy guardrails, etc.

ALTK includes the following components for this stage: [Policy Guard](components/policy-guard.md).
