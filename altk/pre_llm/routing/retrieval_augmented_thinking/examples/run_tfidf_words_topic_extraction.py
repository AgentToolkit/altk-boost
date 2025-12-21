import json
import logging
from pathlib import Path
from chromadb import EphemeralClient
from chromadb.api.types import GetResult
from chromadb.config import Settings
from altk.core.toolkit import AgentPhase
from altk.pre_llm.core.types import TopicExtractionBuildOutput
from altk.pre_llm.core.types import (
    TopicExtractionInput,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.topic_extractor.settings import (
    TopicExtractionSettings,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.topic_extractor.topic_extractor import (
    TopicExtractionMiddleware,
)

# Run with:
# python altk/retrieval_augmented_thinking_toolkit/examples/run_tfidf_words_topic_extraction.py

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(filename)s - %(message)s", force=True
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

client = EphemeralClient(settings=Settings(allow_reset=True))

docs = json.loads((Path(__file__).parent / "chunks.json").read_text())

topic_extraction_settings = {
    "subject": "sound",
    "topic_extractor": {
        "name": "tfidf_words",
        "config": {
            "top_words": 30,
            "top_words_picked": 3,
        },
    },
    "topics_sink": {
        "name": "altk.pre_llm.routing.retrieval_augmented_thinking.chroma.topic_sink_content_provider.ChromaDBProvider",
        "config": {
            "collection": "sound.topics",
            "instance": {"client": client},
        },
    },
}


topic_extractor = TopicExtractionMiddleware.from_settings(
    TopicExtractionSettings(**topic_extraction_settings)
)

logger.info("Extracting topics from chunks")
topic_extraction_output: TopicExtractionBuildOutput = topic_extractor.process(
    data=TopicExtractionInput(documents=docs), phase=AgentPhase.BUILDTIME
)
if topic_extraction_output.error:
    logger.error(f"{topic_extraction_output.error=}")

# Get the extracted topics from the target chroma db collection
topics: GetResult = client.get_or_create_collection("sound.topics").get()
topics_str = [
    f"Topic: {doc}\nMetadata: {metadata}"
    for doc, metadata in zip(topics["documents"], topics["metadatas"])
]
topics_lst = "\n".join(topics_str)
logger.info(f"Extracted topics:\n{topics_lst}")
