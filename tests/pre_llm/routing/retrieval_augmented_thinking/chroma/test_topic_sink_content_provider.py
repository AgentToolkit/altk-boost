from typing import Callable, List


from chromadb.api import ClientAPI
from altk.pre_llm.routing.retrieval_augmented_thinking.chroma.topic_sink_content_provider import (
    ChromaDBProvider,
    ChromaDBProviderSettings,
)


import logging

from altk.pre_llm.routing.retrieval_augmented_thinking.chroma.common import (
    LocalChromaDBConfig,
)


def test_chromadb_content_provider(
    caplog, chunks: List[str], create_chroma: Callable[..., ClientAPI]
):
    caplog.set_level(logging.DEBUG, logger=ChromaDBProvider.__module__)

    # populate the DB
    client = create_chroma("sound", chunks[:10])

    chromadb = ChromaDBProvider("sound", client=client)
    up_to = 5
    retrieved = 0
    for chunk in chromadb.get_content():
        if retrieved >= up_to:
            break
        retrieved += 1
        print(f"Chunk #{retrieved}:\n{chunk}")
    assert retrieved == up_to

    chromadb = ChromaDBProvider("sound", client=client, n_docs=up_to)
    retrieved = 0
    for chunk in chromadb.get_content():
        retrieved += 1
        print(f"Chunk #{retrieved}:\n{chunk}")
    assert retrieved == up_to


def test_embedding_function():
    settings = ChromaDBProviderSettings(
        collection="topics",
        instance=LocalChromaDBConfig(db_path="/tmp/chroma"),
        embedding_function_provider="sentence_transformer",
        embedding_function_config={
            "model_name": "ibm-granite/granite-embedding-107m-multilingual",
            "device": "cpu",
            "normalize_embeddings": False,
        },
    )
    embedding_function = settings.get_embedding_function()
    assert embedding_function.get_config() == {
        "model_name": "ibm-granite/granite-embedding-107m-multilingual",
        "device": "cpu",
        "normalize_embeddings": False,
        "kwargs": {},
    }
    assert embedding_function.name() == "sentence_transformer"
