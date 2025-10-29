# Integrations

ALTK is designed to integrate flexibly into agentic pipelines, and its components can be configured in multiple ways depending on the target environment.

## MCP

A notable integration is with the [ContextForge MCP Gateway](https://github.com/IBM/mcp-context-forge), which allows ALTK components to be configured externally — without modifying the agent code. This separation of concerns enables teams to experiment with lifecycle enhancements, enforce policies, and improve reliability without touching the agent’s core logic. For example, components like SPARC, or Silent Review can be activated or tuned via configuration, making it easier for agents to benefit from these components.

See a demo [here](https://www.youtube.com/watch?v=KMxdkvSsHvo) of how tools responses with large JSON payloads can be handled reliably without polluting your agent's context.

## Langflow

ALTK also works well with [Langflow](http://langflow.org), a visual programming interface for LLM agents. Developers can compose workflows and drop an agent with configurable ALTK components using Langflow’s visual interface to easily experiment with different configurations and understand how ALTK components affect agent behavior.

Here is a [demo](https://www.youtube.com/watch?v=YNwPBK_KxXY) of a custom [ALTK agent](https://github.com/langflow-ai/langflow/blob/main/src/lfx/src/lfx/components/agents/altk_agent.py) in Langflow with ALTK components integrated to improve tool calling.

