import json
from pathlib import Path
from typing import Any, Callable, List, Optional
from chromadb import EphemeralClient
from chromadb.api import ClientAPI
from chromadb.config import Settings

import pytest


@pytest.fixture
def chunks() -> List[str]:
    chunks_file = Path(__file__).parent / "topic_extractor/data/chunks.json"
    return json.loads(chunks_file.read_text())


@pytest.fixture
def create_chroma(request) -> Callable[..., ClientAPI]:
    client = EphemeralClient(settings=Settings(allow_reset=True))

    def _create_chroma(
        col_name: str, chunks: List[str], metadatas: Optional[List[Any]] = None
    ) -> ClientAPI:
        # populate the DBs
        collection = client.create_collection(col_name)
        collection.add(
            ids=[str(i) for i, _ in enumerate(chunks)],
            documents=chunks,
            metadatas=metadatas,
        )
        return client

    yield _create_chroma
    client.reset()


@pytest.fixture
def chroma() -> ClientAPI:
    client = EphemeralClient(settings=Settings(allow_reset=True))
    yield client
    client.reset()
