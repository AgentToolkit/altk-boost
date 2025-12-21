import logging
from typing import Set

from pydantic import ConfigDict

from altk.pre_llm.core.types import EmbeddedTopic, TopicInfo, TopicLoadingInput
from altk.pre_llm.core.types import (
    TopicsSink,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.topic_extractor.topic_extractor import (
    TOPICS_SINKS,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.topic_loading.settings import (
    TopicLoadingSettings,
)
from altk.core.toolkit import AgentPhase, ComponentBase

logger = logging.getLogger(__name__)


class TopicLoadingMiddleware(ComponentBase):
    """
    Loads topics provided as `TopicInfo`'s into the `TopicsSink` specified in the TopicLoadingSettings. If the topics already have the embedding calculated the `EmbeddedTopic` class is used instead.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)
    topics_sink: TopicsSink

    @classmethod
    def from_settings(cls, settings: TopicLoadingSettings) -> "TopicLoadingMiddleware":
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

        return cls(
            topics_sink=topics_sink,
        )

    @classmethod
    def supported_phases(cls) -> Set[AgentPhase]:
        return {AgentPhase.BUILDTIME}

    def _build(self, data: TopicLoadingInput):
        """
        Loads the already embedded topics into the `TopicSink`
        """
        if data.topics and isinstance(data.topics[0], EmbeddedTopic):
            self.topics_sink.add_embedded_topics(data.topics, data.embedding_function)
        elif data.topics and isinstance(data.topics[0], TopicInfo):
            self.topics_sink.add_topics(data.topics)
        else:
            logger.warning("There are no topics to load")
