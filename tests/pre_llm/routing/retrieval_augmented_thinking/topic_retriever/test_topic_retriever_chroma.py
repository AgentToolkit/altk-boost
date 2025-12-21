import logging
from typing import Callable, List

from chromadb.api import ClientAPI
from altk.core.toolkit import AgentPhase
from altk.pre_llm.core.types import RetrievedTopic, TopicInfo, TopicRetrievalRunOutput
from altk.pre_llm.core.types import (
    TopicRetrievalRunInput,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.chroma.topic_retriever import (
    ChromaDBTopicRetriever,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.topic_retriever.settings import (
    Settings,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.topic_retriever.topic_retriever import (
    TopicRetrievalMiddleware,
)


def test_topic_retriever(caplog, create_chroma: Callable[..., ClientAPI]):
    caplog.set_level(logging.INFO, TopicRetrievalMiddleware.__module__)
    caplog.set_level(logging.INFO, ChromaDBTopicRetriever.__module__)
    col_name = "test.collection"
    topics: List[TopicInfo] = [
        TopicInfo(topic="Job 1", expertise="expert", subject="s_1"),
        TopicInfo(topic="Job 2", expertise="knowledge", subject="s_1"),
        TopicInfo(topic="Job 3", expertise="mentions", subject="s_1"),
        TopicInfo(topic="Job 4", expertise="mentions", subject="s_2"),
        TopicInfo(topic="Job 5", expertise="knowledge", subject="s_2"),
    ]
    client = create_chroma(
        col_name,
        [topic.topic for topic in topics],
        [{"subject": topic.subject, "expertise": topic.expertise} for topic in topics],
    )
    topic_retriever = TopicRetrievalMiddleware(
        topic_retriever=ChromaDBTopicRetriever(collection=col_name, client=client)
    )
    topic_retriever_ouput: TopicRetrievalRunOutput = topic_retriever.process(
        data=TopicRetrievalRunInput(
            messages=[{"role": "user", "content": "What are my job responsibilities?"}]
        ),
        phase=AgentPhase.RUNTIME,
    )
    retrieved_topics: List[RetrievedTopic] = sorted(
        topic_retriever_ouput.topics, key=lambda t: t.topic.topic
    )
    assert len(retrieved_topics) == len(topics)
    for retrieved_topic, topic in zip(retrieved_topics, topics):
        assert retrieved_topic.topic.topic == topic.topic
        assert retrieved_topic.topic.subject == topic.subject
        assert retrieved_topic.topic.expertise == topic.expertise
        assert retrieved_topic.topic.metadata == {}
        assert retrieved_topic.distance is not None
    for topic in retrieved_topics:
        print(topic)


def test_topic_retriever_using_dict_settings(
    caplog, create_chroma: Callable[..., ClientAPI]
):
    caplog.set_level(logging.INFO, TopicRetrievalMiddleware.__module__)
    caplog.set_level(logging.INFO, ChromaDBTopicRetriever.__module__)
    col_name = "test.collection"
    topics: List[TopicInfo] = [
        TopicInfo(topic="Job 1", expertise="expert", subject="s_1"),
        TopicInfo(topic="Job 2", expertise="knowledge", subject="s_1"),
        TopicInfo(topic="Job 3", expertise="mentions", subject="s_1"),
        TopicInfo(topic="Job 4", expertise="mentions", subject="s_2"),
        TopicInfo(topic="Job 5", expertise="knowledge", subject="s_2"),
    ]
    client = create_chroma(
        col_name,
        [topic.topic for topic in topics],
        [{"subject": topic.subject, "expertise": topic.expertise} for topic in topics],
    )
    topic_retriever_settings = {
        "name": "chromadb",
        "config": {"collection": col_name, "instance": {"client": client}},
    }
    topic_retriever = TopicRetrievalMiddleware.from_settings(
        Settings(**topic_retriever_settings)
    )
    topic_retriever_ouput: TopicRetrievalRunOutput = topic_retriever.process(
        data=TopicRetrievalRunInput(
            messages=[{"role": "user", "content": "What are my job responsibilities?"}]
        ),
        phase=AgentPhase.RUNTIME,
    )
    retrieved_topics: List[RetrievedTopic] = sorted(
        topic_retriever_ouput.topics, key=lambda t: t.topic.topic
    )
    assert len(retrieved_topics) == len(topics)
    for retrieved_topic, topic in zip(retrieved_topics, topics):
        assert retrieved_topic.topic.topic == topic.topic
        assert retrieved_topic.topic.subject == topic.subject
        assert retrieved_topic.topic.expertise == topic.expertise
        assert retrieved_topic.topic.metadata == {}
        assert retrieved_topic.distance is not None
    for topic in retrieved_topics:
        print(topic)


def test_topic_retriever_wo_levels_of_expertise(
    caplog, create_chroma: Callable[..., ClientAPI]
):
    caplog.set_level(logging.INFO, TopicRetrievalMiddleware.__module__)
    caplog.set_level(logging.INFO, ChromaDBTopicRetriever.__module__)
    col_name = "test.collection"
    topics: List[TopicInfo] = [
        TopicInfo(topic="Job 1", subject="s_1"),
        TopicInfo(topic="Job 2", subject="s_1"),
    ]
    client = create_chroma(
        col_name,
        [topic.topic for topic in topics],
        [{"subject": topic.subject} for topic in topics],
    )
    topic_retriever_settings = {
        "name": "chromadb",
        "config": {"collection": col_name, "instance": {"client": client}},
    }
    topic_retriever = TopicRetrievalMiddleware.from_settings(
        Settings(**topic_retriever_settings)
    )
    topic_retriever_ouput: TopicRetrievalRunOutput = topic_retriever.process(
        data=TopicRetrievalRunInput(
            messages=[{"role": "user", "content": "What are my job responsibilities?"}]
        ),
        phase=AgentPhase.RUNTIME,
    )
    retrieved_topics: List[RetrievedTopic] = sorted(
        topic_retriever_ouput.topics, key=lambda t: t.topic.topic
    )
    assert len(retrieved_topics) == len(topics)
    for retrieved_topic, topic in zip(retrieved_topics, topics):
        assert retrieved_topic.topic.topic == topic.topic
        assert retrieved_topic.topic.subject == topic.subject
        assert retrieved_topic.topic.expertise is None
        assert retrieved_topic.topic.metadata == {}
        assert retrieved_topic.distance is not None

    for topic in retrieved_topics:
        print(topic)
