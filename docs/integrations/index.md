# Integrations

ALTK is designed to integrate flexibly into agentic pipelines, and its components can be configured in multiple ways depending on the target environment.
We plan on integrating ALTK components into the following frameworks.

## MCP (coming soon)

A notable integration is with the [Context Forge MCP Gateway](https://github.com/IBM/mcp-context-forge), which allows ALTK components to be configured externally — without modifying the agent code. This separation of concerns enables teams to experiment with lifecycle enhancements, enforce policies, and improve reliability without touching the agent’s core logic. For example, components like SPARC, or Silent Review can be activated or tuned via configuration, making it easier for agents to benefit from these components.

<!-- Add demo links -->

## Langflow (coming soon)
ALTK also works well with [Langflow](http://langflow.org), a visual programming interface for LLM agents. Developers can compose workflows and drop an agent with configurable ALTK components using Langflow’s visual interface to easily experiment with different configurations and understand how ALTK components affect agent behavior.

<!-- See an agent with ALTK components in Langflow here: https://github.com/langflow-ai/langflow/pull/10221  (change to proper link once merged) -->
