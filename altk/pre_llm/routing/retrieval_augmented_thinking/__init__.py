import logging


logger = logging.getLogger(__name__)
# import built-in TopicRetriever implementations to force their registering
try:
    from .chroma.topic_retriever import ChromaDBTopicRetriever
    from .chroma.topic_sink_content_provider import ChromaDBProvider
except ModuleNotFoundError:
    logger.warning(
        "Chroma DB required packages not installed, ChromaDBTopicRetriever and ChromaDBProvider can't be used."
    )
try:
    from .milvus.topic_retriever import MilvusTopicRetriever
    from .milvus.topic_sink import MilvusProvider
except ModuleNotFoundError:
    logger.warning(
        "Milvus required packages not installed, MilvusTopicRetriever and MilvusProvider can't be used."
    )
