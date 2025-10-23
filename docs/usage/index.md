#### Pre-LLM
For immediately before the prompt is sent to the model

<div class="grid">
  <a href="https://github.com/AgentToolkit/agent-lifecycle-toolkit/blob/main/altk/pre_llm/spotlight/README.md" class="card">
    <b>️✨ Spotlight</b><br/>
    Emphasize important spans within your prompts to steer attention
  </a>
</div>

#### Pre-tool
For immediately before a tool is invoked by an agent
<div class="grid">
  <a
    href="https://github.com/AgentToolkit/agent-lifecycle-toolkit/blob/main/altk/pre_tool/refraction/README.md"
    class="card"
  >
    <b>️💡 Refraction</b><br/>
    Validate and repair tool call sequences using classical AI planning
  </a>
  <a
    href="https://github.com/AgentToolkit/agent-lifecycle-toolkit/blob/main/altk/pre_tool/sparc/README.md"
    class="card"
  >
    <b>️⚡️ SPARC</b><br/>
    Evaluate the static and semantic elements tool calls before execution
  </a>
</div>

#### Post-tool
For immediately after a tool response is received

<div class="grid">
  <a
    href="https://github.com/AgentToolkit/agent-lifecycle-toolkit/blob/main/altk/post_tool/code_generation/README.md"
    class="card"
  >
    <b>📚 JSON Processor</b><br/>
    Dynamically extract data from large and complex JSON objects
  </a>
  <a
    href="https://github.com/AgentToolkit/agent-lifecycle-toolkit/blob/main/altk/post_tool/rag_repair/README.md"
    class="card"
  >
    <b>📄🛠️ RAG Repair</b><br/>
    Use domain documentation to repair tool call errors
  </a>
  <a
    href="https://github.com/AgentToolkit/agent-lifecycle-toolkit/blob/main/altk/post_tool/silent_review/README.md"
    class="card"
  >
    <b>️💬 Silent Review</b><br/>
    Useful for correcting tool calls where errors are not explicit in the response
  </a>
</div>

#### Pre-response
For immediately before the agent returns a response to the user

<div class="grid">
  <a
    href="https://github.com/AgentToolkit/agent-lifecycle-toolkit/blob/main/altk/pre_response/policy_guard/README.md"
    class="card"
  >
    <b>🛡️ Policy Guard</b><br/>
    Guard and enforce policies in LLM responses
  </a>
</div>
