from typing import Union, cast
from toolguard.buildtime.llm.tg_litellm import LanguageModelBase
from altk.core.llm.types import GenerationArgs
from altk.core.llm import ValidatingLLMClient, LLMClient

MAX_TOKENS = 16000  # min of claude4, oss, gpt 4o, ...


class TG_LLMClient(LanguageModelBase):
    def __init__(self, llm_client: Union[LLMClient, ValidatingLLMClient]):
        self.llm_client = llm_client

    async def generate(self, messages: list[dict]) -> str:
        if isinstance(self.llm_client, ValidatingLLMClient):
            llm_client = cast(ValidatingLLMClient, self.llm_client)
            return await llm_client.generate_async(
                prompt=messages,
                schema=str,
                generation_args=GenerationArgs(max_tokens=MAX_TOKENS),
            )

        return await self.llm_client.generate_async(
            prompt=messages, generation_args=GenerationArgs(max_tokens=MAX_TOKENS)
        )  # type: ignore
