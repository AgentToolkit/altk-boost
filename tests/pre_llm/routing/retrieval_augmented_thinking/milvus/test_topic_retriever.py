import logging
from pathlib import Path

import pytest
from pymilvus import model

from altk.pre_llm.core.types import (
    TopicInfo,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.milvus.common import (
    AnnSearchConfig,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.milvus.error import (
    SearchTypeMismatchError,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.milvus.topic_retriever import (
    MilvusTopicRetriever,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.milvus.topic_sink import (
    MilvusProvider,
)


def test_topic_retriever_full_text_search(tmp_path: Path, caplog):
    caplog.set_level(logging.DEBUG, MilvusTopicRetriever.__module__)
    caplog.set_level(logging.DEBUG, MilvusProvider.__module__)
    tmp_path.mkdir(exist_ok=True)
    db_path = tmp_path / "milvus.db"
    topic_sink = MilvusProvider(str(db_path))
    topics = [
        TopicInfo(
            topic="Job 1",
            subject="HR Job Area",
            metadata={"env": "testing", "prop_1": 1},
        ),
        TopicInfo(
            topic="Job 2",
            subject="HR Job Area",
            metadata={"env": "prod", "prop_1": 2},
        ),
    ]

    topic_sink.add_topics(topics)
    topic_retriever = MilvusTopicRetriever(
        str(db_path), metadata_fields=["env", "prop_1"]
    )
    retrieved_topics = topic_retriever.get_topics("Get job positions")
    assert len(retrieved_topics) == 2
    assert topics == sorted(
        [retrieved_topic.topic for retrieved_topic in retrieved_topics],
        key=lambda t: t.topic,
    )


def test_topic_retriever_full_text_search_with_filtering(tmp_path: Path, caplog):
    caplog.set_level(logging.DEBUG, MilvusTopicRetriever.__module__)
    caplog.set_level(logging.DEBUG, MilvusProvider.__module__)
    tmp_path.mkdir(exist_ok=True)
    db_path = tmp_path / "milvus.db"
    topic_sink = MilvusProvider(str(db_path))
    topics = [
        TopicInfo(
            topic="Job 1",
            subject="HR Job Area",
            metadata={"env": "testing", "prop_1": 1},
        ),
        TopicInfo(
            topic="Job 2",
            subject="HR Job Area",
            metadata={"env": "prod", "prop_1": 2},
        ),
    ]

    topic_sink.add_topics(topics)
    topic_retriever = MilvusTopicRetriever(
        str(db_path), metadata_fields=["env", "prop_1"]
    )
    retrieved_topics = topic_retriever.get_topics(
        "Get job positions", query_kwargs={"filter": 'env == "prod"'}
    )
    assert len(retrieved_topics) == 1
    assert topics[1] == retrieved_topics[0].topic

    retrieved_topics = topic_retriever.get_topics(
        "Get job positions", query_kwargs={"filter": "prop_1 > 0"}
    )
    assert len(retrieved_topics) == 2
    assert topics == sorted(
        [retrieved_topic.topic for retrieved_topic in retrieved_topics],
        key=lambda t: t.topic,
    )


def test_topic_retriever_semantic_text_search(tmp_path: Path, caplog):
    caplog.set_level(logging.DEBUG, MilvusTopicRetriever.__module__)
    caplog.set_level(logging.DEBUG, MilvusProvider.__module__)
    tmp_path.mkdir(exist_ok=True)
    db_path = tmp_path / "milvus.db"
    topic_sink = MilvusProvider(str(db_path), ann_search_config=AnnSearchConfig())
    topics = [
        TopicInfo(
            topic="Software Engineer",
            subject="HR Job Area",
            metadata={"env": "testing", "prop_1": 1},
        ),
        TopicInfo(
            topic="Product Manager",
            subject="HR Job Area",
            metadata={"env": "prod", "prop_1": 2},
        ),
    ]

    topic_sink.add_topics(topics)
    topic_retriever = MilvusTopicRetriever(
        str(db_path),
        metadata_fields=["env", "prop_1"],
        ann_search_config=AnnSearchConfig(),
    )
    retrieved_topics = topic_retriever.get_topics(
        "Get engineer positions", distance_threshold=0.5
    )
    assert len(retrieved_topics) == 1
    assert topics[0] == retrieved_topics[0].topic


def test_topic_retriever_semantic_text_search_sentence_transformer_embedding(
    tmp_path: Path, caplog
):
    caplog.set_level(logging.DEBUG, MilvusTopicRetriever.__module__)
    caplog.set_level(logging.DEBUG, MilvusProvider.__module__)
    tmp_path.mkdir(exist_ok=True)
    db_path = tmp_path / "milvus.db"
    ann_search_config = AnnSearchConfig(
        embedding_function=model.dense.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2", device="cpu"
        ),
    )

    topic_sink = MilvusProvider(
        str(db_path),
        ann_search_config=ann_search_config,
    )
    topics = [
        TopicInfo(
            topic="Software Engineer",
            subject="HR Job Area",
            metadata={"env": "testing", "prop_1": 1},
        ),
        TopicInfo(
            topic="Product Manager",
            subject="HR Job Area",
            metadata={"env": "prod", "prop_1": 2},
        ),
    ]

    topic_sink.add_topics(topics)
    topic_retriever = MilvusTopicRetriever(
        str(db_path),
        metadata_fields=["env", "prop_1"],
        ann_search_config=ann_search_config,
    )
    retrieved_topics = topic_retriever.get_topics(
        "Get engineer positions", distance_threshold=0.5
    )
    assert len(retrieved_topics) == 1
    assert topics[0] == retrieved_topics[0].topic


def test_topic_retriever_fails_if_search_type_mismatch(tmp_path: Path, caplog):
    caplog.set_level(logging.DEBUG, MilvusTopicRetriever.__module__)
    caplog.set_level(logging.DEBUG, MilvusProvider.__module__)
    tmp_path.mkdir(exist_ok=True)
    db_path = tmp_path / "milvus.db"
    # By default the MilvusProvider loads the topics with full text search
    topic_sink = MilvusProvider(str(db_path), collection_name="topics_full_text_search")
    topics = [
        TopicInfo(
            topic="Software Engineer",
            subject="HR Job Area",
            metadata={"env": "testing", "prop_1": 1},
        ),
        TopicInfo(
            topic="Product Manager",
            subject="HR Job Area",
            metadata={"env": "prod", "prop_1": 2},
        ),
    ]

    topic_sink.add_topics(topics)

    # If the Topic Retriever is configured with semantic search it will fail with SearchTypeMismatchError
    with pytest.raises(
        SearchTypeMismatchError,
        match="The collection 'topics_full_text_search' was not setup to do semantic search",
    ):
        _ = MilvusTopicRetriever(
            str(db_path),
            collection_name="topics_full_text_search",
            metadata_fields=["env", "prop_1"],
            ann_search_config=AnnSearchConfig(),
        )

    # Create a MilvusProvider to load topics so they can be queried using semantic search
    topic_sink = MilvusProvider(
        str(db_path),
        collection_name="topics_semantic_search",
        ann_search_config=AnnSearchConfig(),
    )
    topics = [
        TopicInfo(
            topic="Software Engineer",
            subject="HR Job Area",
            metadata={"env": "testing", "prop_1": 1},
        ),
        TopicInfo(
            topic="Product Manager",
            subject="HR Job Area",
            metadata={"env": "prod", "prop_1": 2},
        ),
    ]

    topic_sink.add_topics(topics)

    # By default the Topic Retriever is configured to use full text search and it will fail since the collection was setup with semantic search
    with pytest.raises(
        SearchTypeMismatchError,
        match="The collection 'topics_semantic_search' was not setup to do full text search",
    ):
        _ = MilvusTopicRetriever(
            str(db_path),
            collection_name="topics_semantic_search",
            metadata_fields=["env", "prop_1"],
        )
