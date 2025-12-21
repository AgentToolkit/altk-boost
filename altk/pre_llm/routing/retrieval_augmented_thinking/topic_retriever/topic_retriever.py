import logging
from typing import Dict, Set, Type

from pydantic import ConfigDict

from altk.pre_llm.core.types import TopicRetrievalRunInput, TopicRetrievalRunOutput
from altk.pre_llm.core.types import (
    TopicRetriever,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.topic_retriever.settings import (
    Settings,
)
from altk.core.toolkit import AgentPhase, ComponentBase

logger = logging.getLogger(__name__)

TOPIC_RETRIEVERS: Dict[str, Type[TopicRetriever]] = {}


def register(impl_name: str):
    def _register(cls):
        if impl_name in TOPIC_RETRIEVERS:
            logger.warning(
                f"Overriding registered TopicRetriever {impl_name} with class {TOPIC_RETRIEVERS[impl_name]} with new factory method {cls}"
            )
        else:
            logger.info(
                f"Registering class {cls} as a TopicRetriever implementation {impl_name}"
            )
        TOPIC_RETRIEVERS[impl_name] = cls
        return cls

    return _register


class TopicRetrievalMiddleware(ComponentBase):
    """
    Retrieves topics of expertise using a `TopicRetriever` specified in the provided `Settings`.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)
    topic_retriever: TopicRetriever

    @classmethod
    def from_settings(cls, settings: Settings) -> "TopicRetrievalMiddleware":
        if settings.name not in TOPIC_RETRIEVERS:
            raise ValueError(f"Unkonwn TopicRetriever implementation: {settings.name}")
        factory_method = getattr(TOPIC_RETRIEVERS[settings.name], "from_settings", None)
        if not factory_method:
            raise ValueError(
                f"TopicRetriever implementation {TOPIC_RETRIEVERS[settings.name]} is missing the class method from_settings"
            )
        topic_retriever: TopicRetriever = factory_method(settings.config)
        return cls(topic_retriever=topic_retriever)

    @classmethod
    def supported_phases(cls) -> Set[AgentPhase]:
        return {AgentPhase.RUNTIME}

    def _run(self, data: TopicRetrievalRunInput) -> TopicRetrievalRunOutput:
        """
        Retrieves topics of expertise that are most related to the user query

        Args:
            data: a `TopicRetrievalRunInput` with the user query, the number of topics to return from the topic retriever and an optional value to filter the Topics 'flags' field

        Returns:
            A `TopicRetrievalRunOutput` containing the topics of expertise as a list of `TopicInfo`
        """
        if not data.messages:
            raise ValueError(
                "A conversation context with at least one message must be provided"
            )
        return TopicRetrievalRunOutput(
            topics=self.topic_retriever.get_topics(
                query=data.messages[-1].get("content"),
                n_results=data.n_results,
                query_kwargs=data.query_kwargs,
                distance_threshold=data.distance_threshold,
            )
        )
