from abc import ABC, abstractmethod
from typing import List, Dict


class I_TG_LLM(ABC):
    @abstractmethod
    async def chat_json(self, messages: List[Dict]) -> Dict:
        pass

    @abstractmethod
    async def generate(self, messages: List[Dict]) -> str:
        pass
