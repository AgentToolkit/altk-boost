import copy
import logging
from typing import Annotated, Set, cast

from altk.pre_llm.routing.follow_up_detection.core.toolkit import (
    FollowUpDetectionRunInput,
    FollowUpDetectionRunOutput,
)
from altk.core.toolkit import (
    AgentPhase,
    ComponentBase,
    ComponentConfig,
)
from altk.core.llm.base import LLMClient
from pydantic import ConfigDict, Field
from altk.pre_llm.routing.follow_up_detection.core.toolkit import (
    FollowUpDetector,
)
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage


logger = logging.getLogger(__name__)

FOLLOW_UP_PROMPT = [
    {
        "content": "Your task is to determine if the latest message from a user is continuing the conversation between the user and a chatbot, or if it signifies a new topic.",
        "role": "system",
    },
    {
        "content": """
Output either 'Same topic' or 'New topic'. If the LATEST CHATBOT MESSAGE is requesting broad information from the user, such as a name, id, title, you should always say 'Same topic'. Output only either 'Same topic' or 'New topic'.

Conversational context:
{conversation_history}

Now output the answer for the following query
LATEST USER MESSAGE: {query}
""",
        "role": "user",
    },
]

DefaultMessages = Annotated[list[BaseMessage], Field(min_length=1)]


class DefaultFollowUpDetector:
    def detect_follow_up(
        self,
        config: ComponentConfig,
        data: FollowUpDetectionRunInput[DefaultMessages],
    ) -> FollowUpDetectionRunOutput:
        try:
            user_utterance = data.user_query
            conversation_history = self.get_conversation_history(
                data.conversation_history
            )
            logger.debug(f"User utterance: {user_utterance}")
            logger.debug(f"Conversation history: {conversation_history}")
            llm_client = cast(LLMClient, config.llm_client)
            prompt_messages = copy.deepcopy(FOLLOW_UP_PROMPT)
            prompt_messages[1]["content"] = prompt_messages[1]["content"].format(
                query=user_utterance, conversation_history=conversation_history
            )
            llm_output = llm_client.generate(prompt_messages)
            return FollowUpDetectionRunOutput(
                is_follow_up="Same topic".casefold() in llm_output.strip().casefold(),
                metadata={"detection_type": "llm"},
            )
        except Exception as e:
            return FollowUpDetectionRunOutput(error=e)

    def get_conversation_history(self, messages: list[BaseMessage]) -> str:
        def format_message(
            message: BaseMessage, last_chatbot_message: bool = False
        ) -> str:
            formatted_message = ""
            if isinstance(message, HumanMessage):
                formatted_message = f"USER: {message.content}"
            elif isinstance(message, AIMessage) and not last_chatbot_message:
                formatted_message = f"CHATBOT: {message.content}"
            elif isinstance(message, AIMessage) and last_chatbot_message:
                formatted_message = f"LATEST CHATBOT MESSAGE: {message.content}"
            else:
                logger.warning(
                    f"Message '{message.content}' is neither a HumanMessage or AIMessage, formatting it as an empty string."
                )
            return formatted_message

        return "\n".join(
            [
                format_message(message, i == len(messages) - 1)
                for i, message in enumerate(messages)
            ]
        )


class FollowUpDetectionComponent(ComponentBase):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    follow_up_detector: FollowUpDetector = DefaultFollowUpDetector()

    @classmethod
    def supported_phases(cls) -> Set[AgentPhase]:
        return {AgentPhase.RUNTIME}

    def _run(self, data: FollowUpDetectionRunInput) -> FollowUpDetectionRunOutput:
        if not self.config:
            raise ValueError(
                "Follow up detection component not configured. A `Config` object with an instance of `LLMClient` needs to be passed when creating the FollowUpDetectionComponent object."
            )
        is_follow_up = False
        if data.detect_follow_up:
            is_follow_up = data.detect_follow_up(
                data.conversation_history, data.user_query
            )
        if is_follow_up:
            return FollowUpDetectionRunOutput(
                is_follow_up=is_follow_up,
                metadata={"detection_type": "detect_follow_up_callback"},
            )
        else:
            return self.follow_up_detector.detect_follow_up(self.config, data)
