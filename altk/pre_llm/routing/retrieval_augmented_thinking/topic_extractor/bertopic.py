from typing import Dict, List, Literal

from pydantic import BaseModel

try:
    from bertopic import BERTopic
    from sklearn.feature_extraction.text import CountVectorizer
    from sentence_transformers import SentenceTransformer
    from hdbscan import HDBSCAN
except ImportError as err:
    raise ImportError(
        'You need to install the routing dependencies to use this component. Run `pip install "agent-lifecycle-toolkit[routing]"`'
    ) from err

from altk.pre_llm.core.types import TopicExtractionBuildOutput, TopicInfo
from altk.pre_llm.core.types import (
    TopicExtractionInput,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.topic_extractor.tfidf_words import (
    CountVectorizerSettings,
)


class HDBSCANSettings(BaseModel):
    min_cluster_size: int = 2
    min_samples: int = 1
    metric: str = "euclidean"
    prediction_data: bool = True


class BERTopicExtractorSettings(BaseModel):
    count_vectorizer_settings: CountVectorizerSettings = CountVectorizerSettings(
        ngram_range=(3, 5), stop_words="english"
    )
    hdbscan_settings: HDBSCANSettings = HDBSCANSettings()
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_model_type: Literal["sentence_transformer"] = "sentence_transformer"
    nr_topics: int = 100000
    calculate_probabilities: bool = True


class BERTopicTopicExtractor(BaseModel):
    settings: BERTopicExtractorSettings = BERTopicExtractorSettings()

    @classmethod
    def from_settings(
        cls,
        settings: BERTopicExtractorSettings | Dict | None = None,
    ) -> "BERTopicTopicExtractor":
        _settings = (
            BERTopicExtractorSettings(**settings)
            if isinstance(settings, Dict)
            else settings
        )
        return cls(settings=_settings) if _settings else cls()

    def extract_topics(
        self, subject, input: TopicExtractionInput
    ) -> TopicExtractionBuildOutput:
        print(
            f"Running {self.__class__.__name__} with these settings: \n{self.settings.model_dump_json(indent=4)}"
        )
        result: List[TopicInfo] = []
        # TODO get to know in detail how this code works to avoid having a try catch block with a large scope
        try:
            docs = list(input.documents)
            print("# Create a CountVectorizer with n-grams (1,k)")
            vectorizer_model = CountVectorizer(
                **self.settings.count_vectorizer_settings.model_dump(exclude_none=True)
            )

            print("# Create Sentence Transformers")
            if self.settings.embedding_model_type == "sentence_transformer":
                embedding_model = SentenceTransformer(self.settings.embedding_model)
            else:
                raise ValueError(
                    f"Unsupported embedding model type {self.settings.embedding_model_type}"
                )

            hdbscan_model = HDBSCAN(
                **self.settings.hdbscan_settings.model_dump(exclude_none=True)
            )

            print("# Init Bert")
            topic_model = BERTopic(
                vectorizer_model=vectorizer_model,
                embedding_model=embedding_model,
                hdbscan_model=hdbscan_model,
                nr_topics=self.settings.nr_topics,
                calculate_probabilities=self.settings.calculate_probabilities,
            )

            print("# fit()")
            topics, probs = topic_model.fit_transform(docs)

            print("# Dumping topics\n")
            for topic_id in sorted(set(topics)):
                if topic_id == -1:
                    continue  # Skip outlier topic

                # Get topic keywords
                topic_words = topic_model.get_topic(topic_id)
                if not topic_words:
                    continue

                print(f"🟦 Topic {topic_id}:")
                for word, score in topic_words:
                    print(f"   {word:<15} {score:.3f}")
                print()  # Empty line between topics
                result.append(
                    TopicInfo(
                        subject=subject,
                        topic=" ".join([word for word, _ in topic_words]),
                    )
                )

            print("# DONE")
            return TopicExtractionBuildOutput(topics=result)
        except Exception as e:
            return TopicExtractionBuildOutput(error=e)
