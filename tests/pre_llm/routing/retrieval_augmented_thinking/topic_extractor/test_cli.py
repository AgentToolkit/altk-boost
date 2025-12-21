import json
from pathlib import Path
from altk.pre_llm.routing.retrieval_augmented_thinking.topic_extractor.cli import (
    MultipleTopicExtractionSettings,
    generate_llm_topic_extraction_settings,
)


def test_generate_llm_topic_extraction():
    dict_settings = json.loads(
        (Path(__file__).parent / "data/askhr_topic_extraction_llm.json").read_text()
    )
    collections = dict_settings["content_provider"]["config"]["collections"]
    settings: MultipleTopicExtractionSettings = generate_llm_topic_extraction_settings(
        dict_settings
    )
    # there's a topic extractor for each collection
    assert len(settings.topic_extractors) == len(collections)
