import logging
import os
from typing import Any, Dict, List
from warnings import warn

try:
    from pymilvus import DataType, Function, FunctionType, MilvusClient
    from pymilvus.model.base import BaseEmbeddingFunction
except ImportError as err:
    raise ImportError(
        'You need to install the routing dependencies to use this component. Run `pip install "agent-lifecycle-toolkit[routing]"`'
    ) from err

from altk.pre_llm.core.types import TopicInfo
from altk.pre_llm.routing.elapsed_time_logger import processing_time_logger
from altk.pre_llm.core.types import (
    EmbeddedTopic,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.milvus.common import (
    AnnSearchConfig,
    FullTextSearchConfig,
    MilvusConfig,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.topic_extractor.topic_extractor import (
    TopicExtractionMiddleware,
)

logger = logging.getLogger(__name__)


class MilvusTopicsSinkConfig(MilvusConfig):
    full_text_search: FullTextSearchConfig = FullTextSearchConfig()
    ann_search: AnnSearchConfig | None = None


@TopicExtractionMiddleware.register_topics_sink()
class MilvusProvider:
    def __init__(
        self,
        milvus_uri: str = "http://localhost:19530",
        milvus_token: str | None = None,
        milvus_db: str | None = None,
        collection_name: str = "topics",
        full_text_search_config: FullTextSearchConfig | None = None,
        ann_search_config: AnnSearchConfig | None = None,
    ) -> None:
        self.client = MilvusClient(
            uri=milvus_uri, token=milvus_token or "", db_name=milvus_db or ""
        )
        logger.info(f"Using Milvus {milvus_uri=} {milvus_db=}")
        self.collection_name = collection_name
        self.ann_search_config = ann_search_config
        self.full_text_search_config = full_text_search_config or FullTextSearchConfig()
        if not self.client.has_collection(collection_name):
            if ann_search_config is None:
                self.with_full_text_search(self.full_text_search_config)
            else:
                self.with_ann_text_search(ann_search_config)

    @classmethod
    def create_topics_sink(
        cls, settings: MilvusTopicsSinkConfig | Dict
    ) -> "MilvusProvider":
        logger.info(f"Creating Milvus Topics Sink with settings:\n{settings}")
        _settings = (
            MilvusTopicsSinkConfig(**settings)
            if isinstance(settings, Dict)
            else settings
        )
        return cls(
            milvus_uri=_settings.uri,
            milvus_token=os.getenv("MILVUS_TOKEN"),
            milvus_db=_settings.database,
            collection_name=_settings.collection,
            full_text_search_config=_settings.full_text_search,
            ann_search_config=_settings.ann_search,
        )

    def with_full_text_search(self, config: FullTextSearchConfig):
        schema = self.client.create_schema(
            enable_dynamic_field=True
        )  # to store topic metadata fields

        schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
        schema.add_field(
            field_name="text",
            datatype=DataType.VARCHAR,
            max_length=config.topic_field_max_length,
            enable_analyzer=True,
        )
        schema.add_field(
            field_name="subject",
            datatype=DataType.VARCHAR,
            max_length=config.subject_field_max_length,
        )
        schema.add_field(field_name="sparse", datatype=DataType.SPARSE_FLOAT_VECTOR)

        bm25_function = Function(
            name="text_bm25_emb",  # Function name
            input_field_names=[
                "text"
            ],  # Name of the VARCHAR field containing raw text data
            output_field_names=[
                "sparse"
            ],  # Name of the SPARSE_FLOAT_VECTOR field reserved to store generated embeddings
            function_type=FunctionType.BM25,  # Set to `BM25`
        )

        schema.add_function(bm25_function)

        index_params = self.client.prepare_index_params()

        index_params.add_index(
            field_name="sparse",
            index_type="SPARSE_INVERTED_INDEX",
            metric_type="BM25",
            params=config.sparse_index_params,
        )
        self.client.create_collection(
            collection_name=self.collection_name,
            schema=schema,
            index_params=index_params,
        )
        logger.info(
            f"Collection {self.collection_name} created and setup for full text search using the BM25 algorithm"
        )

    def with_ann_text_search(self, config: AnnSearchConfig):
        schema = self.client.create_schema(
            enable_dynamic_field=True
        )  # to store topic metadata fields
        schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
        schema.add_field(
            field_name="text",
            datatype=DataType.VARCHAR,
            max_length=config.topic_field_max_length,
            enable_analyzer=True,
        )
        schema.add_field(
            field_name="subject",
            datatype=DataType.VARCHAR,
            max_length=config.subject_field_max_length,
        )
        schema.add_field(
            field_name="vector",
            datatype=DataType.FLOAT_VECTOR,
            dim=config.vector_dimensions or config.get_embedding_function().dim,
        )

        index_params = self.client.prepare_index_params()
        index_params.add_index(
            "vector", index_type="AUTOINDEX", metric_type=config.metric_type
        )

        self.client.create_collection(
            collection_name=self.collection_name,
            schema=schema,
            index_params=index_params,
        )
        logger.info(
            f"Collection {self.collection_name} created and setup for semantic search"
        )

    def _add_topics_full_text_search(self, topics: List[TopicInfo]):
        documents = [
            (
                {
                    "id": i,
                    "text": topics[i].topic,
                    "subject": topics[i].subject,
                    "expertise": topics[i].expertise,
                    **topics[i].metadata,
                }
                if topics[i].expertise
                else {
                    "id": i,
                    "text": topics[i].topic,
                    "subject": topics[i].subject,
                    **topics[i].metadata,
                }
            )
            for i in range(len(topics))
        ]
        logger.info(f"Inserting {len(documents)} documents in the Milvus DB")
        self.client.insert(
            self.collection_name,
            documents,
        )
        logger.info(f"{len(documents)} documents inserted in the Milvus DB")

    def _add_topics_ann_search(
        self,
        topics: List[TopicInfo],
        emb_fn: BaseEmbeddingFunction | None = None,
        embeddings: list[float] | None = None,
    ):
        if not embeddings and emb_fn is None:
            raise ValueError(
                "An embedding function must be provided to add topics with ANN search."
            )
        _embeddings = embeddings or emb_fn.encode_documents(
            [topic.topic for topic in topics]
        )  # Precompute embeddings
        documents = [
            (
                {
                    "id": i,
                    "vector": _embeddings[i],
                    "text": topics[i].topic,
                    "subject": topics[i].subject,
                    "expertise": topics[i].expertise,
                    **topics[i].metadata,
                }
                if topics[i].expertise
                else {
                    "id": i,
                    "vector": _embeddings[i],
                    "text": topics[i].topic,
                    "subject": topics[i].subject,
                    **topics[i].metadata,
                }
            )
            for i in range(len(_embeddings))
        ]
        logger.info(f"Inserting {len(documents)} documents in the Milvus DB")
        self.client.insert(
            self.collection_name,
            documents,
        )
        logger.info(f"{len(documents)} documents inserted in the Milvus DB")

    @processing_time_logger(logger)
    def add_topics(self, topics: List[TopicInfo]):
        if self.ann_search_config is None:
            self._add_topics_full_text_search(topics)
        else:
            self._add_topics_ann_search(
                topics,
                self.ann_search_config.get_embedding_function(),
            )

    @processing_time_logger(logger)
    def add_embedded_topics(
        self, topics: List[EmbeddedTopic], emb_fn: Any | None = None
    ):
        warn(
            "Using the emb_fn parameter when calling the add_embedded_topics TopicSink method is deprecated. You should set an embedding function when creating the TopicSink",
            DeprecationWarning,
            stacklevel=2,
        )
        if self.ann_search_config is None:
            raise TypeError(
                "Inserting preembedded topics when using Milvus Full Text Search (https://milvus.io/docs/full-text-search.md) is not supported."
            )
        self._add_topics_ann_search(
            [topic.topic for topic in topics],
            embeddings=(
                emb_fn.encode_documents(
                    [embedded_topic.topic.topic for embedded_topic in topics]
                )
                if emb_fn
                else [topic.embeddings for topic in topics]
            ),
        )
