<h1 align="center" >
    <img alt="Agent Lifecycle Toolkit (ALTK) logo" src="assets/logo.png" height="120">
</h1>

<h4 align="center">Delivering plug-and-play, framework-agnostic technology to boost agents' performance</h4>

<div style="text-align: center;">

<tr>
<td align="center">
  <a href="https://github.com/AgentToolkit/agent-lifecycle-toolkit" style="text-decoration: none; color: inherit;"><b>Star us on GitHub!</b></a> &nbsp; <a href="https://github.com/AgentToolkit/agent-lifecycle-toolkit">
    <img src="https://img.shields.io/github/stars/AgentToolkit/agent-lifecycle-toolkit.svg?style=social" alt="GitHub stars" style="vertical-align: middle; height: 30px;">
  </a>
</td>
</tr>
<br>
<tr>
<td align="center">
  <a href="https://www.youtube.com/@AgentToolkit" style="text-decoration: none; color: inherit;"><b>Subscribe to our YouTube channel</b></a> &nbsp; <a href="https://www.youtube.com/@AgentToolkit">
    <img src="https://upload.wikimedia.org/wikipedia/commons/b/b8/YouTube_Logo_2017.svg" style="vertical-align: middle; height: 18px;">
  </a>
</td>
</tr>
</div>


## Community Bulletin
### 🔜 What's Ahead
- **Dec. 1-5, 2025**: Joint demos at AWS re:Ignite

### ✅ Past Highlights
- **Nov. 10, 2025**: ALTK showcases at NY TechXchange Dev Day
- **Nov. 6, 2025**: ATLK featured at Lausanne TechXchange Dev Day
- **Oct. 29, 2025**: 🎉 ALTK is live! Check out the launch [blog](https://research.ibm.com/blog/altk-agent-toolkit?previewToken=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6MTEsImlhdCI6MTc2MTc1MTg3MiwiZXhwIjoxNzYyMDExMDcyLCJzdWIiOiI0NTYwIn0.jfBYD6cOFSJXw0ZFPziCtGExsIvlc9uFp433KdO1CDE)

## What is ALTK?
The Agent Lifecycle Toolkit helps agent builders create better performing agents by easily integrating our components into agent pipelines.

- *Does your agent not follow instructions?*
<br> [Spotlight](https://agenttoolkit.github.io/agent-lifecycle-toolkit/concepts/components/spotlight/) emphasizes important spans in prompts to steer LLM attention.
- *Does your agent struggle to route to the right tool?*
<br> [Retrieval Augmented Thinking](concepts/components/rat/) provides your agent with tool hints generated from tool domain content.
- *Does your agent generate inconsistent tool sequences?*
<br> [Refraction](https://github.com/AgentToolkit/agent-lifecycle-toolkit/tree/main/altk/pre_tool/refraction) validates and repairs tool call syntax to prevent execution failures.
- *Is your agent calling tools with hallucinated arguments or struggling to choose the correct tools in the right order?*
<br> [SPARC](https://github.com/AgentToolkit/agent-lifecycle-toolkit/tree/main/altk/pre_tool/sparc) makes sure tool calls match the tool specifications and request semantics, and are generated correctly based on the conversation.
- *Is your agent overwhelmed with large JSON payloads in its context?*
<br> [JSON Processor](https://github.com/AgentToolkit/agent-lifecycle-toolkit/tree/main/altk/post_tool/code_generation) generates code on the fly to extract relevant data in JSON tool responses.
- *Is your agent ignoring subtle semantic tool errors?*
<br> [Silent Error Review](https://github.com/AgentToolkit/agent-lifecycle-toolkit/tree/main/altk/post_tool/silent_review) detects silent errors in tool responses and assess relevance, accuracy, and completeness.
- *Is your agent not able to recover from tool call failures?*
<br> [RAG Repair](https://github.com/AgentToolkit/agent-lifecycle-toolkit/tree/main/altk/post_tool/rag_repair) repairs failed tool calls using domain-specific documents via Retrieval-Augmented Generation.
- *Does your agent return responses that violate policies or instructions?*
<br> [Policy Guard](https://github.com/AgentToolkit/agent-lifecycle-toolkit/tree/main/altk/pre_response/policy_guard) ensures agent outputs comply with defined policies and repairs them if needed.
- *Does your tool have clear metadata or docstrings for the agent?*
<br> [Tool Enrichment](https://github.com/AgentToolkit/agent-lifecycle-toolkit/tree/main/altk/build_time/tool_enrichment_toolkit) generates tool and parameter descriptions to enhance tool calling.
- *Has your agent been tested to call the correct tool with the right arguments?*
<br> [Test Case Generation](https://github.com/AgentToolkit/agent-lifecycle-toolkit/tree/main/altk/build_time/test_case_generation_toolkit) generates user utterances to test its behavior across a variety of scenarios.
- *Does your agent call the correct tool with the right arguments for these test cases?*
<br> [Tool Validation](https://github.com/AgentToolkit/agent-lifecycle-toolkit/tree/main/altk/build_time/tool_validation_toolkit) invokes the agent with test utterances and identify different types of tool-selection and argument-related errors.

## Installation
To use ALTK, simply install agent-lifecycle-toolkit from your package manager, e.g. pip:

```bash
pip install agent-lifecycle-toolkit
```

More [detailed installation instructions](./getting_started) are available in the docs.
