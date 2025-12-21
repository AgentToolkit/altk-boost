import logging
from typing import List

import pytest

from altk.pre_llm.core.types import (
    EmbeddedTopic,
    RetrievedTopic,
    TopicInfo,
    TopicLoadingInput,
    TopicRetrievalRunInput,
)
from altk.pre_llm.core.types import (
    TopicRetrievalRunOutput,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.milvus.topic_retriever import (
    MilvusTopicRetriever,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.milvus.topic_sink import (
    MilvusProvider,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.topic_loading.topic_loading import (
    TopicLoadingMiddleware,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.topic_retriever.topic_retriever import (
    TopicRetrievalMiddleware,
)
from altk.core.toolkit import AgentPhase


def test_preembedded_topic_loading(tmp_path, caplog):
    caplog.set_level(logging.DEBUG, MilvusProvider.__module__)
    tmp_path.mkdir(exist_ok=True)
    db_path = tmp_path / "milvus.db"

    topics = [
        EmbeddedTopic(
            topic=TopicInfo(
                topic="Job tasks",
                subject="job_offering",
                metadata={"env_1": "live", "env_2": "dark_lunch"},
            ),
            embeddings=[1, 2],
        ),
        EmbeddedTopic(
            topic=TopicInfo(
                topic="Job responsibilities",
                subject="job_offering",
                metadata={"env_1": "staging", "env_2": "testing"},
            ),
            embeddings=[3, 2],
        ),
    ]
    topic_loading = TopicLoadingMiddleware(topics_sink=MilvusProvider(str(db_path)))
    with pytest.raises(TypeError) as exc_info:
        topic_loading.process(
            data=TopicLoadingInput(topics=topics), phase=AgentPhase.BUILDTIME
        )
    assert (
        str(exc_info.value)
        == "Inserting preembedded topics when using Milvus Full Text Search (https://milvus.io/docs/full-text-search.md) is not supported."
    )


def test_topic_loading(tmp_path, caplog):
    caplog.set_level(logging.DEBUG, MilvusProvider.__module__)
    tmp_path.mkdir(exist_ok=True)
    db_path = tmp_path / "milvus.db"

    topics = [
        TopicInfo(
            topic="Job tasks",
            subject="job_offering",
            metadata={"env_1": "live", "env_2": "dark_lunch"},
        ),
        TopicInfo(
            topic="Job responsibilities",
            subject="job_offering",
            metadata={"env_1": "staging", "env_2": "testing"},
        ),
    ]
    topic_loading = TopicLoadingMiddleware(topics_sink=MilvusProvider(str(db_path)))
    topic_loading.process(
        data=TopicLoadingInput(topics=topics), phase=AgentPhase.BUILDTIME
    )

    topic_retrieval = TopicRetrievalMiddleware(
        topic_retriever=MilvusTopicRetriever(
            str(db_path), metadata_fields=["env_1", "env_2"]
        )
    )
    topic_retriever_ouput: TopicRetrievalRunOutput = topic_retrieval.process(
        data=TopicRetrievalRunInput(
            messages=[{"role": "user", "content": "What are my job responsibilities?"}]
        ),
        phase=AgentPhase.RUNTIME,
    )
    retrieved_topics: List[RetrievedTopic] = sorted(
        topic_retriever_ouput.topics, key=lambda t: t.topic
    )
    assert len(retrieved_topics) == 1
    assert retrieved_topics[0].topic.topic == "Job responsibilities"
    assert retrieved_topics[0].topic.subject == "job_offering"
    assert retrieved_topics[0].topic.metadata == {
        "env_1": "staging",
        "env_2": "testing",
    }
    assert retrieved_topics[0].distance is not None
