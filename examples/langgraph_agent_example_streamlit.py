"""Example of using ALTK with generic agent to check for silent errors.
This example uses the .env file in the root directory.
Copy the .env.example to .env and fill out the following variables:
ALTK_MODEL_NAME = anthropic/claude-sonnet-4-20250514
ANTHROPIC_API_KEY = *** anthropic api key ***

Note that this example will require installing streamilt, langgraph, and langchain-anthropic.
Execute this demo with `streamlit run langgraph_agent_example_streamlit.py`
"""

import random
import warnings
import json

from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, START, END
from langchain_core.tools import tool
from typing_extensions import Annotated
from langgraph.prebuilt import ToolNode
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.messages.base import messages_to_dict
import operator
from typing import TypedDict, List
from langgraph.prebuilt import InjectedState
import streamlit as st

from altk.post_tool.silent_review.silent_review import (
    SilentReviewForJSONDataComponent,
)
from altk.post_tool.core.toolkit import SilentReviewRunInput, Outcome
from altk.core.toolkit import AgentPhase

from dotenv import load_dotenv

warnings.filterwarnings("ignore", category=UserWarning)
load_dotenv()
tool_silent_error_raised = False
silent_error_raised = False
retries = 0


@tool
def get_weather(city: str, state: Annotated[dict, InjectedState]) -> dict[str, str]:
    """Get weather for a given city."""
    global retries
    if random.random() >= (0.500 + retries * 0.25):
        # Simulates a silent error from an external service, less likely if retrying
        result = {"weather": "Weather service is under maintenance."}
        global tool_silent_error_raised
        tool_silent_error_raised = True
    else:
        result = {"weather": f"It's sunny and {random.randint(50, 90)}F in {city}!"}

    return result


class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    next: str


def post_tool_hook(state: AgentState) -> AgentState:
    # Creates a post-tool node that reviews for silent errors
    if use_silent_review:
        global retries
        tool_response = json.loads(state["messages"][-1].content)
        # Use SilentReview component to check if it's a silent error
        review_input = SilentReviewRunInput(
            messages=messages_to_dict(state["messages"]), tool_response=tool_response
        )
        reviewer = SilentReviewForJSONDataComponent()
        review_result = reviewer.process(data=review_input, phase=AgentPhase.RUNTIME)
        if review_result.outcome == Outcome.NOT_ACCOMPLISHED:
            # Agent should retry tool call if silent error was detected
            print("(ALTK: Silent error detected, retry the get_weather tool!)")
            retries += 1
            global silent_error_raised
            silent_error_raised = True
            return {
                "next": "agent",
                "messages": [
                    HumanMessage(
                        content="!!! Silent error detected, RETRY the get_weather tool !!!"
                    )
                ],
            }
        else:
            return {"next": "final_message"}
    else:
        return {"next": "final_message"}


def final_message_node(state):
    return state


tools = [get_weather]
llm = ChatAnthropic(model="claude-sonnet-4-20250514")
llm_with_tools = llm.bind_tools(tools, tool_choice="get_weather")


def call_model(state: AgentState):
    messages = state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


# creates agent with pre-tool node that conditionally goes to tool node
builder = StateGraph(AgentState)
builder.add_node("agent", call_model)
builder.add_node("call_tool", ToolNode(tools))
builder.add_node("post_tool_hook", post_tool_hook)
builder.add_node("final_message", final_message_node)
builder.add_edge(START, "agent")
builder.add_conditional_edges(
    "agent",
    lambda state: "call_tool" if state["messages"][-1].tool_calls else "final_message",
    {"call_tool": "call_tool", "final_message": "final_message"},
)
builder.add_edge("call_tool", "post_tool_hook")
builder.add_conditional_edges(
    "post_tool_hook",
    lambda state: state["next"],
    {"agent": "agent", "final_message": "final_message"},
)
builder.add_edge("final_message", END)
agent = builder.compile()


st.title("ALTK Chatbot example with Silent Error Review")
st.markdown(
    "This demo demonstrates using the ALTK to check for silent errors on an agent. The weather service will randomly silently fail. \
            \n- With Silent Error Review, the silent error is detected and then the agent is suggested to retry. \
            \n- Without Silent Review, the agent fails."
)

use_silent_review = st.checkbox("Use Silent Error Review")

if "messages" not in st.session_state:
    st.session_state.messages = []

if prompt := st.chat_input(
    "I can tell you the weather in a given city. But my weather service is being spotty..."
):
    with st.chat_message("user"):
        st.markdown(prompt)

    st.session_state.messages.append(HumanMessage(content=prompt))

    with st.chat_message("assistant"):
        inputs = {"messages": [HumanMessage(content=prompt)]}
        result = agent.invoke(inputs)

        if tool_silent_error_raised:
            with st.chat_message("tool"):
                st.write("Weather service: (Weather service is under maintenance.)")

        if silent_error_raised:
            with st.chat_message("altk"):
                st.write(
                    "ALTK: (Silent error detected, suggest agent to retry the get_weather tool.)"
                )

        response = f"Agent response : {result['messages'][-1].content} \n"
        if retries > 0:
            response += f"\n(number of retries: {retries})"
        st_response = st.write(response)
    st.session_state.messages.append({"role": "assistant", "content": response})
