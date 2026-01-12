from typing import (
    Any,
    Dict,
    Generic,
    Iterable,
    Iterator,
    List,
    Literal,
    Optional,
    Protocol,
    TypeVar,
    runtime_checkable,
)

from pydantic import BaseModel, ConfigDict, Field

from altk.core.toolkit import ComponentInput, ComponentOutput

T = TypeVar("T")


class TopicInfo(BaseModel):
    topic: str = Field(description="Text that describes the topic")
    expertise: Optional[Literal["expert", "knowledge", "mentions"]] = Field(
        description="Level of expertise that the subject has on the topic", default=None
    )
    subject: str = Field(
        description="Represents the entity that has certain degree of knowledge on the topic. Might be an agent name."
    )
    metadata: Dict[str, bool | int | float | str] = Field(
        description="Topic fields that can be used to filter topics during topic retrieval.",
        default=dict(),
    )

    def __lt__(self, other: "TopicInfo"):
        # expertise level precedence
        # expert > knowledge > mentions
        if not isinstance(other, __class__):
            return NotImplemented
        if (
            self.topic == other.topic
            and self.subject == other.subject
            and (
                (
                    self.expertise == "mentions"
                    and other.expertise in ["knowledge", "expert"]
                )
                or (self.expertise == "knowledge" and other.expertise == "expert")
            )
        ):
            return True
        return False


class EmbeddedTopic(BaseModel):
    topic: TopicInfo
    embeddings: List[Any] | None = None


class RetrievedTopic(BaseModel):
    topic: TopicInfo
    distance: float


class TopicExtractionBuildOutput(ComponentOutput, Generic[T]):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    error: Optional[Exception] = None
    topics: List[TopicInfo] = Field(default_factory=list)
    topic_extractor_output: Optional[T] = None


class TopicExtractionInput(ComponentInput):
    documents: Iterable[str]


class TopicLoadingInput(ComponentInput):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    topics: List[EmbeddedTopic | TopicInfo]
    # embedding_function type: chromadb.api.types.EmbeddingFunction
    embedding_function: Optional[Any] = Field(
        deprecated="This field is deprecated, use a `TopicsSink` with the desired embedding function instead",
        default=None,
    )


@runtime_checkable  # see https://github.com/pydantic/pydantic/discussions/5767#discussioncomment-5919490
class TopicsSink(Protocol):
    def add_topics(self, topics: List[TopicInfo]): ...
    def add_embedded_topics(
        self,
        topics: List[EmbeddedTopic],
        # emb_fn type: chromadb.api.types.EmbeddingFunction
        emb_fn: Any | None = None,
    ): ...


@runtime_checkable  # see https://github.com/pydantic/pydantic/discussions/5767#discussioncomment-5919490
class ContentProvider(Protocol):
    def get_content(self) -> Iterator[str]: ...


class TopicRetrievalRunInput(ComponentInput):
    n_results: int = Field(
        description="Number of results to return from the topic retriever", default=10
    )
    query_kwargs: Dict[str, Any] = Field(
        description="Keyworded args passed directly to the underlying query function. If using ChromaDB as a TopicsSink the kwargs will be passed in the collection.query function.",
        default=dict(),
    )
    distance_threshold: Optional[float] = Field(
        description="Include only topics that are below a given distance threshold in the proximity search query result",
        default=None,
    )


class TopicRetrievalRunOutput(ComponentOutput):
    topics: Optional[List[RetrievedTopic]] = None


@runtime_checkable  # see https://github.com/pydantic/pydantic/discussions/5767#discussioncomment-5919490
class TopicRetriever(Protocol):
    def get_topics(
        self,
        query: str,
        n_results: int = 10,
        query_kwargs: Dict[str, Any] | None = None,
        distance_threshold: float | None = None,
    ) -> List[RetrievedTopic]: ...
