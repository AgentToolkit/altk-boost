from typing import Any, Dict, Literal, List
from altk.core.toolkit import ComponentConfig
from altk.core.llm import LLMClient
from pydantic import BaseModel, ConfigDict, Field


class ContentProviderSettings(BaseModel):
    name: str
    config: Dict | BaseModel


class TopicSinkSettings(BaseModel):
    name: str
    config: Dict | BaseModel


class TopicExtractorSettings(BaseModel):
    name: Literal["llm", "bertopic", "tfidf_words"]
    config: Dict | BaseModel | None = None


class TopicExtractionSettings(ComponentConfig):
    # Some topic extractors used by this component don't need an LLMClient so that setting
    # should be optional, but the llm_client is required in the ComponentConfig superclass.
    # So this is a hack to turn the llm_client from ComponentConfig into an optional variable,
    # until that is changed in the superclass.
    llm_client: LLMClient | None = None
    subject: str
    topics_sink: TopicSinkSettings | None = None
    topic_extractor: TopicExtractorSettings


class MultipleTopicExtractionSettings(BaseModel):
    topic_extractors: List[TopicExtractionSettings]
    topics_sink: TopicSinkSettings


class LLMSettings(BaseModel):
    model_id: str
    provider: Literal["litellm.rits", "watsonx", "litellm.watsonx"] = "watsonx"
    provider_config: Dict[str, Any] = Field(
        description="LLM provider settings", default_factory=dict
    )


class LLMTopicExtractorSettings(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    content_provider: ContentProviderSettings
    llm: LLMSettings | None = None
    levels_of_expertise: bool = True
    llm_client: LLMClient | None = None
