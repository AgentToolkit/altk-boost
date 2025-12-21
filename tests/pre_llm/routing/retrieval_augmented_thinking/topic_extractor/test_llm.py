from altk.pre_llm.core.types import (
    TopicInfo,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.topic_extractor.llm import (
    LLMTopicExtractorOutput,
)


def test_topic_extraction_result():
    topic_extractor_output = LLMTopicExtractorOutput()
    assert topic_extractor_output.chunks_processed == 0
    assert len(topic_extractor_output.chunk_stats) == 0
    topic_extractor_output.chunk_stats[
        topic_extractor_output.chunks_processed
    ].topics = []
    assert len(topic_extractor_output.chunk_stats) == 1
    assert (
        topic_extractor_output.chunk_stats[
            topic_extractor_output.chunks_processed
        ].topics
        == []
    )
    topic_extractor_output.chunks_processed += 1

    assert topic_extractor_output.chunks_processed == 1
    assert len(topic_extractor_output.chunk_stats) == 1
    topic_extractor_output.chunk_stats[
        topic_extractor_output.chunks_processed
    ].extraction_time = 1.5
    topic_extractor_output.chunk_stats[
        topic_extractor_output.chunks_processed
    ].topics = [
        TopicInfo(topic="t_1", expertise="expert", subject="c_1"),
        TopicInfo(topic="t_2", expertise="knowledge", subject="c_1"),
    ]
    topic_extractor_output.chunks_processed += 1

    assert len(topic_extractor_output.chunk_stats) == 2
