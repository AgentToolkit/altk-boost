import logging
import os
import uuid
import warnings
from pathlib import Path
from typing import Any, Dict, Iterator, List, Literal, Optional

from chromadb import GetResult
from chromadb.api import ClientAPI
from chromadb.api.types import EmbeddingFunction
from chromadb.config import DEFAULT_DATABASE, Settings
from chromadb.errors import NotFoundError
from chromadb.utils.batch_utils import create_batches
from pydantic import Field

from altk.pre_llm.core.types import TopicInfo
from altk.pre_llm.routing.elapsed_time_logger import processing_time_logger
from altk.pre_llm.routing.retrieval_augmented_thinking.chroma.common import (
    ChromaDBConfig,
    EphemeralChromaDBConfig,
    LocalChromaDBConfig,
    RemoteChromaDBConfig,
)
from altk.pre_llm.core.types import (
    EmbeddedTopic,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.topic_extractor.topic_extractor import (
    TopicExtractionMiddleware,
)

logger = logging.getLogger(__name__)

DEFAULT_PAGE_SIZE = None
DEAULT_OFFSET = None


class ChromaDBProviderSettings(ChromaDBConfig):
    model_config = {"arbitrary_types_allowed": True}
    dest_collection: str | None = None
    page_size: int = DEFAULT_PAGE_SIZE
    offset: int = DEAULT_OFFSET
    n_docs: int | None = None
    embedding_function_provider: (
        Literal[
            "sentence_transformer",
            "openai",
            "google_generative_ai",
            "cohere",
            "hugging_face",
        ]
        | None
    ) = Field(
        description="Embedding function implementation. See https://docs.trychroma.com/docs/embeddings/embedding-functions",
        default=None,
    )
    embedding_function_config: Dict[str, Any] | None = Field(
        description="Embedding function parameters. See the specific embedding function parameters in https://docs.trychroma.com/docs/embeddings/embedding-functions",
        default=None,
    )
    embedding_function: EmbeddingFunction | None = Field(
        description="A pre instantiated ChromaDB EmbeddingFunction",
        default=None,
    )

    def get_embedding_function(self) -> EmbeddingFunction | None:
        if self.embedding_function:
            return self.embedding_function
        if (
            self.embedding_function_config is None
            or self.embedding_function_provider is None
        ):
            return None
        import chromadb.utils.embedding_functions as embedding_functions

        if self.embedding_function_provider == "openai":
            return embedding_functions.OpenAIEmbeddingFunction.build_from_config(
                self.embedding_function_config
            )
        if self.embedding_function_provider == "google_generative_ai":
            return embedding_functions.GoogleGenerativeAiEmbeddingFunction.build_from_config(
                self.embedding_function_config
            )
        if self.embedding_function_provider == "cohere":
            return embedding_functions.CohereEmbeddingFunction.build_from_config(
                self.embedding_function_config
            )
        if self.embedding_function_provider == "hugging_face":
            return embedding_functions.HuggingFaceEmbeddingFunction.build_from_config(
                self.embedding_function_config
            )
        if self.embedding_function_provider == "sentence_transformer":
            return embedding_functions.SentenceTransformerEmbeddingFunction.build_from_config(
                self.embedding_function_config
            )


@TopicExtractionMiddleware.register_content_provider()
@TopicExtractionMiddleware.register_topics_sink()
class ChromaDBProvider:
    def __init__(
        self,
        collection: str,
        dest_collection: str | None = None,
        db_path: str | Path | None = None,
        host: str | None = None,
        port: int | None = None,
        password: str | None = None,
        ssl: bool = False,
        ssl_verify: bool | None = None,
        client: ClientAPI | None = None,
        page_size: int | None = DEFAULT_PAGE_SIZE,
        offset: int | None = DEAULT_OFFSET,
        n_docs: int | None = None,
        embedding_function: Optional[EmbeddingFunction] = None,
        database: str = DEFAULT_DATABASE,
        **kwargs,
    ):
        self.collection_name = collection
        self.dest_collection_name = dest_collection
        self.page_size = page_size
        self.offset = offset
        self.n_docs = n_docs
        self.chroma_client: ClientAPI | None = None
        self.embedding_function = embedding_function
        if client:
            logger.info("Using provided ChromaDB client")
            self.chroma_client = client
        elif db_path:
            from chromadb import PersistentClient

            logger.info(f"Using in-process ChromaDB instance ({str(db_path)})")
            self.chroma_client = PersistentClient(
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
            self.chroma_client = HttpClient(
                host, port, ssl, settings=settings, database=database, **kwargs
            )
        if not self.chroma_client:
            raise ValueError(
                "Couldn't setup a chroma DB client. Ensure you're giving either a chroma DB host and port or a path to the chroma db data files"
            )

    @classmethod
    def create_content_provider(
        cls, settings: ChromaDBProviderSettings | Dict
    ) -> "ChromaDBProvider":
        if isinstance(settings, Dict):
            _settings = ChromaDBProviderSettings(**settings)
        else:
            _settings = settings
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
        return cls(
            collection=_settings.collection,
            dest_collection=_settings.dest_collection,
            db_path=db_path,
            host=host,
            port=port,
            password=os.getenv("CHROMADB_PASSWORD"),
            ssl=ssl,
            ssl_verify=ssl_verify,
            client=client,
            page_size=_settings.page_size,
            offset=_settings.offset,
            n_docs=_settings.n_docs,
            database=_settings.database,
        )

    @classmethod
    def create_topics_sink(
        cls, settings: ChromaDBProviderSettings | Dict
    ) -> "ChromaDBProvider":
        if isinstance(settings, Dict):
            _settings = ChromaDBProviderSettings(**settings)
        else:
            _settings = settings
        db_path = None
        host = None
        port = None
        client = None
        if isinstance(_settings.instance, EphemeralChromaDBConfig):
            client = _settings.instance.client
        elif isinstance(_settings.instance, LocalChromaDBConfig):
            db_path = _settings.instance.db_path
        elif isinstance(_settings.instance, RemoteChromaDBConfig):
            host = _settings.instance.host
            port = _settings.instance.port
        return cls(
            collection=_settings.collection,
            db_path=db_path,
            host=host,
            port=port,
            password=os.getenv("CHROMADB_PASSWORD"),
            client=client,
            embedding_function=_settings.get_embedding_function(),
            database=_settings.database,
        )

    def get_content(self) -> Iterator[str]:
        yield from self.get_docs_from_collection(self.collection_name)

    def get_docs_from_collection(self, collection_name) -> Iterator[str]:
        collection = self.chroma_client.get_collection(collection_name)
        n_docs = self.n_docs or collection.count()
        offset = self.offset or 0
        retrieved_docs = 0
        page_size = (
            n_docs
            if (self.page_size and self.page_size > n_docs) or not self.page_size
            else self.page_size
        )
        logger.info(
            f"Retrieving documents from collection {collection_name} {page_size=} {offset=}"
        )
        while offset < n_docs:
            response: GetResult = collection.get(offset=offset, limit=page_size)
            documents = response.get("documents")
            retrieved_docs += len(documents)
            logger.debug(
                f"{len(documents)} documents retrieved from collection {collection_name}"
            )
            offset += retrieved_docs
            yield from documents

    @processing_time_logger(logger)
    def add_topics(self, topics: List[TopicInfo]):
        logger.info(
            f"Adding {len(topics)} topics to collection {self.dest_collection_name or self.collection_name}"
        )
        collection = None
        if self.embedding_function:
            logger.info(f"Using embedding function {self.embedding_function.name()}")
            logger.debug(
                f"Embedding function config: {self.embedding_function.get_config()}"
            )
            collection = self.chroma_client.get_or_create_collection(
                self.dest_collection_name or self.collection_name,
                embedding_function=self.embedding_function,
            )
        else:
            collection = self.chroma_client.get_or_create_collection(
                self.dest_collection_name or self.collection_name
            )

        # workaround to support adding large amounts of topics at a time: https://cookbook.chromadb.dev/strategies/batching/#creating-batches
        batches = create_batches(
            api=self.chroma_client,
            ids=[f"{uuid.uuid4()}" for _ in range(len(topics))],
            documents=[topic.topic for topic in topics],
            metadatas=[
                (
                    {
                        "subject": topic.subject,
                        "expertise": topic.expertise,
                        **topic.metadata,
                    }
                    if topic.expertise
                    else {"subject": topic.subject, **topic.metadata}
                )
                for topic in topics
            ],
        )
        for batch in batches:
            logger.info(f"Adding batch of size {len(batch[0])}")
            collection.add(
                ids=batch[0],
                documents=batch[3],
                metadatas=batch[2],
            )

    @processing_time_logger(logger)
    def add_embedded_topics(
        self, topics: List[EmbeddedTopic], emb_fn: EmbeddingFunction | None = None
    ):
        if emb_fn is not None:
            warnings.warn(
                "Passing the embedding function in the `emb_fn` parameter is deprecated, please specify an embedding function when creating the `ChromaDBProvider`.",
                DeprecationWarning,
                stacklevel=2,
            )
        logger.info(
            f"Adding {len(topics)} pre-embedded topics to collection {self.dest_collection_name or self.collection_name}"
        )
        _emb_fn = self.embedding_function or emb_fn
        collection = None
        if _emb_fn:
            logger.info(f"Using embedding function {_emb_fn.name()}")
            logger.debug(f"Embedding function config: {_emb_fn.get_config()}")
            collection = self.chroma_client.get_or_create_collection(
                self.dest_collection_name or self.collection_name,
                embedding_function=_emb_fn,
            )
        else:
            collection = self.chroma_client.get_or_create_collection(
                self.dest_collection_name or self.collection_name
            )

        # workaround to support adding large amounts of topics at a time: https://cookbook.chromadb.dev/strategies/batching/#creating-batches
        embeddings = (
            [topic.embeddings for topic in topics]
            if topics and all([topic.embeddings is not None for topic in topics])
            else None
        )
        batches = create_batches(
            api=self.chroma_client,
            ids=[f"{uuid.uuid4()}" for _ in range(len(topics))],
            documents=[embedded_topic.topic.topic for embedded_topic in topics],
            metadatas=[
                (
                    {
                        "subject": embedded_topic.topic.subject,
                        "expertise": embedded_topic.topic.expertise,
                        **embedded_topic.topic.metadata,
                    }
                    if embedded_topic.topic.expertise
                    else {
                        "subject": embedded_topic.topic.subject,
                        **embedded_topic.topic.metadata,
                    }
                )
                for embedded_topic in topics
            ],
            embeddings=embeddings,
        )
        for batch in batches:
            logger.info(f"Adding batch of size {len(batch[0])}")
            collection.add(
                ids=batch[0],
                documents=batch[3],
                embeddings=batch[1],
                metadatas=batch[2],
            )

    def reset(self):
        # Mostly called from tests
        collection_to_delete = self.dest_collection_name or self.collection_name
        try:
            self.chroma_client.delete_collection(collection_to_delete)
            logger.info(f"Collection {collection_to_delete} deleted")
        except NotFoundError:
            logger.warning(f"Collection {collection_to_delete} not found")
            # ignore the exception as it was raised because the collection doesn't exist
            pass
