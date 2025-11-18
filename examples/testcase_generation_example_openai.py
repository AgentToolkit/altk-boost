from altk.core.toolkit import AgentPhase
from altk.build_time.test_case_generation_toolkit.core.toolkit import (
    TestCaseGenBuildInput,
)
from altk.build_time.test_case_generation_toolkit.utils.test_case_generation import (
    NLTestCaseGenComponent,
)
from altk.build_time.test_case_generation_toolkit.core.config import TestCaseGenConfig
from altk.core.llm import get_llm, GenerationMode
import os


def get_llm_client_obj(model_name="meta-llama/llama-3-3-70b-instruct"):
    openAIClient = get_llm("openai.sync")
    client = openAIClient(
        model=model_name,
        api_key=os.getenv("OPENAI_KEY"),
        base_url=os.getenv("OPENAI_URL"),
    )
    return client


def example_testcase_generation_with_toolkit(python_tool_str, config):
    test_case_gen_input = TestCaseGenBuildInput(python_tool_str=python_tool_str)
    test_case_generation_toolkit = NLTestCaseGenComponent()
    result = test_case_generation_toolkit.process(
        data=test_case_gen_input, config=config, phase=AgentPhase.BUILDTIME
    )
    return result


python_tool_str = '''import requests
from typing import Optional, Dict, Any
from langchain_core.tools import tool
from model_utils import load_github_token

@tool
def listIssues(owner: str, repo: str, requestBody: Optional[Dict[str, Any]] = None):
    """
    Get all the relevant issues.

    """
    token = load_github_token()
    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }

    response = requests.get(url, headers=headers, params=requestBody or {})
    response.raise_for_status()
    return response.json()'''

config = TestCaseGenConfig(
    llm_client=get_llm_client_obj(model_name="meta-llama/llama-3-3-70b-instruct"),
    gen_mode=GenerationMode.TEXT,
    max_nl_utterances=3,
    max_testcases=3,
    clean_nl_utterances=True,
    negative_test_cases=True,
)

result = example_testcase_generation_with_toolkit(python_tool_str, config)
print(result.nl_test_cases)
