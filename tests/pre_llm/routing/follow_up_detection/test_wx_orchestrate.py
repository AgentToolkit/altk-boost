import logging

import pytest
from altk.pre_llm.routing.follow_up_detection.core.toolkit import (
    FollowUpDetectionRunInput,
    FollowUpDetectionRunOutput,
)
from altk.pre_llm.routing.follow_up_detection.follow_up import (
    FollowUpDetectionComponent,
)
from altk.pre_llm.routing.follow_up_detection.wx_orchestrate import (
    WxOrchestrateFollowUpDetector,
    WxOrchestrateMessages,
)
from altk.core.toolkit import AgentPhase, ComponentConfig
from pydantic import ValidationError


def test_basic_conversation(caplog, llm_client):
    caplog.set_level(logging.DEBUG, FollowUpDetectionComponent.__module__)
    caplog.set_level(logging.DEBUG, WxOrchestrateFollowUpDetector.__module__)
    follow_up_detection = FollowUpDetectionComponent(
        config=ComponentConfig(llm_client=llm_client),
        follow_up_detector=WxOrchestrateFollowUpDetector(),
    )
    follow_up_detection_result: FollowUpDetectionRunOutput = follow_up_detection.process(
        data=FollowUpDetectionRunInput[WxOrchestrateMessages](
            conversation_history=[
                {
                    "role": "user",
                    "content": [
                        {
                            "response_type": "text",
                            "text": "how do i make an opportunity",
                        }
                    ],
                },
                {
                    "role": "assistant",
                    "content": [
                        {
                            "response_type": "text",
                            "text": "\n\n### Creating an Opportunity in IBM Sales Cloud (ISC)\n\nTo create an opportunity in IBM Sales Cloud (ISC), follow these steps:\n\n1. **Create a new opportunity**: Click on 'New' in the 'My Opportunities' section.\n2. **Fill in the necessary details**: Enter the opportunity name, select the account, add the sales stage, and input the closing date. Click save.\n3. **Add a product**: Scroll down to the 'Products' section and click 'Add Products.' Search for the product in the catalog, ensuring it's part of the SW Services product family.\n4. **Complete product details**: Enter the estimated total revenue, term, classification, and type code.\n5. **Add 'Data Observability by Databand' product**: Search for 'Data Observability by Databand' and select either 'SW Subscription' or 'SaaS' depending on the customer scenario.\n6. **Complete additional features**: In the 'Additional Features' section, select 'Data Observability.'\n7. **Add opportunity team members**: For an Americas opportunity, add Rodney Cobb; for EMEA, add Sonia Batanero; for APAC and Japan, add Brian Mayer.\n\n\nFor more detailed instructions and variations based on specific products or scenarios, refer to the following resources:\n* [Creating a Databand Opportunity in ISC](https://ibm.seismic.com/Link/Content/DCqmJDP6HVW7pGCFp887M9W7D8mV)\n* [Input Offering Type in ISC -transcript - 2023-Aug-28](https://ibm.seismic.com/Link/Content/DCWPJQd2M2q6m89JFM2HQ6PW9C78)",
                            "format": {"use_padding": True},
                            "streaming_metadata": {
                                "id": 1,
                                "stream_id": "72c986e2-9de7-4811-bb0f-04658374a712",
                            },
                        },
                        {
                            "response_type": "user_defined",
                            "user_defined": {
                                "user_defined_type": "sales-assets-rag",
                                "is_everyone_social_enabled": False,
                            },
                            "repeat_on_reprompt": False,
                            "streaming_metadata": {"id": 2},
                        },
                        {
                            "response_type": "user_defined",
                            "user_defined": {
                                "no_label": "👎🏼",
                                "yes_label": "👍🏼",
                                "issue_options": [
                                    "Partial Answer",
                                    "Wrong No Source",
                                    "Format Style Issues",
                                    "Incorrect Response",
                                    "Expected Tabular Response",
                                    "Other Issues",
                                ],
                                "place_holder_text": "",
                                "user_defined_type": "custom_feedback",
                                "custom_user_defined_type": "custom_feedback",
                                "text_on_negative_feedback": "Thank you for your feedback!",
                                "text_on_positive_feedback": "Thank you for your feedback!",
                                "slack_notification_channel": "ibmSales",
                                "slack_negative_greeting_message": "Dear SMEs \n\n Please review the following interaction to identify potential areas for improvement",
                                "slack_positive_greeting_message": "Hooray :party_1:, user liked the assistant response :tada:",
                            },
                            "streaming_metadata": {"id": 3},
                        },
                    ],
                },
            ],
            user_query="Partial Answer",
        ),
        phase=AgentPhase.RUNTIME,
    )
    assert follow_up_detection_result.is_follow_up
    assert follow_up_detection_result.metadata.get("detection_type") == "llm"


