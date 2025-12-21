import logging
import os
from typing import Any, Dict, List

try:
    from pymilvus import MilvusClient
except ImportError as err:
    raise ImportError(
        'You need to install the routing dependencies to use this component. Run `pip install "agent-lifecycle-toolkit[routing]"`'
    ) from err

from altk.pre_llm.core.types import TopicInfo
from altk.pre_llm.routing.elapsed_time_logger import processing_time_logger
from altk.pre_llm.core.types import (
    RetrievedTopic,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.milvus.common import (
    AnnSearchConfig,
    MilvusConfig,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.milvus.error import (
    SearchTypeMismatchError,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.topic_retriever import (
    topic_retriever,
)

logger = logging.getLogger(__name__)


class MilvusTopicRetrieverConfig(MilvusConfig):
    metadata_fields: list[str] = []
    ann_search: AnnSearchConfig | None = None


@topic_retriever.register("milvus")
class MilvusTopicRetriever:
    def __init__(
        self,
        milvus_uri: str = "http://localhost:19530",
        milvus_token: str | None = None,
        milvus_db: str | None = None,
        collection_name: str = "topics",
        metadata_fields: list[str] | None = None,
        ann_search_config: AnnSearchConfig | None = None,
    ) -> None:
        self.client = MilvusClient(
            uri=milvus_uri, token=milvus_token or "", db_name=milvus_db or ""
        )
        if not self.client.has_collection(collection_name):
            raise ValueError(
                f"Collection {collection_name} does not exist in the Milvus DB {milvus_uri}"
            )
        self.collection_name = collection_name
        self.metadata_fields = metadata_fields or []
        self.ann_search_config = ann_search_config
        self._check_collection_search_type()

    def _check_collection_search_type(self):
        collection_data = self.client.describe_collection(self.collection_name)
        field_name = "vector" if self.ann_search_config else "sparse"
        if not any(
            [
                field.get("name") == field_name
                for field in collection_data.get("fields", [])
            ]
        ):
            if self.ann_search_config:
                raise SearchTypeMismatchError(
                    f"The collection '{self.collection_name}' was not setup to do semantic search"
                )
            else:
                raise SearchTypeMismatchError(
                    f"The collection '{self.collection_name}' was not setup to do full text search"
                )

    @classmethod
    def from_settings(
        cls, settings: MilvusTopicRetrieverConfig | Dict
    ) -> "MilvusTopicRetriever":
        _settings = (
            MilvusTopicRetrieverConfig(**settings)
            if isinstance(settings, Dict)
            else settings
        )
        return cls(
            milvus_uri=_settings.uri,
            milvus_token=os.getenv("MILVUS_TOKEN"),
            milvus_db=_settings.database,
            collection_name=_settings.collection,
            metadata_fields=_settings.metadata_fields,
            ann_search_config=_settings.ann_search,
        )

    @processing_time_logger(logger)
    def get_topics(
        self,
        query: str,
        n_results: int = 10,
        query_kwargs: Dict[str, Any] | None = None,
        distance_threshold: float | None = None,
    ) -> List[RetrievedTopic]:
        if query_kwargs is None:
            query_kwargs = dict()

        logger.debug(
            f"Getting topic documents for user query '{query}', {n_results=}, {query_kwargs=}"
        )
        search_params = {
            "params": {
                "drop_ratio_search": 0.2  # the smallest 20% of values in the query vector will be ignored during the search.
            },
        }
        if distance_threshold:
            search_params["params"]["radius"] = distance_threshold
        query_kwargs = {"search_params": search_params} | query_kwargs
        result = self.client.search(
            collection_name=self.collection_name,
            data=(
                self.ann_search_config.get_embedding_function().encode_queries([query])
                if self.ann_search_config
                else [query]
            ),
            anns_field="vector" if self.ann_search_config else "sparse",
            output_fields=[
                "text",
                "subject",
                "expertise",
            ]
            + self.metadata_fields,
            limit=n_results,
            **query_kwargs,
        )[0]
        results: List[RetrievedTopic] = []
        for document in result:
            topic = TopicInfo(
                topic=document["entity"]["text"],
                subject=document["entity"]["subject"],
                expertise=document["entity"].get("expertise"),
                metadata={
                    k: v
                    for k, v in document["entity"].items()
                    if k not in ("text", "subject", "expertise")
                },
            )
            results.append(RetrievedTopic(topic=topic, distance=document["distance"]))
        return results
