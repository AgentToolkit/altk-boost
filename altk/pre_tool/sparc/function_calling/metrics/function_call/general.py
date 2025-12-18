from typing import Any, Dict, List, Optional, Union
from altk.pre_tool.sparc.function_calling.metrics.base import (
    FunctionMetricsPrompt,
)

_general_system = (
    "### Task Description and Role:\n\n"
    "{{ task_description }}\n\n"
    "Your output must conform to the following JSON schema, in the same order as the fields appear in the schema:\n"
    "{{ metric_jsonschema }}"
)

_general_user: str = (
    "Conversation context:\n"
    "{{ conversation_context }}\n\n"
    "Tool Specification:\n"
    "{{ tool_inventory }}\n\n"
    "Proposed tool call:\n"
    "{{ tool_call }}\n\n"
    "Return a JSON object as specified in the system prompt. You MUST keep the same order of fields in the JSON object as provided in the JSON schema and examples."
)

_general_user_no_spec: str = (
    "Conversation context:\n"
    "{{ conversation_context }}\n\n"
    "Proposed tool call:\n"
    "{{ tool_call }}\n\n"
    "Return a JSON object as specified in the system prompt. You MUST keep the same order of fields in the JSON object as provided in the JSON schema and examples."
)


class GeneralMetricsPrompt(FunctionMetricsPrompt):
    """Prompt builder for general tool-call semantic metrics."""

    system_template = _general_system
    user_template = _general_user


class GeneralMetricsPromptNoSpec(FunctionMetricsPrompt):
    """Prompt builder for tool-spec-free general metrics."""

    system_template = _general_system
    user_template = _general_user_no_spec


def get_general_metrics_prompt(
    prompt: Union[GeneralMetricsPrompt, GeneralMetricsPromptNoSpec],
    conversation_context: Union[str, List[Dict[str, str]]],
    tool_call: Dict[str, Any],
    tool_inventory: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, str]]:
    """
    Build the messages for a general semantic evaluation.

    Args:
        prompt: Prompt instance (with or without tool spec support)
        conversation_context: Conversation history
        tool_call: The tool call to evaluate
        tool_inventory: Optional tool specifications (not needed for tool-spec-free metrics)

    Returns the list of chat messages (system -> [few-shot] -> user).
    """
    user_kwargs = {
        "conversation_context": conversation_context,
        "tool_call": tool_call,
    }

    # Only include tool_inventory if provided and prompt expects it
    if tool_inventory is not None and isinstance(prompt, GeneralMetricsPrompt):
        user_kwargs["tool_inventory"] = tool_inventory

    return prompt.build_messages(user_kwargs=user_kwargs)
