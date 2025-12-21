import logging

from chromadb.api import ClientAPI
from chromadb.api.types import GetResult

from altk.pre_llm.core.types import TopicExtractionBuildOutput
from altk.pre_llm.routing.retrieval_augmented_thinking.chroma.topic_sink_content_provider import (
    ChromaDBProvider,
    TopicExtractionMiddleware,
)
from altk.pre_llm.core.types import (
    TopicExtractionInput,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.topic_extractor.settings import (
    TopicExtractionSettings,
)
from altk.core.toolkit import AgentPhase


def test_bertopic_extractor_default_params(caplog, chunks, chroma: ClientAPI):
    caplog.set_level(logging.DEBUG, logger=ChromaDBProvider.__module__)
    caplog.set_level(logging.DEBUG, logger=TopicExtractionMiddleware.__module__)

    topic_extractor_settings = {
        "subject": "sound",
        "topic_extractor": {"name": "bertopic", "config": {"nr_topics": 1000}},
        "topics_sink": {
            "name": "altk.pre_llm.routing.retrieval_augmented_thinking.chroma.topic_sink_content_provider.ChromaDBProvider",
            "config": {
                "collection": "sound.topics",
                "instance": {"client": chroma},
            },
        },
    }

    topic_extractor = TopicExtractionMiddleware.from_settings(
        TopicExtractionSettings(**topic_extractor_settings)
    )

    topic_extraction_output: TopicExtractionBuildOutput = topic_extractor.process(
        data=TopicExtractionInput(documents=chunks[:10]), phase=AgentPhase.BUILDTIME
    )
    assert topic_extraction_output.error is None

    # list the extracted topics returned in the output
    for topic in topic_extraction_output.topics:
        print(topic)

    # list the extracted topics stored in the target collection
    assert "sound.topics" in [col.name for col in chroma.list_collections()]
    topics: GetResult = chroma.get_collection("sound.topics").get()
    print()
    print("Extracted topics:")
    for doc, metadata in [
        (doc, metadata)
        for doc, metadata in zip(topics["documents"], topics["metadatas"])
    ]:
        print()
        print(f"Topic: {doc}")
        print(f"Metadata: {metadata}")


def test_bertopic_extractor_custom_params(caplog, chunks, chroma: ClientAPI):
    caplog.set_level(logging.DEBUG, logger=ChromaDBProvider.__module__)
    caplog.set_level(logging.DEBUG, logger=TopicExtractionMiddleware.__module__)

    topic_extractor_settings = {
        "subject": "sound",
        "topic_extractor": {
            "name": "bertopic",
        },
        "topics_sink": {
            "name": "altk.pre_llm.routing.retrieval_augmented_thinking.chroma.topic_sink_content_provider.ChromaDBProvider",
            "config": {
                "collection": "sound.topics",
                "instance": {"client": chroma},
            },
        },
    }

    topic_extractor = TopicExtractionMiddleware.from_settings(
        TopicExtractionSettings(**topic_extractor_settings)
    )

    topic_extraction_output: TopicExtractionBuildOutput = topic_extractor.process(
        data=TopicExtractionInput(documents=chunks[:10]), phase=AgentPhase.BUILDTIME
    )
    assert topic_extraction_output.error is None

    # list the extracted topics returned in the output
    for topic in topic_extraction_output.topics:
        print(topic)

    # list the extracted topics stored in the target collection
    assert "sound.topics" in [col.name for col in chroma.list_collections()]
    topics: GetResult = chroma.get_collection("sound.topics").get()
    print()
    print("Extracted topics:")
    for doc, metadata in [
        (doc, metadata)
        for doc, metadata in zip(topics["documents"], topics["metadatas"])
    ]:
        print()
        print(f"Topic: {doc}")
        print(f"Metadata: {metadata}")
