import logging
from typing import (
    Dict,
    Generic,
    List,
    Optional,
    Protocol,
    Set,
    Type,
    TypeVar,
    runtime_checkable,
)
from altk.core.toolkit import AgentPhase, ComponentBase, ComponentInput
from pydantic import ConfigDict
from altk.pre_llm.core.types import TopicExtractionBuildOutput, TopicInfo, TopicsSink
from altk.pre_llm.core.types import (
    ContentProvider,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.topic_extractor.settings import (
    TopicExtractionSettings,
)

logger = logging.getLogger(__name__)


CONTENT_PROVIDERS: Dict[str, Type[ContentProvider]] = {}
TOPICS_SINKS: Dict[str, Type[TopicsSink]] = {}

InputType = TypeVar("InputType", bound=ComponentInput)
OutputType = TypeVar("OutputType")


@runtime_checkable  # see https://github.com/pydantic/pydantic/discussions/5767#discussioncomment-5919490
class TopicExtractor(Generic[InputType, OutputType], Protocol):
    def extract_topics(
        self, subject: str, input: Optional[InputType]
    ) -> TopicExtractionBuildOutput[OutputType]: ...


class TopicExtractionMiddleware(ComponentBase, Generic[InputType, OutputType]):
    """
    Extracts topics of expertise using a `TopicExtractor`
    and stores them using the `TopicsSink`. The extracted topics belong to a subject
    that is set to the `subject` field in each topic.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)
    subject: str
    topics_sink: TopicsSink | None = None
    topic_extractor: TopicExtractor[InputType, OutputType]

    @classmethod
    def from_settings(
        cls, settings: TopicExtractionSettings
    ) -> "TopicExtractionMiddleware":
        topics_sink: TopicsSink = None
        if settings.topics_sink:
            if settings.topics_sink.name not in TOPICS_SINKS:
                raise ValueError(
                    f"Unregistered TopicsSink implementation {settings.topics_sink.name}"
                )
            factory_method = getattr(
                TOPICS_SINKS[settings.topics_sink.name],
                "create_topics_sink",
                None,
            )
            if not factory_method:
                raise ValueError(
                    f"TopicsSink implementation {TOPICS_SINKS[settings.topics_sink.name]} is missing the class method from_topics_sink_settings"
                )
            topics_sink = factory_method(settings.topics_sink.config)
        topic_extractor = None
        if settings.topic_extractor.name == "llm":
            from altk.pre_llm.routing.retrieval_augmented_thinking.topic_extractor.llm import (
                LLMTopicExtractor,
            )

            topic_extractor = LLMTopicExtractor.from_settings(
                settings.topic_extractor.config, settings
            )
        elif settings.topic_extractor.name == "bertopic":
            from altk.pre_llm.routing.retrieval_augmented_thinking.topic_extractor.bertopic import (
                BERTopicTopicExtractor,
            )

            topic_extractor = BERTopicTopicExtractor.from_settings(
                settings.topic_extractor.config
            )
        elif settings.topic_extractor.name == "tfidf_words":
            from altk.pre_llm.routing.retrieval_augmented_thinking.topic_extractor.tfidf_words import (
                TFIDFWordsTopicExtractor,
            )

            topic_extractor = TFIDFWordsTopicExtractor.from_settings(
                settings.topic_extractor.config
            )

        if not topic_extractor:
            raise ValueError("No topic extractor implementation provided in settings")
        return cls(
            config=settings,
            subject=settings.subject,
            topics_sink=topics_sink,
            topic_extractor=topic_extractor,
        )

    @classmethod
    def register_content_provider(cls):
        def _register(cls):
            impl_name = (
                f"{cls.__module__}.{cls.__qualname__}"
                if cls.__module__
                else cls.__qualname__
            )
            if impl_name in CONTENT_PROVIDERS:
                logger.warning(
                    f"Overriding registered ContentProvider {impl_name} with class {CONTENT_PROVIDERS[impl_name]} with new class {cls}"
                )
            else:
                logger.info(
                    f"Registering class {cls} as a ContentProvider implementation {impl_name}"
                )
            CONTENT_PROVIDERS[impl_name] = cls
            return cls

        return _register

    @classmethod
    def register_topics_sink(cls):
        def _register(cls):
            impl_name = (
                f"{cls.__module__}.{cls.__qualname__}"
                if cls.__module__
                else cls.__qualname__
            )
            if impl_name in TOPICS_SINKS:
                logger.warning(
                    f"Overriding registered TopicsSink {impl_name} with class {TOPICS_SINKS[impl_name]} with new class {cls}"
                )
            else:
                logger.info(
                    f"Registering class {cls} as a TopicsSink implementation {impl_name}"
                )
            TOPICS_SINKS[impl_name] = cls
            return cls

        return _register

    @classmethod
    def supported_phases(cls) -> Set[AgentPhase]:
        return {AgentPhase.BUILDTIME}

    def _build(self, data: InputType) -> TopicExtractionBuildOutput[OutputType]:
        """
        Does the topic extraction.

        Args:
            data: not used, must be passed as None when invoking this method

        Returns:
            A `TopicExtractionOutput` containing the topics of expertise as a list of `TopicInfo`
        """
        topic_extraction_output = self.topic_extractor.extract_topics(
            self.subject, data
        )
        if self.topics_sink and topic_extraction_output.topics:
            deduped_topics = remove_dup_topics(topic_extraction_output.topics)
            self.topics_sink.add_topics(deduped_topics)
        elif not topic_extraction_output.topics:
            logger.warning("No topics were extracted")
        return topic_extraction_output


def remove_dup_topics(topics: List[TopicInfo]) -> List[TopicInfo]:
    unique_topics = []
    for topic in topics:
        if topic not in unique_topics and not any(
            [topic < _topic for _topic in topics]
        ):
            unique_topics.append(topic)
    return unique_topics
