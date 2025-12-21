import argparse
import json
import logging
from pathlib import Path
import time
from typing import Dict, List, Optional

from altk.pre_llm.routing.retrieval_augmented_thinking.topic_extractor.settings import (
    MultipleTopicExtractionSettings,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.topic_extractor.topic_extraction import (
    create_topic_extractions,
    run_topic_extractions,
)


logger = logging.getLogger(__name__)


def get_arg_parser():
    parser = argparse.ArgumentParser(
        description="Run topic extraction agent lifecycle component"
    )

    parser.add_argument(
        "--topic_extractor",
        type=str,
        choices=["llm", "bertopic", "tfidf_words"],
        help="Topic extraction implementation to use",
        required=True,
    )

    parser.add_argument(
        "--topic_extraction_config",
        type=Path,
        help="Topic extraction config file",
        required=True,
    )

    parser.add_argument(
        "--log_level",
        type=str,
        help="Log level. Can be any of the built-in logging module levels",
        required=False,
    )
    return parser


def generate_llm_topic_extraction_settings(
    llm_topic_extraction: Dict,
) -> MultipleTopicExtractionSettings:
    content_provider = llm_topic_extraction.get("content_provider", {}).get("name")
    if (
        content_provider
        == "altk.routing_toolkit.retrieval_augmented_thinking.topic_extractor.chromadb.ChromaDBProvider"
    ):
        collections = llm_topic_extraction["content_provider"]["config"]["collections"]
        db_path = llm_topic_extraction["content_provider"]["config"]["instance"][
            "db_path"
        ]
        n_docs = llm_topic_extraction["content_provider"]["config"].get("n_docs")
        dest_db_path = llm_topic_extraction["topics_sink"]["config"]["instance"][
            "db_path"
        ]
        dest_collection = llm_topic_extraction["topics_sink"]["config"]["collection"]
        levels_of_expertise = llm_topic_extraction.get("levels_of_expertise", False)
        model_id = llm_topic_extraction.get("model_id", False)
        provider = llm_topic_extraction.get("provider", "watsonx")

        llm_topic_extraction_dict_settings = (
            generate_llm_topic_extraction_dict_settings(
                collections=collections,
                dest_collection=dest_collection,
                db_path=Path(db_path),
                model_id=model_id,
                provider=provider,
                n_docs=n_docs,
                dest_db_path=Path(dest_db_path),
                levels_of_expertise=levels_of_expertise,
            )
        )
        return MultipleTopicExtractionSettings(**llm_topic_extraction_dict_settings)

    else:
        raise ValueError(f"Unsupported content provider: {content_provider}")


def generate_llm_topic_extraction_dict_settings(
    collections: List[str],
    dest_collection: str,
    db_path: Path,
    model_id: str,
    provider: str = "watsonx",
    n_docs: Optional[int] = None,
    dest_db_path: Optional[Path] = None,
    levels_of_expertise: bool = False,
) -> Dict:
    return {
        "topic_extractors": [
            {
                "subject": col,
                "topic_extractor": {
                    "name": "llm",
                    "config": {
                        "content_provider": {
                            "name": "altk.routing_toolkit.retrieval_augmented_thinking.topic_extractor.chromadb.ChromaDBProvider",
                            "config": {
                                "collection": col,
                                "n_docs": n_docs,
                                "instance": {"db_path": str(db_path)},
                            },
                        },
                        "model_id": model_id,
                        "provider": provider,
                        "levels_of_expertise": levels_of_expertise,
                    },
                },
            }
            for col in collections
        ],
        "topics_sink": {
            "name": "altk.routing_toolkit.retrieval_augmented_thinking.topic_extractor.chromadb.ChromaDBProvider",
            "config": {
                "collection": dest_collection,
                "instance": {
                    "db_path": str(dest_db_path) if dest_db_path else str(db_path)
                },
            },
        },
    }


if __name__ == "__main__":
    args = get_arg_parser().parse_args()
    if args.log_level:
        logging.basicConfig(level=args.log_level)
        print(f"Log level set to {args.log_level}")
    else:
        logging.basicConfig()
        logging.getLogger(run_topic_extractions.__module__).setLevel(logging.INFO)
        logger.setLevel(logging.INFO)

    settings: MultipleTopicExtractionSettings = None
    if args.topic_extractor == "llm":
        settings = generate_llm_topic_extraction_settings(
            json.loads(args.topic_extraction_config.read_text())
        )
    if settings is None:
        raise ValueError(
            f"Unsupported topic extractor implementation: {args.topic_extractor}"
        )
    start = time.time()
    logger.info(f"Topic extraction settings:\n{settings.model_dump_json(indent=4)}")
    run_topic_extractions(create_topic_extractions(settings), settings)
    logger.info(f"Topic extraction took {time.time() - start:.2f} seconds")
