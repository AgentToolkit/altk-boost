import logging

from pydantic import ValidationError
import pytest
from altk.pre_llm.routing.follow_up_detection.core.toolkit import (
    FollowUpDetectionRunInput,
    FollowUpDetectionRunOutput,
)
from altk.pre_llm.routing.follow_up_detection.follow_up import (
    DefaultMessages,
    FollowUpDetectionComponent,
)
from langchain_core.messages import AIMessage, HumanMessage
from altk.core.toolkit import (
    AgentPhase,
    ComponentConfig,
)


def test_basic_conversation(caplog, llm_client):
    caplog.set_level(logging.DEBUG, FollowUpDetectionComponent.__module__)
    follow_up_detection = FollowUpDetectionComponent(
        config=ComponentConfig(llm_client=llm_client)
    )
    follow_up_detection_result: FollowUpDetectionRunOutput = (
        follow_up_detection.process(
            data=FollowUpDetectionRunInput[DefaultMessages](
                conversation_history=[
                    HumanMessage(content="I need the total sales for one year?"),
                    AIMessage(content="For which year?"),
                ],
                user_query="2021",
            ),
            phase=AgentPhase.RUNTIME,
        )
    )
    assert follow_up_detection_result.is_follow_up
    assert follow_up_detection_result.metadata.get("detection_type") == "llm"

    follow_up_detection_result: FollowUpDetectionRunOutput = (
        follow_up_detection.process(
            data=FollowUpDetectionRunInput[DefaultMessages](
                conversation_history=[
                    HumanMessage(content="I need the total sales for one year?"),
                    AIMessage(content="For which year?"),
                ],
                user_query="forget about it",
            ),
            phase=AgentPhase.RUNTIME,
        )
    )
    assert not follow_up_detection_result.is_follow_up
    assert follow_up_detection_result.metadata.get("detection_type") == "llm"


def test_follow_up_detected_by_callback(caplog, llm_client):
    caplog.set_level(logging.DEBUG, FollowUpDetectionComponent.__module__)
    follow_up_detection = FollowUpDetectionComponent(
        config=ComponentConfig(llm_client=llm_client)
    )
    follow_up_detection_result: FollowUpDetectionRunOutput = (
        follow_up_detection.process(
            data=FollowUpDetectionRunInput[DefaultMessages](
                conversation_history=[
                    HumanMessage(content="I need the total sales for one year?"),
                    AIMessage(content="For which year?"),
                ],
                user_query="2021",
                detect_follow_up=lambda messages, user_query: user_query.isdigit()
                and user_query == "2021",
            ),
            phase=AgentPhase.RUNTIME,
        )
    )
    # The follow up was detected by calling the detect_follow_up callback provided by the caller
    assert follow_up_detection_result.is_follow_up
    assert (
        follow_up_detection_result.metadata.get("detection_type")
        == "detect_follow_up_callback"
    )


def test_invalid_conversation(caplog):
    caplog.set_level(logging.DEBUG, FollowUpDetectionComponent.__module__)

    with pytest.raises(ValidationError) as excinfo:
        _ = FollowUpDetectionRunInput[DefaultMessages](
            conversation_history=[], user_query=""
        )
    assert "List should have at least 1 item after validation" in str(excinfo.value)
    assert "String should have at least 1 character" in str(excinfo.value)
    assert excinfo.value.error_count() == 2
    assert "conversation_history" in excinfo.value.errors()[0].get("loc")
    assert "user_query" in excinfo.value.errors()[1].get("loc")
