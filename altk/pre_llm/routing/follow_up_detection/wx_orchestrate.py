import copy
import logging
from typing import Annotated, Any, Dict, List
from altk.pre_llm.routing.follow_up_detection.core.toolkit import (
    FollowUpDetectionRunInput,
    FollowUpDetectionRunOutput,
)
from altk.core.toolkit import ComponentConfig
from altk.core.llm.base import LLMClient
from pydantic import AfterValidator, Field
import pydash as _

logger = logging.getLogger(__name__)


def parse_msg_content(content: dict):
    match _.get(content, "response_type"):
        case "text":
            return _.get(content, "text", "").replace("\n", " ")
        case "option":
            return "Select one of the following: " + ", ".join(
                [option.get("label") for option in _.get(content, "options", [])]
            )
        case _:
            return str(content)


def format_msgs(msg: dict, cutoff: int | None = None):
    if _.get(msg, "role") == "user":
        return f"USER: {'...'.join([parse_msg_content(item) for item in msg.get('content')])}"
    else:
        # TODO: does cutoff actually help?
        # return f"CHATBOT: {"...".join([parse_content(item)[:cutoff] for item in msg.get("content")])}"
        return f"CHATBOT: {'...'.join([parse_msg_content(item) for item in msg.get('content')])}"


def validate_conversation_history(conversation_history: list[dict[str, Any]]):
    for message in conversation_history:
        if "role" not in message or "content" not in message:
            raise ValueError(
                f"Messages must contain 'role' and 'content' keys.\n{message=}"
            )
        if not isinstance(message.get("content"), list):
            raise ValueError(f"Message 'content' key must be a list.\n{message=}")

    if conversation_history[-1].get("role") != "assistant":
        raise ValueError(
            f"Last message from the conversation history must be an assistant message.\n{conversation_history[-1].get('role')}"
        )
    return conversation_history


WxOrchestrateMessages = Annotated[
    list[dict[str, Any]],
    Field(min_length=1),
    AfterValidator(validate_conversation_history),
]


class WxOrchestrateFollowUpDetector:
    def detect_follow_up(
        self,
        config: ComponentConfig,
        data: FollowUpDetectionRunInput[WxOrchestrateMessages],
    ) -> FollowUpDetectionRunOutput:
        query = data.user_query
        conversation_history = data.conversation_history
        logger.debug(f"User utterance: {query}")
        logger.debug(f"Conversation history: {conversation_history}")
        mentions_assistant = self.mentions_assistant(query, conversation_history)
        if mentions_assistant:
            logger.info(
                "Follow up detected by the presence of an option choosen by the user in the conversation"
            )
            return FollowUpDetectionRunOutput(
                is_follow_up=mentions_assistant,
                metadata={"detection_type": "choosen_option"},
            )
        try:
            is_follow_up = self.detect_follow_up_using_llm(
                config.llm_client, query, conversation_history
            )
            logger.info("Follow up detected by using an LLM")
            return FollowUpDetectionRunOutput(
                is_follow_up=is_follow_up, metadata={"detection_type": "llm"}
            )
        except Exception as e:
            logger.exception("Error during follow-up processing")
            return FollowUpDetectionRunOutput(error=e)

    def mentions_assistant(
        self, query: str, conversation_history: List[Dict[str, Any]]
    ) -> bool:
        # condition 2: MATCHES OPTION FROM ASSISTANT MESSAGE
        labels = []
        for content in conversation_history[-1]["content"]:
            if _.get(content, "response_type") == "option":
                labels += [
                    _.get(option, "label", "").casefold().strip()
                    for option in _.get(content, "options", [])
                ]
                labels += [
                    _.get(option, "value.input.text", "").casefold().strip()
                    for option in _.get(content, "options", [])
                ]

        return query.casefold().strip() in labels

    def detect_follow_up_using_llm(
        self,
        llm_client: LLMClient,
        query: str,
        conversation_history: List[Dict],
    ) -> bool:
        # defer import to avoid circular dependency with follow_up_detection_toolkit.follow_up
        from altk.pre_llm.routing.follow_up_detection.follow_up import (
            FOLLOW_UP_PROMPT,
        )

        prompt_messages = copy.deepcopy(FOLLOW_UP_PROMPT)
        prompt_messages[1]["content"] = prompt_messages[1]["content"].format(
            query=query,
            conversation_history=self.format_conversation_history(conversation_history),
        )
        llm_output = llm_client.generate(prompt_messages)
        return "Same topic".casefold() in llm_output.strip().casefold()

    def format_conversation_history(self, messages: List[Dict]) -> str:
        history_str = "\n".join([format_msgs(msg) for msg in messages])

        last_chatbot_msg = history_str.rfind("CHATBOT:")
        if last_chatbot_msg != -1:
            history_str = (
                history_str[:last_chatbot_msg]
                + "LATEST CHATBOT MESSAGE:"
                + history_str[last_chatbot_msg + len("CHATBOT:") :]
            )
        return history_str
