from typing import Dict, Optional
from pydantic import BaseModel
from altk.pre_llm.core.types import TopicExtractionBuildOutput, TopicInfo
from altk.pre_llm.core.types import (
    TopicExtractionInput,
)

try:
    from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
except ImportError as err:
    raise ImportError(
        'You need to install the routing dependencies to use this component. Run `pip install "agent-lifecycle-toolkit[routing]"`'
    ) from err

import numpy as np


class TFIDFVectorizerSettings(BaseModel):
    max_df: Optional[float] = 0.95
    min_df: Optional[float] = 1
    max_features: Optional[int] = 5000
    stop_words: Optional[str] = "english"
    token_pattern: Optional[str] = r"(?u)\b\w[\w-]*\b"
    ngram_range: Optional[tuple] = (3, 3)

    norm: Optional[str] = "l2"
    use_idf: Optional[bool] = True
    smooth_idf: Optional[bool] = True
    sublinear_tf: Optional[bool] = True


class CountVectorizerSettings(BaseModel):
    max_df: Optional[float] = 0.95
    min_df: Optional[float] = 1
    max_features: Optional[int] = 5000
    stop_words: Optional[str] = "english"
    token_pattern: Optional[str] = r"(?u)\b\w[\w-]*\b"
    ngram_range: Optional[tuple] = (3, 3)


class TFIDFWordsTopicExtractorSettings(BaseModel):
    tfidf_vectorizer_settings: TFIDFVectorizerSettings = TFIDFVectorizerSettings()
    count_vectorizer_settings: CountVectorizerSettings = CountVectorizerSettings()

    top_words: Optional[int] = 30
    top_words_picked: Optional[int] = 20


class TFIDFWordsTopicExtractor(BaseModel):
    settings: TFIDFWordsTopicExtractorSettings = TFIDFWordsTopicExtractorSettings()

    @classmethod
    def from_settings(
        cls,
        settings: TFIDFWordsTopicExtractorSettings | Dict | None = None,
    ) -> "TFIDFWordsTopicExtractor":
        _settings = (
            TFIDFWordsTopicExtractorSettings(**settings)
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
        descriptions = []
        # TODO get to know in detail how this code works to avoid having a try catch block with a large scope
        try:
            documents = list(input.documents)

            # handle default parameters
            vectorizer_args = self.settings.count_vectorizer_settings.model_dump(
                exclude_none=True
            )
            tfidf_vectorizer = self.settings.tfidf_vectorizer_settings.model_dump(
                exclude_none=True
            )

            # Vectorize corpus
            tfidf_vectorizer = TfidfVectorizer(**tfidf_vectorizer)

            tfidf_vectorizer.fit(documents)

            # Exclude words that occur only once
            # Compute term frequencies for the single document
            count_vectorizer = CountVectorizer(**vectorizer_args)
            count_vectorizer.fit(documents)
            for doc in documents:
                print("DOC")
                print(doc)

                tfidf_matrix = tfidf_vectorizer.transform([doc])
                feature_names = tfidf_vectorizer.get_feature_names_out()
                scores = tfidf_matrix.toarray()[0]

                term_freqs = count_vectorizer.transform([doc]).toarray()[0]
                count_feature_names = count_vectorizer.get_feature_names_out()

                # Create a mapping from term to frequency
                freq_dict = dict(zip(count_feature_names, term_freqs))

                # Filter: Keep only words that appear more than once
                top_indices = np.argsort(scores)[::-1]
                top_words = []

                top_n = self.settings.top_words
                for i in top_indices:
                    word = feature_names[i]
                    if freq_dict.get(word, 0) > 0:
                        top_words.append((word, scores[i]))
                    if len(top_words) >= top_n:
                        break

                word_str = ""
                for word, _ in top_words[: self.settings.top_words_picked]:
                    new_word_str = f"{word_str}, {word}"
                    word_str = new_word_str
                    # print(f"  {term}: {score:.4f}")
                word_str = word_str.removeprefix(", ")
                print("TOPICS:", word_str)
                print()
                descriptions.append(word_str)
            return TopicExtractionBuildOutput(
                topics=[
                    TopicInfo(topic=description, subject=subject)
                    for description in descriptions
                ]
            )
        except Exception as e:
            return TopicExtractionBuildOutput(
                error=e,
                topics=[
                    TopicInfo(topic=description, subject=subject)
                    for description in descriptions
                ],
            )