def test_conversation_with_mention_to_assistant(caplog, llm_client):
    caplog.set_level(logging.DEBUG, FollowUpDetectionComponent.__module__)
    caplog.set_level(logging.DEBUG, WxOrchestrateFollowUpDetector.__module__)
    follow_up_detection = FollowUpDetectionComponent(
        config=ComponentConfig(llm_client=llm_client),
        follow_up_detector=WxOrchestrateFollowUpDetector(),
    )
    follow_up_detection_result: FollowUpDetectionRunOutput = follow_up_detection.process(
        data=FollowUpDetectionRunInput[WxOrchestrateMessages](
            conversation_history=[
                {
                    "role": "user",
                    "content": [
                        {
                            "response_type": "text",
                            "text": "what is ibm water policy",
                        }
                    ],
                },
                {
                    "role": "assistant",
                    "content": [
                        {
                            "response_type": "text",
                            "text": "Thanks!\xa0Before I answer, it would be helpful for me if you could share some of the below information about the deal.",
                        },
                        {
                            "response_type": "text",
                            "text": "Which of the below can you share?",
                            "repeat_on_reprompt": False,
                        },
                        {
                            "response_type": "option",
                            "options": [
                                {
                                    "label": "ISC Opportunity ID",
                                    "value": {"input": {"text": "ISC Opportunity ID"}},
                                },
                                {
                                    "label": "ISC Account ID",
                                    "value": {"input": {"text": "ISC Account ID"}},
                                },
                                {
                                    "label": "Domestic Buying Group ID",
                                    "value": {
                                        "input": {"text": "Domestic Buying Group ID"}
                                    },
                                },
                                {
                                    "label": "Domestic Client ID",
                                    "value": {"input": {"text": "Domestic Client ID"}},
                                },
                                {
                                    "label": "Not related to an opportunity",
                                    "value": {
                                        "input": {
                                            "text": "Not related to an opportunity"
                                        }
                                    },
                                },
                            ],
                            "repeat_on_reprompt": True,
                        },
                    ],
                },
            ],
            user_query="Domestic Client ID",
        ),
        phase=AgentPhase.RUNTIME,
    )
    assert follow_up_detection_result.is_follow_up
    assert follow_up_detection_result.metadata.get("detection_type") == "choosen_option"


def test_invalid_conversation_history():
    with pytest.raises(ValueError) as excinfo:
        FollowUpDetectionRunInput[WxOrchestrateMessages](
            conversation_history=[
                {
                    "role": "user",
                    "content": [
                        {
                            "response_type": "text",
                            "text": "what is ibm water policy",
                        }
                    ],
                },
            ],
            user_query="Hi",
        )
    assert (
        "Last message from the conversation history must be an assistant message."
        in str(excinfo.value)
    )

    with pytest.raises(ValidationError) as excinfo:
        _ = FollowUpDetectionRunInput[WxOrchestrateMessages](
            conversation_history=[],
            user_query="Domestic Client ID",
        )
    assert "List should have at least 1 item after validation, not 0" in str(
        excinfo.value
    )
    assert excinfo.value.error_count() == 1
    assert "conversation_history" in excinfo.value.errors()[0].get("loc")

    with pytest.raises(ValueError) as excinfo:
        _ = FollowUpDetectionRunInput[WxOrchestrateMessages](
            conversation_history=[{}],
            user_query="Hi",
        )
    assert "Messages must contain 'role' and 'content' keys" in str(excinfo.value)

    with pytest.raises(ValueError) as excinfo:
        _ = FollowUpDetectionRunInput[WxOrchestrateMessages](
            conversation_history=[{"role": "user", "content": "Hi"}],
            user_query="Hi",
        )
    assert "Message 'content' key must be a list" in str(excinfo.value)
