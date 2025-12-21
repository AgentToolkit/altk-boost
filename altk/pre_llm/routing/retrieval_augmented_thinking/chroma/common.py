from chromadb.api import ClientAPI
from chromadb.config import DEFAULT_DATABASE
from pydantic import BaseModel, ConfigDict


class EphemeralChromaDBConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    client: ClientAPI


class LocalChromaDBConfig(BaseModel):
    db_path: str


class RemoteChromaDBConfig(BaseModel):
    host: str
    port: int
    ssl: bool = False
    ssl_verify: bool | None = None


class ChromaDBConfig(BaseModel):
    collection: str
    database: str = DEFAULT_DATABASE
    instance: LocalChromaDBConfig | RemoteChromaDBConfig | EphemeralChromaDBConfig
