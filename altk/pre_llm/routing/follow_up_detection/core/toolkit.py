from typing import (
    Any,
    Callable,
    Generic,
    Optional,
    Protocol,
    TypeVar,
    runtime_checkable,
)
from altk.core.toolkit import (
    ComponentConfig,
    ComponentInput,
    ComponentOutput,
)
from pydantic import ConfigDict, Field


class FollowUpDetectionRunOutput(ComponentOutput):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    is_follow_up: bool | None = Field(
        description="Flag indicating if the last message in a conversation is a follow up or not",
        default=None,
    )
    metadata: dict[str, Any] = Field(
        description="Field containing metadata fields with follow-up detector specific information.",
        default_factory=dict,
    )
    error: Optional[Exception] = Field(
        description="If there was an error running the component this field contains the Python Exception object that was raised.",
        default=None,
    )


M = TypeVar("M")


class FollowUpDetectionRunInput(ComponentInput, Generic[M]):
    """Contains the input needed for a follow up detection.
    The generic type "M" can be instantiated by the follow up detector implementation with the type of the messages the implementation handles.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)
    detect_follow_up: Callable[[M, str], bool] | None = Field(
        description="Callable that receives a list of messages with the conversation history, the user query, and returns a flag indicating if the user query is a follow up question.",
        default=None,
    )
    conversation_history: M = Field(
        description="Messages with the conversation history. The follow up detector implementation instantiates the generic type with the actual type that represents the conversation history."
    )
    user_query: str = Field(description="The user query", min_length=1)


@runtime_checkable  # see https://github.com/pydantic/pydantic/discussions/5767#discussioncomment-5919490
class FollowUpDetector(Protocol):
    def detect_follow_up(
        self, config: ComponentConfig, data: FollowUpDetectionRunInput
    ) -> FollowUpDetectionRunOutput: ...
