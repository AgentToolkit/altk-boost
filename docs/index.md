<h1 align="center" >
    <img alt="Agent Lifecycle Toolkit (ALTK) logo" src="assets/logo.png" height="120">
</h1>

<h4 align="center">Delivering plug-and-play, framework-agnostic technology to boost agents' performance</h4>

<div style="text-align: center;">
<table align="center" border="1" cellpadding="10" cellspacing="0" style="border-collapse: collapse; margin: 20px auto; font-size: 1.2em;">
  <tr>
    <td align="center">
      <a href="https://github.com/AgentToolkit/agent-lifecycle-toolkit" style="text-decoration: none; color: inherit;"><b>Star us on GitHub!</b></a> &nbsp; <a href="https://github.com/AgentToolkit/agent-lifecycle-toolkit">
        <img src="https://img.shields.io/github/stars/AgentToolkit/agent-lifecycle-toolkit.svg?style=social" alt="GitHub stars" style="vertical-align: middle; height: 30px;">
      </a>
    </td>
  </tr>
</table>
</div>

## What is ALTK?
The Agent Lifecycle Toolkit helps agent builders create better performing agents by easily integrating our components into agent pipelines. The components help improve the performance of agents by addressing key gaps in various stages of the agent lifecycle, such as in reasoning, or tool calling errors, or output guardrails.

![lifecycle.png](assets/lifecycle.png)


## Installation
To use ALTK, simply install agent-lifecycle-toolkit from your package manager, e.g. pip:

```bash
pip install agent-lifecycle-toolkit
```

More [detailed installation instructions](./getting_started) are available in the docs.


## Features

| Lifecycle Stage | Component                                                              | Purpose                                                                                                                                                                                                                                                   |
|-----------------|------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Pre-LLM         | [Spotlight](https://github.com/AgentToolkit/agent-lifecycle-toolkit/tree/main/altk/pre_llm/spotlight)                                    | *Does your agent not follow instructions?* Emphasize important spans in prompts to steer LLM attention.                                                                                                                                                   |
| Pre-tool        | [Refraction](https://github.com/AgentToolkit/agent-lifecycle-toolkit/tree/main/altk/pre_tool/refraction)              | *Does your agent generate inconsistent tool sequences?* Validate and repair tool call syntax to prevent execution failures.                                                                                                                               |
| Pre-tool        | [SPARC](https://github.com/AgentToolkit/agent-lifecycle-toolkit/tree/main/altk/pre_tool/sparc)                        | *Is your agent calling tools with hallucinated arguments or struggling to choose the correct tools in the right order?* Make sure tool calls match the tool specifications and request semantics, and are generated correctly based on the conversation.  |
| Post-tool       | [JSON Processor](https://github.com/AgentToolkit/agent-lifecycle-toolkit/tree/main/altk/post_tool/code_generation)                                                      | *Is your agent overwhelmed with large JSON payloads in its context?* Generate code on the fly to extract relevant data in JSON tool responses.                                                                                                            |
| Post-tool       | [Silent Error Review](https://github.com/AgentToolkit/agent-lifecycle-toolkit/tree/main/altk/post_tool/silent_review) | *Is your agent ignoring subtle semantic tool errors?* Detect silent errors in tool responses and assess relevance, accuracy, and completeness.                                                                                                            |
| Post-tool       | [RAG Repair](https://github.com/AgentToolkit/agent-lifecycle-toolkit/tree/main/altk/post_tool/rag_repair)             | *Is your agent not able to recover from tool call failures?* Repair failed tool calls using domain-specific documents via Retrieval-Augmented Generation.                                                                                                 |
| Pre-response    | [Policy Guard](https://github.com/AgentToolkit/agent-lifecycle-toolkit/tree/main/altk/pre_response/policy_guard)                              | *Does your agent return responses that violate policies or instructions?* Ensure agent outputs comply with defined policies and repairs them if needed.                                                                                                   |
