"""Example of using ALTK with generic agent to check for silent errors.
This example uses the .env file in the root directory.
Copy the .env.example to .env and fill out the following variables:
ALTK_MODEL_NAME = anthropic/claude-sonnet-4-20250514
ANTHROPIC_API_KEY = *** anthropic api key ***

Note that this example will require installing langgraph, and langchain-anthropic.
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

from altk.post_tool.silent_review.silent_review import (
    SilentReviewForJSONDataComponent,
)
from altk.post_tool.core.toolkit import SilentReviewRunInput, Outcome
from altk.core.toolkit import AgentPhase

from dotenv import load_dotenv

load_dotenv()
warnings.filterwarnings("ignore", category=UserWarning)
retries = 0


@tool
def get_weather(city: str, state: Annotated[dict, InjectedState]) -> dict[str, str]:
    """Get weather for a given city."""
    global retries
    if random.random() >= (0.500 + retries * 0.25):
        # Simulates a silent error from an external service, less likely if retrying
        result = {"weather": "Weather service is under maintenance."}
    else:
        result = {"weather": f"It's sunny and {random.randint(50, 90)}F in {city}!"}

    return result


class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    next: str


def post_tool_hook(state: AgentState) -> AgentState:
    # Creates a post-tool node that reviews for silent errors
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

# Runs the agent, try running this multiple times to see the ALTK detect the silent error
result = agent.invoke({"messages": [HumanMessage(content="what is the weather in sf")]})
print(result["messages"][-1].content)
if retries > 0:
    print(f"(get_weather was retried: {retries} times)")
