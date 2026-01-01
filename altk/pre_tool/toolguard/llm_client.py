
from typing import Union, cast
from altk.core.llm.types import GenerationArgs
from ...core.llm import ValidatingLLMClient, LLMClient
from toolguard.llm.tg_litellm import LanguageModelBase


class TG_LLMEval(LanguageModelBase):
    def __init__(self, llm_client: Union[LLMClient, ValidatingLLMClient]):
        super().__init__(llm_client.get_model_id()) # type: ignore
        self.llm_client = llm_client

    async def generate(self, messages: list[dict]) -> str:
        if isinstance(self.llm_client, ValidatingLLMClient):
            llm_client = cast(ValidatingLLMClient, self.llm_client)
            return await llm_client.generate_async(
                prompt=messages, 
                schema=str, 
                generation_args = GenerationArgs(max_tokens=10000)
            )
        
        return await self.llm_client.generate_async(
            prompt=messages,
            generation_args = GenerationArgs(max_tokens=10000)
        ) # type: ignore
