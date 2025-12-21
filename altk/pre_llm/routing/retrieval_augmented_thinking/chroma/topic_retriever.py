import logging
import os
from pathlib import Path
from typing import Any, Dict, List

from chromadb import QueryResult
from chromadb.api import ClientAPI
from chromadb.config import DEFAULT_DATABASE, Settings

from altk.pre_llm.core.types import RetrievedTopic, TopicInfo
from altk.pre_llm.routing.elapsed_time_logger import processing_time_logger
from altk.pre_llm.routing.retrieval_augmented_thinking.chroma.common import (
    ChromaDBConfig,
    EphemeralChromaDBConfig,
    LocalChromaDBConfig,
    RemoteChromaDBConfig,
)
from altk.pre_llm.core.types import (
    TopicRetriever,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.topic_retriever import (
    topic_retriever,
)

logger = logging.getLogger(__name__)


@topic_retriever.register("chromadb")
class ChromaDBTopicRetriever:
    def __init__(
        self,
        collection: str,
        client: ClientAPI | None = None,
        db_path: str | Path | None = None,
        host: str | None = None,
        port: int | None = None,
        password: str | None = None,
        ssl: bool = False,
        ssl_verify: bool | None = None,
        database: str = DEFAULT_DATABASE,
        **kwargs,
    ):
        if client:
            logger.info("Using provided ChromaDB client")
            self.client = client
        elif db_path:
            from chromadb import PersistentClient

            logger.info(f"Using in-process ChromaDB instance ({str(db_path)})")
            self.client = PersistentClient(
                path=str(db_path), database=database, **kwargs
            )
        elif host and port:
            from chromadb import HttpClient

            logger.info(f"Using remote ChromaDB instance ({host}:{port})")
            settings: Settings | None = None
            if password is not None:
                settings = Settings(
                    chroma_client_auth_provider="chromadb.auth.token_authn.TokenAuthClientProvider",
                    chroma_client_auth_credentials=password,
                    chroma_auth_token_transport_header="Authorization",
                    chroma_server_ssl_verify=ssl_verify,
                )
            self.client = HttpClient(
                host, port, ssl, settings=settings, database=database, **kwargs
            )
        else:
            raise ValueError(
                "Couldn't setup a chroma DB client. Ensure you're giving either a chroma DB host and port or a path to the chroma db data files"
            )
        self.collection = self.client.get_collection(name=collection)

    @classmethod
    def from_settings(cls, settings: ChromaDBConfig | Dict) -> TopicRetriever:
        _settings = (
            ChromaDBConfig(**settings) if isinstance(settings, Dict) else settings
        )
        db_path = None
        host = None
        port = None
        client = None
        ssl = False
        ssl_verify = None
        if isinstance(_settings.instance, EphemeralChromaDBConfig):
            client = _settings.instance.client
        elif isinstance(_settings.instance, LocalChromaDBConfig):
            db_path = _settings.instance.db_path
        elif isinstance(_settings.instance, RemoteChromaDBConfig):
            host = _settings.instance.host
            port = _settings.instance.port
            ssl = _settings.instance.ssl
            ssl_verify = _settings.instance.ssl_verify
        else:
            raise ValueError(
                "Couldn't setup a chroma DB client. Ensure you're giving either a chroma DB host and port or a path to the chroma db data files"
            )
        return cls(
            collection=_settings.collection,
            database=_settings.database,
            db_path=db_path,
            host=host,
            port=port,
            password=os.getenv("CHROMADB_PASSWORD"),
            client=client,
            ssl=ssl,
            ssl_verify=ssl_verify,
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
        result: QueryResult = self.collection.query(
            query_texts=[query], n_results=n_results, **query_kwargs
        )
        results: List[RetrievedTopic] = []
        for topic, topic_metadata, distance in zip(
            result["documents"][0], result["metadatas"][0], result["distances"][0]
        ):
            topic = TopicInfo(
                topic=topic,
                subject=topic_metadata["subject"],
                expertise=topic_metadata.get("expertise"),
                metadata={
                    k: v
                    for k, v in topic_metadata.items()
                    if k
                    not in (
                        "subject",
                        "expertise",
                    )
                },
            )
            if distance_threshold is None or distance < distance_threshold:
                results.append(RetrievedTopic(topic=topic, distance=distance))
            if len(results) == n_results:
                break
        return results
