import logging
from typing import List

from chromadb import PersistentClient
from chromadb.api import ClientAPI
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from sentence_transformers import SentenceTransformer

from altk.pre_llm.core.types import (
    EmbeddedTopic,
    RetrievedTopic,
    TopicInfo,
    TopicLoadingInput,
    TopicRetrievalRunInput,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.chroma.topic_retriever import (
    ChromaDBTopicRetriever,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.chroma.topic_sink_content_provider import (
    ChromaDBProvider,
)
from altk.pre_llm.core.types import (
    TopicRetrievalRunOutput,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.topic_loading.topic_loading import (
    TopicLoadingMiddleware,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.topic_retriever.topic_retriever import (
    TopicRetrievalMiddleware,
)
from altk.core.toolkit import AgentPhase


def test_preembedded_topic_loading_and_filtering_using_ephemeral_chroma(
    chroma: ClientAPI,
):
    embedding_model_name = "ibm-granite/granite-embedding-107m-multilingual"
    embedding_model = SentenceTransformer(embedding_model_name)

    topics = [
        EmbeddedTopic(
            topic=TopicInfo(
                topic="Job tasks",
                subject="job_offering",
                metadata={"env_1": "live", "env_2": "dark_lunch"},
            ),
            embeddings=embedding_model.encode("Job tasks").tolist(),
        ),
        EmbeddedTopic(
            topic=TopicInfo(
                topic="Job responsibilities",
                subject="job_offering",
                metadata={"env_1": "staging", "env_2": "testing"},
            ),
            embeddings=embedding_model.encode("Job responsibilities").tolist(),
        ),
    ]
    topic_loading = TopicLoadingMiddleware(
        topics_sink=ChromaDBProvider(collection="topics", client=chroma)
    )
    topic_loading.process(
        data=TopicLoadingInput(topics=topics), phase=AgentPhase.BUILDTIME
    )

    topic_retriever = TopicRetrievalMiddleware(
        topic_retriever=ChromaDBTopicRetriever(collection="topics", client=chroma)
    )

    # Get topics having metadata fields `env_1` or `env_2` containing any of the values ["live", "dark_lunch"]
    topic_retriever_ouput: TopicRetrievalRunOutput = topic_retriever.process(
        data=TopicRetrievalRunInput(
            messages=[{"role": "user", "content": "What are my job responsibilities?"}],
            query_kwargs={
                "where": {
                    "$or": [
                        {"env_1": {"$in": ["live", "dark_lunch"]}},
                        {"env_2": {"$in": ["live", "dark_lunch"]}},
                    ]
                }
            },
        ),
        phase=AgentPhase.RUNTIME,
    )
    retrieved_topics: List[RetrievedTopic] = sorted(
        topic_retriever_ouput.topics, key=lambda t: t.topic
    )
    assert len(retrieved_topics) == 1
    assert retrieved_topics[0].topic.topic == "Job tasks"
    assert retrieved_topics[0].topic.subject == "job_offering"
    assert retrieved_topics[0].topic.metadata == {
        "env_1": "live",
        "env_2": "dark_lunch",
    }
    assert retrieved_topics[0].distance is not None

    # Get topics having metadata fields `env_1` or `env_2` containing any of the values ["testing", "dark_lunch"]
    topic_retriever_ouput: TopicRetrievalRunOutput = topic_retriever.process(
        data=TopicRetrievalRunInput(
            messages=[{"role": "user", "content": "What are my job responsibilities?"}],
            query_kwargs={
                "where": {
                    "$or": [
                        {"env_1": {"$in": ["testing", "dark_lunch"]}},
                        {"env_2": {"$in": ["testing", "dark_lunch"]}},
                    ]
                }
            },
        ),
        phase=AgentPhase.RUNTIME,
    )
    retrieved_topics = sorted(topic_retriever_ouput.topics, key=lambda t: t.topic)
    assert len(retrieved_topics) == 2
    assert retrieved_topics[0].topic.topic == "Job tasks"
    assert retrieved_topics[0].topic.subject == "job_offering"
    assert retrieved_topics[0].topic.metadata == {
        "env_1": "live",
        "env_2": "dark_lunch",
    }
    assert retrieved_topics[0].distance is not None
    assert retrieved_topics[1].topic.topic == "Job responsibilities"
    assert retrieved_topics[1].topic.subject == "job_offering"
    assert retrieved_topics[1].topic.metadata == {
        "env_1": "staging",
        "env_2": "testing",
    }
    assert retrieved_topics[1].distance is not None

    # There are no topics having metadata fields `env_1` or `env_2` with any of these values: ["user_acceptance", "load_testing"]
    topic_retriever_ouput: TopicRetrievalRunOutput = topic_retriever.process(
        data=TopicRetrievalRunInput(
            messages=[{"role": "user", "content": "What are my job responsibilities?"}],
            query_kwargs={
                "where": {
                    "$or": [
                        {"env_1": {"$in": ["user_acceptance", "load_testing"]}},
                        {"env_2": {"$in": ["user_acceptance", "load_testing"]}},
                    ]
                }
            },
        ),
        phase=AgentPhase.RUNTIME,
    )
    retrieved_topics = sorted(topic_retriever_ouput.topics, key=lambda t: t.topic)
    assert len(retrieved_topics) == 0

    # Return only 1 topic using the n_results param
    topic_retriever_ouput: TopicRetrievalRunOutput = topic_retriever.process(
        data=TopicRetrievalRunInput(
            messages=[{"role": "user", "content": "What are my job responsibilities?"}],
            n_results=1,
        ),
        phase=AgentPhase.RUNTIME,
    )
    retrieved_topics = sorted(topic_retriever_ouput.topics, key=lambda t: t.topic)
    assert len(retrieved_topics) == 1


def test_preembedded_topic_loading_and_filtering_using_persistent_chroma(
    tmpdir, caplog
):
    # Chroma DB persistent files will be created under the temp directory tmpdir that was created by the tmpdir pytest fixture
    caplog.set_level(logging.DEBUG, logger=ChromaDBProvider.__module__)
    caplog.set_level(logging.DEBUG, logger=ChromaDBTopicRetriever.__module__)

    embedding_model_name = "ibm-granite/granite-embedding-107m-multilingual"
    embedding_model = SentenceTransformer(embedding_model_name)

    topics = [
        EmbeddedTopic(
            topic=TopicInfo(
                topic="Job tasks",
                subject="job_offering",
                metadata={"env": "dark_lunch"},
            ),
            embeddings=embedding_model.encode("Job tasks").tolist(),
        ),
        EmbeddedTopic(
            topic=TopicInfo(
                topic="Job skills",
                subject="job_offering",
                metadata={"env": "testing"},
            ),
            embeddings=embedding_model.encode("Job skills").tolist(),
        ),
    ]

    topic_loading = TopicLoadingMiddleware(
        topics_sink=ChromaDBProvider(collection="topics", db_path=tmpdir)
    )
    topic_loading.process(
        data=TopicLoadingInput(topics=topics), phase=AgentPhase.BUILDTIME
    )

    topic_retriever = TopicRetrievalMiddleware(
        topic_retriever=ChromaDBTopicRetriever(
            collection="topics", client=PersistentClient(path=tmpdir)
        )
    )

    # Get topics whose metadata fields contains any of these values: ["live", "dark_lunch"]
    topic_retriever_ouput: TopicRetrievalRunOutput = topic_retriever.process(
        data=TopicRetrievalRunInput(
            messages=[{"role": "user", "content": "What are my job responsibilities?"}],
            query_kwargs={"where": {"env": "dark_lunch"}},
        ),
        phase=AgentPhase.RUNTIME,
    )
    retrieved_topics: List[RetrievedTopic] = sorted(
        topic_retriever_ouput.topics, key=lambda t: t.topic
    )
    assert len(retrieved_topics) == 1
    assert retrieved_topics[0].topic.topic == "Job tasks"
    assert retrieved_topics[0].topic.subject == "job_offering"
    assert retrieved_topics[0].topic.metadata == {"env": "dark_lunch"}
    assert retrieved_topics[0].distance is not None


def test_topic_loading_with_embedding_function(caplog, tmpdir):
    caplog.set_level(logging.DEBUG, logger=ChromaDBProvider.__module__)

    topics = [
        TopicInfo(
            topic="Job tasks",
            subject="job_offering",
            metadata={"env": "dark_lunch"},
        ),
        TopicInfo(
            topic="Job skills",
            subject="job_offering",
            metadata={"env": "testing"},
        ),
    ]

    topic_loading = TopicLoadingMiddleware(
        topics_sink=ChromaDBProvider(
            collection="topics",
            db_path=tmpdir,
            embedding_function=SentenceTransformerEmbeddingFunction(
                "ibm-granite/granite-embedding-107m-multilingual"
            ),
        )
    )
    topic_loading.process(
        data=TopicLoadingInput(topics=topics),
        phase=AgentPhase.BUILDTIME,
    )

    chroma_client = PersistentClient(path=tmpdir)
    topic_retriever = TopicRetrievalMiddleware(
        topic_retriever=ChromaDBTopicRetriever(
            collection="topics", client=chroma_client
        )
    )

    # Get topics whose metadata fields contains any of these values: ["live", "dark_lunch"]
    topic_retriever_ouput: TopicRetrievalRunOutput = topic_retriever.process(
        data=TopicRetrievalRunInput(
            messages=[{"role": "user", "content": "What are my job responsibilities?"}],
            query_kwargs={"where": {"env": "dark_lunch"}},
        ),
        phase=AgentPhase.RUNTIME,
    )
    retrieved_topics: List[RetrievedTopic] = sorted(
        topic_retriever_ouput.topics, key=lambda t: t.topic
    )
    assert len(retrieved_topics) == 1
    assert retrieved_topics[0].topic.topic == "Job tasks"
    assert retrieved_topics[0].topic.subject == "job_offering"
    assert retrieved_topics[0].topic.metadata == {"env": "dark_lunch"}
    assert retrieved_topics[0].distance is not None
