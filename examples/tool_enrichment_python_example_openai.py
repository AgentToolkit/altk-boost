from altk.core.toolkit import AgentPhase
from altk.core.llm import get_llm, GenerationMode
from altk.build_time.tool_enrichment_toolkit.core.toolkit import (
    PythonToolEnrichBuildInput,
)
from altk.build_time.tool_enrichment_toolkit.utils.tool_enrichment import (
    PythonToolEnrichComponent,
)
from altk.build_time.tool_enrichment_toolkit.core.config import PythonToolEnrichConfig
import os


def get_llm_client_obj(model_name="meta-llama/llama-3-3-70b-instruct"):
    openAIClient = get_llm("openai.sync")
    client = openAIClient(
        model=model_name,
        api_key=os.getenv("OPENAI_KEY"),
        base_url=os.getenv("OPENAI_URL"),
    )
    return client


def example_tool_enrichment_with_toolkit(python_tool, config):
    tool_enrich_input = PythonToolEnrichBuildInput(python_tool=python_tool)

    tool_enrich_middleware = PythonToolEnrichComponent()
    result = tool_enrich_middleware.process(
        data=tool_enrich_input, config=config, phase=AgentPhase.BUILDTIME
    )
    return result


python_tool = '''import requests
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

config = PythonToolEnrichConfig(
    llm_client=get_llm_client_obj(model_name="meta-llama/llama-3-3-70b-instruct"),
    gen_mode=GenerationMode.TEXT,
    enable_tool_description_enrichment=True,
    enable_tool_parameter_description_enrichment=True,
    enable_tool_return_description_enrichment=True,
    enable_tool_example_enrichment=True,
)

result = example_tool_enrichment_with_toolkit(python_tool, config)
print(result.enriched_python_tool)
