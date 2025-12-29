
from ...core.llm import ValidatingLLMClient
from toolguard.llm.tg_litellm import LanguageModelBase


class TG_LLMEval(LanguageModelBase):
    def __init__(self, llm_client: ValidatingLLMClient):
        super().__init__(llm_client.get_model_id()) # type: ignore
        self.llm_client = llm_client

    async def generate(self, messages: list[dict]) -> str:
        return await self.llm_client.generate_async(
            prompt=messages, 
            schema=str, 
            params = {"max_tokens":10000}
        )
