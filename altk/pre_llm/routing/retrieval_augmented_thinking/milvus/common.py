from typing import Any, Dict, Literal
from pydantic import BaseModel, Field

try:
    from pymilvus import model
    from pymilvus.model.base import BaseEmbeddingFunction
except ImportError as err:
    raise ImportError(
        'You need to install the routing dependencies to use this component. Run `pip install "agent-lifecycle-toolkit[routing]"`'
    ) from err


class MilvusConfig(BaseModel):
    collection: str = "topics"
    database: str | None = None
    uri: str


class SearchConfig(BaseModel):
    topic_field_max_length: int = 10000
    subject_field_max_length: int = 1000


class FullTextSearchConfig(SearchConfig):
    sparse_index_params: dict = {
        "inverted_index_algo": "DAAT_MAXSCORE",
        "bm25_k1": 1.2,
        "bm25_b": 0.75,
    }


class AnnSearchConfig(SearchConfig):
    model_config = {"arbitrary_types_allowed": True}

    embedding_function_provider: Literal["default", "sentence_transformer"] = Field(
        description="Embedding function provider", default="default"
    )
    embedding_function_config: Dict[str, Any] | None = Field(
        description="Embedding function parameters",
        default=None,
    )
    embedding_function: BaseEmbeddingFunction | None = Field(
        description="Embbeding function already instantiated", default=None
    )
    vector_dimensions: int | None = Field(description="Vector dimensions", default=None)
    metric_type: str = "COSINE"

    def get_embedding_function(self) -> BaseEmbeddingFunction:
        if self.embedding_function:
            return self.embedding_function
        if self.embedding_function_provider == "default":
            return model.DefaultEmbeddingFunction()
        elif self.embedding_function_provider == "sentence_transformer":
            return model.dense.SentenceTransformerEmbeddingFunction(
                **(self.embedding_function_config or {})
            )
        else:
            raise ValueError(
                f"Unsupported embedding function provider: {self.embedding_function_provider}"
            )
