import logging
from altk.core.toolkit import AgentPhase
from altk.pre_llm.core.types import (
    TopicExtractionBuildOutput,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.topic_extractor.settings import (
    MultipleTopicExtractionSettings,
)
from typing import List
from altk.pre_llm.routing.retrieval_augmented_thinking.topic_extractor.topic_extractor import (
    TopicExtractionMiddleware,
)

logger = logging.getLogger(__name__)


def create_topic_extractions(settings: MultipleTopicExtractionSettings):
    topic_extractions: List[TopicExtractionMiddleware] = []
    for topic_extractor_setting in settings.topic_extractors:
        if not topic_extractor_setting.topics_sink:
            topic_extractor_setting.topics_sink = settings.topics_sink
        topic_extractions.append(
            TopicExtractionMiddleware.from_settings(topic_extractor_setting)
        )

    return topic_extractions


def run_topic_extractions(
    topic_extractions: List[TopicExtractionMiddleware],
    settings: MultipleTopicExtractionSettings,
):
    for topic_extraction, topic_extraction_settings in zip(
        topic_extractions, settings.topic_extractors
    ):
        result: TopicExtractionBuildOutput = topic_extraction.process(
            data=None, phase=AgentPhase.BUILDTIME
        )
        logger.info(f"Topic extraction from: {topic_extraction_settings.subject}")
        logger.info(
            f"Chunks processed: {result.topic_extractor_output.chunks_processed}"
        )
        logger.info(f"Error: {result.error}")
        logger.info(f"Number of extracted topics: {len(result.topics)}")
        if result.topic_extractor_output.chunks_processed > 0:
            extraction_times = [
                chunk.extraction_time
                for chunk in result.topic_extractor_output.chunk_stats.values()
                if not chunk.error
            ]
            logger.info(
                f"Average chunk topic extraction time: {sum(extraction_times) / len(extraction_times)}"
            )
