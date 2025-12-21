from collections import defaultdict
import copy
from dataclasses import dataclass
import json
import logging
import os
import time
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from altk.pre_llm.core.types import TopicExtractionBuildOutput, TopicInfo
from altk.pre_llm.core.types import (
    ContentProvider,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.topic_extractor.settings import (
    LLMTopicExtractorSettings,
    TopicExtractionSettings,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.topic_extractor.topic_extractor import (
    remove_dup_topics,
)
from altk.core.llm import LLMClient, get_llm

logger = logging.getLogger(__name__)
PROMPT_TOPICS_MESSAGES = [
    {
        "role": "system",
        "content": "You are an agent who reads a portion of a document and generates a list of concepts or topics that are described in the document",
    },
    {
        "role": "user",
        "content": """
Your task is to identify up to 20 concepts that are referenced in a document below.
A concept is a phrase (3-7 words) that could be a topic, entity (proper name, such as a person, product or service), or a phrase/concept someone might talk about.

You should output the concepts that the document has the most expertise in and teaches you the most about.  Don't output concepts the document knows nothing about.

Now here is your actual document to analyize
<BEGIN DOCUMENT>
{document}
<END DOCUMENT>

Now output your list of concepts.  The format should be a JSON array on a single line. Output no other commentary or line feeds.  If there are no concepts, output an empty array. And they must be at least 3 words long
""",
    },
]
PROMPT_CATEGORIZE_TOPICS_MESSAGES = [
    {
        "role": "system",
        "content": "You are an agent who reads a portion of a document and a list of topics, and categorizes the expertise of that document on each topic.",
    },
    {
        "role": "user",
        "content": """
Your task is to read (a) a list of concepts/topics/topic phrases, and (b) a document, and then categorize the documents level of expertise on each of the concepts from (a)

You must choose from 3 categories of expertise:

1. Expert:  the document is clearly explains and defines the concept or topic. It does not need to mention it by name, but it clearly teaches a lot about that topic
2. Knowledge:  the document conveys information about the topic beyond just mentioning its name.  You learn something about that concept by reading the document.
3. Mentions:  the document mentions the topic one or more times, but you don't learn a lot about it


Here are is your list of topics to categorize:
{topics}

Now here is your document to analyize
<BEGIN DOCUMENT>
{document}
<END DOCUMENT>

Now output your categorization of each of the topics above, in order.  Output your assessment in a JSON array, on a single line with no commenttary or additional line feeds.   Each element of the array contain only the assessment ("Expert", "Knowledge", "Mentions") for each topic above. Do not repeat the topic in the assessment array. If you are given an empty array of topics, output an empty array.
""",
    },
]


@dataclass
class TopicExtractionResult:
    topics: Optional[List[TopicInfo]] = None
    error: Optional[str] = None


class ChunkStat(BaseModel):
    topics: Optional[List[TopicInfo]] = None
    extraction_time: Optional[float] = None
    error: Optional[str] = None


class LLMTopicExtractorOutput(BaseModel):
    chunk_stats: Dict[int, ChunkStat] = Field(
        default_factory=lambda: defaultdict(ChunkStat)
    )
    chunks_processed: int = 0


class LLMTopicExtractor(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    content_provider: ContentProvider
    # model_id: str
    # provider: Literal["litellm.rits", "watsonx", "litellm.watsonx"] = "watsonx"
    llm_client: LLMClient
    levels_of_expertise: bool = True

    @classmethod
    def from_settings(
        cls,
        settings: LLMTopicExtractorSettings | Dict,
        topic_extraction_settings: TopicExtractionSettings | None = None,
    ) -> "LLMTopicExtractor":
        from altk.pre_llm.routing.retrieval_augmented_thinking.topic_extractor.topic_extractor import (
            CONTENT_PROVIDERS,
        )

        _settings = (
            LLMTopicExtractorSettings(**settings)
            if isinstance(settings, Dict)
            else settings
        )
        if _settings.content_provider.name not in CONTENT_PROVIDERS:
            raise ValueError(
                f"Unregistered ContentProvider implementation {_settings.content_provider.name}"
            )
        factory_method = getattr(
            CONTENT_PROVIDERS[_settings.content_provider.name],
            "create_content_provider",
            None,
        )
        if not factory_method:
            raise ValueError(
                f"ContentProvider implementation {CONTENT_PROVIDERS[_settings.content_provider.name]} is missing the class method create_content_provider"
            )
        content_provider: ContentProvider = factory_method(
            _settings.content_provider.config
        )
        llm_client = _settings.llm_client or (
            topic_extraction_settings.llm_client if topic_extraction_settings else None
        )
        if not llm_client:
            if not _settings.llm:
                raise ValueError(
                    "If an LLMClient instance is not provided the settings object must include LLM settings in the `llm` field"
                )
            if _settings.llm.provider == "litellm.rits":
                # Basic RITS LiteLLM clients
                RITSLiteLLMClient = get_llm("litellm.rits")

                llm_client = RITSLiteLLMClient(
                    model_name=_settings.llm.model_id,
                    model_url=_settings.llm.model_id.split("/")[1]
                    .replace(".", "-")
                    .lower(),  # Llama-3.1-8B-Instruct -> llama-3-1-8b-instruct
                    # hooks=[lambda event, payload: print(f"[RITS] {event}: {payload}")],
                )
            elif _settings.llm.provider == "watsonx":
                WatsonXAIClient = get_llm("watsonx")
                llm_client = WatsonXAIClient(
                    model_id=_settings.llm.model_id,
                    api_key=_settings.llm.provider_config.get("api_key")
                    or os.getenv("WX_API_KEY"),
                    project_id=_settings.llm.provider_config.get("project_id")
                    or os.getenv("WX_PROJECT_ID"),
                    url=_settings.llm.provider_config.get("url") or os.getenv("WX_URL"),
                    # hooks=[lambda event, payload: print(f"[SYNC HOOK] {event}: {payload}")],
                )
            elif _settings.llm.provider == "litellm.watsonx":
                WatsonXLiteLLMClient = get_llm("litellm.watsonx")

                llm_client = WatsonXLiteLLMClient(
                    model_name=_settings.llm.model_id,
                    # hooks=[lambda event, payload: print(f"[SYNC HOOK] {event}: {payload}")],
                )
            else:
                raise ValueError(
                    f"Unsupported model provider: {_settings.llm.provider}. "
                    "Supported model providers from the LLM Client Library: "
                    "'litellm.rits', 'watsonx' and 'litellm.watsonx'"
                )

        return cls(
            content_provider=content_provider,
            llm_client=llm_client,
            levels_of_expertise=_settings.levels_of_expertise,
        )

    def extract_topics(
        self, subject, input: Optional[BaseModel] = None
    ) -> TopicExtractionBuildOutput[LLMTopicExtractorOutput]:
        topic_extractor_output = LLMTopicExtractorOutput()
        result = TopicExtractionBuildOutput[LLMTopicExtractorOutput](
            topic_extractor_output=topic_extractor_output
        )
        try:
            for chunk in self.content_provider.get_content():
                logger.info(
                    f"Extracting topics for {subject} #{topic_extractor_output.chunks_processed}:\n{chunk}"
                )
                start = time.time()
                topic_extraction_result = self.extract_topics_from_content(
                    chunk,
                    subject,
                    self.llm_client,
                    self.levels_of_expertise,
                )
                self._set_extraction_time(topic_extractor_output, time.time() - start)
                if not topic_extraction_result.error:
                    self._set_topics_extracted(
                        topic_extractor_output, topic_extraction_result.topics
                    )
                    logger.info(
                        f"{len(topic_extraction_result.topics)} topics extracted from chunk #{topic_extractor_output.chunks_processed} for {subject} in {self._get_extraction_time(topic_extractor_output): .2f} secs."
                    )
                    deduped_topics = remove_dup_topics(topic_extraction_result.topics)
                    start = time.time()
                    if deduped_topics:
                        self._add_topics(result, deduped_topics)
                    else:
                        logger.warning(
                            f"Could not extract any topics from chunk #{topic_extractor_output.chunks_processed}"
                        )
                else:
                    self._set_chunk_error(
                        topic_extractor_output, topic_extraction_result.error
                    )
                    logger.warning(
                        f"No topics could be extracted from chunk #{topic_extractor_output.chunks_processed} for {subject}"
                    )
                self._new_chunk_processed(topic_extractor_output)
            return result
        except Exception as e:
            logger.exception("Error processing chunks")
            result.error = e
            return result

    def extract_topics_from_content(
        self,
        chunk: str,
        subject: str,
        llm: LLMClient,
        levels_of_expertise: bool = True,
    ) -> TopicExtractionResult:
        messages = copy.deepcopy(PROMPT_TOPICS_MESSAGES)
        messages[1]["content"] = messages[1]["content"].format(document=chunk)
        json_str = llm.generate(messages)
        try:
            topics = json.loads(json_str)
            logger.debug(f"Extracted topics {json_str}")
            if not isinstance(topics, List) or not all(
                [isinstance(topic, str) for topic in topics]
            ):
                return TopicExtractionResult(
                    error=f"Topics returned by the LLM should be an array of strings, the LLM returned this value instead {json_str}"
                )
        except json.JSONDecodeError:
            logger.warning(f"LLM returned a non json string {json_str!r}")
            return TopicExtractionResult(
                error=f"LLM returned a non json string {json_str!r}"
            )
        if levels_of_expertise:
            try:
                messages = copy.deepcopy(PROMPT_CATEGORIZE_TOPICS_MESSAGES)
                messages[1]["content"] = messages[1]["content"].format(
                    document=chunk, topics=json_str
                )
                json_str = llm.generate(messages)
                try:
                    expertises = json.loads(json_str)
                    logger.debug(
                        f"Generated levels of expertise for each topic {json_str}"
                    )
                    if not isinstance(expertises, List) or not all(
                        [
                            isinstance(level_of_expertise, str)
                            for level_of_expertise in expertises
                        ]
                    ):
                        return TopicExtractionResult(
                            error=f"Levels of expertises returned by the LLM should be an array of strings, the LLM returned this value instead {json_str}"
                        )
                except json.JSONDecodeError:
                    logger.warning(f"LLM returned a non json string {json_str!r}")
                    return TopicExtractionResult(
                        error=f"LLM returned a non json string {json_str!r}"
                    )
                return TopicExtractionResult(
                    [
                        TopicInfo(
                            topic=topic,
                            expertise=expertise.lower(),
                            subject=subject,
                        )
                        for topic, expertise in zip(topics, expertises)
                    ]
                )
            except ValidationError as e:
                logging.error(e)
                return TopicExtractionResult(
                    error=f"Error creating TopicInfo object: {e}"
                )
        else:
            return TopicExtractionResult(
                [TopicInfo(topic=topic, subject=subject) for topic in topics]
            )

    def _set_chunk_error(self, output: LLMTopicExtractorOutput, error: str):
        output.chunk_stats[output.chunks_processed].error = error

    def _set_extraction_time(self, output: LLMTopicExtractorOutput, time: float):
        output.chunk_stats[output.chunks_processed].extraction_time = time

    def _get_extraction_time(self, output: LLMTopicExtractorOutput) -> float | None:
        return output.chunk_stats[output.chunks_processed].extraction_time

    def _set_topics_extracted(
        self, output: LLMTopicExtractorOutput, topics: List[TopicInfo]
    ):
        output.chunk_stats[output.chunks_processed].topics = topics

    def _new_chunk_processed(self, output: LLMTopicExtractorOutput):
        output.chunks_processed += 1

    def _add_topics(
        self,
        output: TopicExtractionBuildOutput[LLMTopicExtractorOutput],
        topics: List[TopicInfo],
    ):
        output.topics.extend(topics)
