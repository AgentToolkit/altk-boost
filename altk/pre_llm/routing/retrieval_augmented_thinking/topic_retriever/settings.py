from typing import Dict
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel


class Settings(BaseSettings):
    """Topic retriever settings

    All settings can be configured via environment variables with the prefix TOPIC_RETRIEVER_.
    For nested settings the __ separator is used to separate the inner setting object from the
    container setting object, e.g. TOPIC_RETRIEVER__config.instance.db_path=/path/to/chroma_db will set
    the Setting object property config.instance.db_path=/path/to/chroma_db
    """

    model_config = SettingsConfigDict(
        env_prefix="TOPIC_RETRIEVER_",
        env_file=".env",
        extra="ignore",
    )
    name: str
    config: Dict | BaseModel
