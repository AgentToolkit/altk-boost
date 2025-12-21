import json
import logging
from pathlib import Path

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
from altk.pre_llm.routing.retrieval_augmented_thinking.topic_extractor.tfidf_words import (
    TFIDFWordsTopicExtractor,
)
from altk.core.toolkit import AgentPhase


def test_tfidf_words_extractor_default_params(caplog, chunks, chroma: ClientAPI):
    caplog.set_level(logging.DEBUG, logger=ChromaDBProvider.__module__)
    caplog.set_level(logging.DEBUG, logger=TopicExtractionMiddleware.__module__)

    topic_extractor_settings = {
        "subject": "sound",
        "topic_extractor": {
            "name": "tfidf_words",
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


def test_tfidf_words_extractor_settings(chroma: ClientAPI):
    topic_extraction_settings = {
        "subject": "sound",
        "topic_extractor": {
            "name": "tfidf_words",
            "config": {"top_words": 40, "top_words_picked": 10},
        },
        "topics_sink": {
            "name": "altk.pre_llm.routing.retrieval_augmented_thinking.chroma.topic_sink_content_provider.ChromaDBProvider",
            "config": {
                "collection": "sound.topics",
                "instance": {"client": chroma},
            },
        },
    }

    topic_extraction = TopicExtractionMiddleware.from_settings(
        TopicExtractionSettings(**topic_extraction_settings)
    )

    assert isinstance(topic_extraction.topic_extractor, TFIDFWordsTopicExtractor)
    assert topic_extraction.topic_extractor.settings.top_words == 40
    assert topic_extraction.topic_extractor.settings.top_words_picked == 10

    topic_extractor_settings_wo_topic_extractor = dict(topic_extraction_settings)
    topic_extractor_settings_wo_topic_extractor["topic_extractor"].pop("config")
    topic_extraction = TopicExtractionMiddleware.from_settings(
        TopicExtractionSettings(**topic_extractor_settings_wo_topic_extractor)
    )

    assert isinstance(topic_extraction.topic_extractor, TFIDFWordsTopicExtractor)
    assert topic_extraction.topic_extractor.settings.top_words == 30
    assert topic_extraction.topic_extractor.settings.top_words_picked == 20
    DEFAULT_COUNT_VECTORIZER_ARGS = {
        "max_df": 0.95,  # Ignore terms that appear in more than 85% of documents (too common)
        "min_df": 1,  # Include terms that appear in at least 1 document
        "max_features": 5000,  # Limit to top 1000 features ordered by term frequency across corpus
        "stop_words": "english",  # Remove English stop words
        "token_pattern": r"(?u)\b\w[\w-]*\b",
        "ngram_range": (3, 3),  # Include unigrams and N-grams
    }
    DEFAULT_TFIDF_VECTORIZER_ARGS = {
        "norm": "l2",  # Normalize the TF-IDF vectors (Euclidean norm)
        "use_idf": True,  # Enable inverse document frequency reweighting
        "smooth_idf": True,  # Smooth IDF weights by adding 1 to document frequencies to prevent zero division
        "sublinear_tf": True,  # Apply sublinear tf scaling: tf = 1 + log(tf)
    }
    assert (
        topic_extraction.topic_extractor.settings.count_vectorizer_settings.model_dump()
        == DEFAULT_COUNT_VECTORIZER_ARGS
    )
    assert (
        topic_extraction.topic_extractor.settings.tfidf_vectorizer_settings.model_dump()
        == dict(DEFAULT_COUNT_VECTORIZER_ARGS) | DEFAULT_TFIDF_VECTORIZER_ARGS
    )


def test_tfidf_words_extractor_settings_from_file(chroma: ClientAPI):
    topic_extraction_settings = json.loads(
        (Path(__file__).parent / "data/topic_extraction_tfidf_words.json").read_text()
    )
    topic_extraction_settings["topics_sink"]["config"]["instance"]["client"] = chroma
    topic_extraction = TopicExtractionMiddleware.from_settings(
        TopicExtractionSettings(**topic_extraction_settings)
    )
    assert isinstance(topic_extraction.topic_extractor, TFIDFWordsTopicExtractor)
    assert topic_extraction.topic_extractor.settings.top_words == 40
    assert topic_extraction.topic_extractor.settings.top_words_picked == 10


def test_tfidf_words_extractor_custom_params(caplog, chunks, chroma: ClientAPI):
    caplog.set_level(logging.DEBUG, logger=ChromaDBProvider.__module__)
    caplog.set_level(logging.DEBUG, logger=TopicExtractionMiddleware.__module__)

    topic_extractor_settings = {
        "subject": "sound",
        "topic_extractor": {
            "name": "tfidf_words",
            "config": {"top_words": 10, "top_words_picked": 2},
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
