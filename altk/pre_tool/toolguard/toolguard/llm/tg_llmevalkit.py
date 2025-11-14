from altk.pre_tool.toolguard.toolguard.llm.i_tg_llm import I_TG_LLM
from altk.core.llm import ValidatingLLMClient


class TG_LLMEval(I_TG_LLM):
    def __init__(self, llm_client: ValidatingLLMClient):
        if not isinstance(llm_client, ValidatingLLMClient):
            print("llm_client is a ValidatingLLMClient")
            exit(1)
        self.llm_client = llm_client

    async def chat_json(self, messages: list[dict], schema=dict) -> dict:
        return self.llm_client.generate(
            prompt=messages, schema=schema, retries=5, schema_field=None
        )

    async def generate(self, messages: list[dict]) -> str:
        return self.llm_client.generate(
            prompt=messages, schema=str, retries=5, schema_field=None
        )
