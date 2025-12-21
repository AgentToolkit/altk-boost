import logging
from pathlib import Path
from pymilvus import MilvusClient, model
import pytest

from altk.pre_llm.core.types import TopicInfo
from altk.pre_llm.core.types import (
    EmbeddedTopic,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.milvus.common import (
    AnnSearchConfig,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.milvus.topic_sink import (
    MilvusProvider,
)


def test_topic_sink_full_text_search(tmp_path: Path, caplog):
    caplog.set_level(logging.DEBUG, MilvusProvider.__module__)
    tmp_path.mkdir(exist_ok=True)
    db_path = tmp_path / "milvus.db"
    topic_sink = MilvusProvider(str(db_path))
    topic_sink.add_topics(
        [
            TopicInfo(
                topic="t1", subject="s1", metadata={"env": "testing", "prop_1": 1}
            ),
            TopicInfo(
                topic="t2", subject="s1", metadata={"env": "testing", "prop_1": 2}
            ),
        ],
    )

    # verify that the documents were inserted into the DB
    client = MilvusClient(str(db_path))
    docs = client.query(
        collection_name="topics",
        output_fields=[
            "text",
            "subject",
            "env",
        ],
        limit=10,
    )
    print(docs)
    assert len(docs) == 2
    assert (
        "prop_1" not in docs[0]
    )  # since prop_1 was not requested to be returned in the output_fields parameter it's not returned
    assert docs[0]["text"] == "t1"
    assert docs[0]["subject"] == "s1"
    assert (
        docs[0]["env"] == "testing"
    )  # env metadata field is returned along the other fields
    assert "prop_1" not in docs[1]  # idem as abobe
    assert docs[1]["text"] == "t2"
    assert docs[1]["subject"] == "s1"
    assert docs[1]["env"] == "testing"  # idem as above


def test_topic_sink_semantic_search(tmp_path: Path, caplog):
    caplog.set_level(logging.DEBUG, MilvusProvider.__module__)
    tmp_path.mkdir(exist_ok=True)
    db_path = tmp_path / "milvus.db"
    topic_sink = MilvusProvider(str(db_path), ann_search_config=AnnSearchConfig())
    topic_sink.add_topics(
        [
            TopicInfo(
                topic="Sound perception",
                subject="s1",
                metadata={"env": "testing", "prop_1": 1},
            ),
            TopicInfo(
                topic="Economic policy",
                subject="s1",
                metadata={"env": "testing", "prop_1": 2},
            ),
        ],
    )

    # verify that the documents were inserted into the DB
    client = MilvusClient(str(db_path))
    docs = client.query(
        collection_name="topics",
        output_fields=[
            "text",
            "subject",
            "env",
        ],
        limit=10,
    )
    print(docs)
    assert len(docs) == 2
    assert (
        "prop_1" not in docs[0]
    )  # since prop_1 was not requested to be returned in the output_fields parameter it's not returned
    assert docs[0]["text"] == "Sound perception"
    assert docs[0]["subject"] == "s1"
    assert (
        docs[0]["env"] == "testing"
    )  # env metadata field is returned along the other fields
    assert "prop_1" not in docs[1]  # idem as abobe
    assert docs[1]["text"] == "Economic policy"
    assert docs[1]["subject"] == "s1"
    assert docs[1]["env"] == "testing"  # idem as above

    emb_fn = model.DefaultEmbeddingFunction()
    query_vectors = emb_fn.encode_queries(["Economies from developing countries"])
    results = client.search(
        data=query_vectors,
        collection_name="topics",
        output_fields=[
            "text",
            "subject",
            "env",
        ],
    )
    # all docs are returned
    assert len(results[0]) == 2
    # first doc is the most similar
    assert results[0][0]["text"] == "Economic policy"
    assert results[0][1]["text"] == "Sound perception"


def test_add_embedded_topics_fails_with_full_text_search(tmp_path: Path, caplog):
    caplog.set_level(logging.DEBUG, MilvusProvider.__module__)
    tmp_path.mkdir(exist_ok=True)
    db_path = tmp_path / "milvus.db"
    topic_sink = MilvusProvider(str(db_path))
    with pytest.raises(
        TypeError,
        match="Inserting preembedded topics when using Milvus Full Text Search",
    ):
        topic_sink.add_embedded_topics(
            [
                EmbeddedTopic(
                    topic=TopicInfo(
                        topic="t1",
                        subject="s1",
                        metadata={"env": "testing", "prop_1": 1},
                    ),
                    embeddings=[0.1, 0.2, 0.3],
                ),
            ],
        )


def test_add_embedded_topics(tmp_path: Path, caplog):
    caplog.set_level(logging.DEBUG, MilvusProvider.__module__)
    tmp_path.mkdir(exist_ok=True)
    db_path = tmp_path / "milvus.db"
    topic_sink = MilvusProvider(
        str(db_path), ann_search_config=AnnSearchConfig(vector_dimensions=3)
    )
    topic_sink.add_embedded_topics(
        [
            EmbeddedTopic(
                topic=TopicInfo(
                    topic="Sound perception",
                    subject="s1",
                    metadata={"env": "testing", "prop_1": 1},
                ),
                embeddings=[0.1, 0.2, 0.3],
            ),
            EmbeddedTopic(
                topic=TopicInfo(
                    topic="Economic policy",
                    subject="s1",
                    metadata={"env": "testing", "prop_1": 2},
                ),
                embeddings=[0.4, 0.5, 0.6],
            ),
        ],
    )
    client = MilvusClient(str(db_path))
    results = client.query(
        collection_name="topics",
        output_fields=[
            "text",
            "subject",
            "env",
            "vector",
        ],
        limit=10,
    )
    assert len(results) == 2
    assert results[0]["text"] == "Sound perception"
    assert results[0]["vector"] == pytest.approx([0.1, 0.2, 0.3], rel=1e-6, abs=1e-8)
    assert results[1]["text"] == "Economic policy"
    assert results[1]["vector"] == pytest.approx([0.4, 0.5, 0.6], rel=1e-6, abs=1e-8)


def test_add_embedded_topics_using_embedding_function(tmp_path: Path, caplog):
    caplog.set_level(logging.DEBUG, MilvusProvider.__module__)
    tmp_path.mkdir(exist_ok=True)
    db_path = tmp_path / "milvus.db"
    topic_sink = MilvusProvider(str(db_path), ann_search_config=AnnSearchConfig())
    topic_sink.add_embedded_topics(
        [
            EmbeddedTopic(
                topic=TopicInfo(
                    topic="Sound perception",
                    subject="s1",
                    metadata={"env": "testing", "prop_1": 1},
                ),
                embeddings=[
                    0.1,
                    0.2,
                    0.3,
                ],  # Although embeddings are provided, they will be ignored since an emb_fn is provided
            ),
            EmbeddedTopic(
                topic=TopicInfo(
                    topic="Economic policy",
                    subject="s1",
                    metadata={"env": "testing", "prop_1": 2},
                ),
                embeddings=[0.4, 0.5, 0.6],
            ),
        ],
        emb_fn=model.DefaultEmbeddingFunction(),
    )
    client = MilvusClient(str(db_path))
    results = client.query(
        collection_name="topics",
        output_fields=[
            "text",
            "subject",
            "env",
            "vector",
        ],
        limit=10,
    )
    assert len(results) == 2
    assert results[0]["text"] == "Sound perception"
    assert results[1]["text"] == "Economic policy"
