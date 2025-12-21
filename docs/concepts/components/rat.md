# Retrieval Augmented Thinking

A middleware solution to improve routing accuracy for manager agents that contain "difficult-to-describe" collaborator agents, such as those implement RAG. [Retrieval-Augmented Thinking](https://github.com/AgentToolkit/agent-lifecycle-toolkit/tree/main/altk/pre_llm/routing/retrieval_augmented_thinking) is made up of both a  **build-time** component (extracting topics of expertise) and a **run-time** component (Retrieval Agumented Thinking) to improve collaborator selection.


## Table of Contents

- [Overview](#overview)
- [How it Works](#how-it-works)
- [Sample Results](#sample-results)
- [Getting Started](#getting-started)
- [Topic Extraction](#topic-extraction)
- [Topic Loading](#topic-loading)
- [Topic Retrieval](#topic-retrieval)

## Overview

Retrieval-Augmented Thinking is a technique that uses _dynamic instruction_ at runtime to give hints to the agent regarding which collaborator(s) might be best to consult to answer a user query.  This approach has proven highly effective for improving collaborator invocations for agents that have broad areas of expertise, such as RAG-based agents.

## How it Works

Retrieval-Augmented Thinking operates in two steps

1. **Build time**
During agent build, content (documents, etc) for each route must be made available to a build time topic extraction processor, which extracts topics of expertise and stores them in a vector store for later retrieval.  Given that documents are often stored in vector stores for RAG implementations, we provide a sample implementation of processing content directly from a ChromaDB vector store.

2. **Runtime**
Simply select a RAT-enabled WxO Style for your agent to leverage Retrieval-Augmented thinking in production.  When a query comes in, the vector store that has been populated with "Topics of Expertise" is searched, and the most relevant collaborator expertise is summarized and dynamically injected into the thinking prompt.  This provides more information to the AI Agent to make good routing choices and produce the best possible plan.

**Architecture**

<img src="../../../assets/img_rat_architecture.png" />

## Sample Results

We evaluated Retrieve-And-Think using an AskHR dataset, where a ReACT-based manager agent routes to 7 collaborator agents, each of which is backed by RAG.   We then evaluate two key metrics:  (1) % of time the correct agent is called _first_, and (2) % of time the correct collaborator agent is called _ever_.   We compare with and without Retrieval-Augmented Thinking

### llama-3-3-70b
| Style | Correct Agent Called First | Correct Agent Called Ever|
|:--|:--:|:--:|
|React| 56% | 67% |
|React with RAT | 84% | 86%|

### granite-3-2-8b
| Style | Correct Agent Called First | Correct Agent Called Ever|
|:--|:--:|:--:|
|React| 49% | 54% |
|React with RAT | 79% | 84%|

## Getting Started
Go to our GitHub repo and get the code running by following the instructions in the [README](https://github.com/AgentToolkit/agent-lifecycle-toolkit/tree/main/altk/pre_llm/routing/retrieval_augmented_thinking/README.md).


## Topic Extraction

The `TopicExtractionMiddleware` is a build time component that extracts a list of topics from documents using a `TopicExtractor` and stores them in a `TopicSink`. A topic is represented by the `TopicInfo` object that has the following properties:

* `topic`: this is a string with the extracted topic from the document
* `expertise`: this is an optional field that has the level of expertise the document has on the topic. The different levels of expertise are, from high to low: `expert`, `knowledge`, and `mentions`.
* `subject`: this is a string representing the "entity" owning the documents and for which we want to know which topics it has knowledge on. It's tipically an agent name or an agent tool name.
* `metadata`: a dictionary with key value pairs that can be used to store metadata associated to the topic.

Topics can be extracted with the following topic extractors:

* [LLM](#llm-topic-extractor). Uses an LLM to extract the topics from the documents and optionally set the level of expertise that the document has on each topic.
* [TFIDF words](#tfidf-words-topic-extractor). Uses Term Frequency (TF) and Inverse Document Frequency (IDF) to identify the most relevant words in a document to extract the topics.
* [BERTopic](#bertopic-topic-extractor). Uses the [BERTopic](https://maartengr.github.io/BERTopic/index.html) library.

The extracted topics can be stored in Milvus and Chroma DB using the following topic sinks:

* [`altk.pre_llm.routing.retrieval_augmented_thinking.chroma.topic_sink_content_provider.ChromaDBProvider`](#chromadbprovider). Stores the topics in a ChromaDB instance
* [`altk.routing_toolkit.retrieval_augmented_thinking.chroma.topic_sink.MilvusProvider`](#milvusprovider). Stores the topics in a MilvusDB instance

### LLM Topic Extractor
The LLM Topic Extractor gets the documents from which to extract the topics from a `ContentProvider`. Currently there's only one [`ContentProvider` implementation](#chromadbprovider) that gets the documents from a ChromaDB instance.

The LLM Topic Extractor uses the [ALTK's LLM Library](https://github.com/AgentToolkit/agent-lifecycle-toolkit/tree/main/altk/core/llm) to call the LLM.

In the following example the LLM Topic Extractor gets documents from a ChromaDB, as specified in the Content Provider configuration under the `content_provider` field and stores the extracted topics in another Chroma DB instance specified in the Topic Sink configuration under the `topics_sink` field.

```python
import os
from altk.pre_llm.routing.retrieval_augmented_thinking.chroma.topic_sink_content_provider import ChromaDBProvider
from altk.pre_llm.routing.retrieval_augmented_thinking.core.toolkit import TopicExtractionBuildOutput
from altk.pre_llm.routing.retrieval_augmented_thinking.topic_extractor.llm import LLMTopicExtractor, LLMTopicExtractorOutput
from altk.pre_llm.routing.retrieval_augmented_thinking.topic_extractor.topic_extractor import TopicExtractionMiddleware
from altk.core.llm.base import get_llm
from altk.core.toolkit import AgentPhase


WatsonXAIClient = get_llm("watsonx")
llm_client = WatsonXAIClient(
    model_id="ibm/granite-3-3-8b-instruct",
    api_key=os.getenv("WX_API_KEY"),
    project_id=os.getenv("WX_PROJECT_ID"),
    url=os.getenv("WX_URL"),
)
topic_extractor = LLMTopicExtractor(
    content_provider=ChromaDBProvider(
        collection="sound",
        db_path="/path/to/chroma/db/with/source/documents",
        n_docs=5,
    ),
    llm_client=llm_client,
)
topic_extractor_extraction = TopicExtractionMiddleware(
    subject="sound",
    topic_extractor=topic_extractor,
    topics_sink=ChromaDBProvider(
        collection="sound.topics",
        db_path="/path/to/chroma/db/with/extracted/topics",
    ),
)

topic_extraction_output: TopicExtractionBuildOutput = topic_extractor_extraction.process(data=None, phase=AgentPhase.BUILDTIME)

print(f"{topic_extraction_output.error=}")
print(f"{topic_extraction_output.topics}")
```

### BERTopic Topic Extractor
As this type of topic extractor does not use an externally hosted model there's no need to create an LLM client as we did for the LLM Topic Extractor.
In the following example the extracted topics are stored in the collection `sound.topics` in a local ChromaDB instance whose configuration is specified in the Topic Sink configuration under the `topics_sink` key. There's no need to specify a Content Provider configuration since the BERTTopic extractor receives the documents directly as an input parameter.

```python
from altk.pre_llm.routing.retrieval_augmented_thinking.chroma.topic_sink_content_provider import (
    ChromaDBProvider,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.core.toolkit import (
    TopicExtractionInput,
    TopicExtractionBuildOutput,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.topic_extractor.bertopic import (
    BERTopicTopicExtractor,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.topic_extractor.topic_extractor import (
    TopicExtractionMiddleware,
)
from altk.core.toolkit import AgentPhase


topic_extractor = TopicExtractionMiddleware(
    subject="sound",
    topic_extractor=BERTopicTopicExtractor.from_settings(
        {
            "nr_topics": 1000,
            "count_vectorizer_settings": {
                "ngram_range": (3, 5),
                "stop_words": "english",
            },
        }
    ),
    topics_sink=ChromaDBProvider(
        collection="sound.topics",
        db_path="/path/to/chroma/db/with/extracted/topics",
    ),
)
topic_extraction_output: TopicExtractionBuildOutput = topic_extractor.process(
    data=TopicExtractionInput(documents=["doc_1", "doc_2", "doc_3", "..."]),
    phase=AgentPhase.BUILDTIME,
)

print(f"{topic_extraction_output.error=}")
print(f"{topic_extraction_output.topics}")
```

### TFIDF words Topic Extractor
In this example an `TFIDFWordsTopicExtractor` is used that is instantiated in a similar way than the `BERTopicTopicExtractor`.
```python
from altk.pre_llm.routing.retrieval_augmented_thinking.chroma.topic_sink_content_provider import (
    ChromaDBProvider,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.core.toolkit import (
    TopicExtractionInput,
    TopicExtractionBuildOutput,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.topic_extractor.tfidf_words import (
    TFIDFWordsTopicExtractor,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.topic_extractor.topic_extractor import (
    TopicExtractionMiddleware,
)
from altk.core.toolkit import AgentPhase


topic_extractor = TopicExtractionMiddleware(
    subject="sound",
    topic_extractor=TFIDFWordsTopicExtractor.from_settings(
        {
            "top_words": 50,
            "count_vectorizer_settings": {
                "ngram_range": (3, 5),
                "stop_words": "english",
            },
            "tfidf_vectorizer_settings": {
                "max_df": 0.85,
                "min_df": 2,
            },
        }
    ),
    topics_sink=ChromaDBProvider(
        collection="sound.topics",
        db_path="/path/to/chroma/db/with/extracted/topics",
    ),
)
topic_extraction_output: TopicExtractionBuildOutput = topic_extractor.process(
    data=TopicExtractionInput(documents=["doc_1", "doc_2", "doc_3", "..."]),
    phase=AgentPhase.BUILDTIME,
)

print(f"{topic_extraction_output.error=}")
print(f"{topic_extraction_output.topics}")
```

### Runnable Topic Extraction examples
You need to run the following scripts from the root of the ALTK repository.
```console
# LLM topic extraction example that gets documents and stores extracted topics in a Chroma DB
export WX_API_KEY=...
export WX_PROJECT_ID=...
export WX_URL=https://us-south.ml.cloud.ibm.com⁄
python altk/pre_llm/routing/retrieval_augmented_thinking/examples/run_llm_topic_extraction.py

# LLM topic extraction example that gets documents from a Chroma DB and stores extracted topics in a Milvus vector store
python altk/pre_llm/routing/retrieval_augmented_thinking/examples/run_llm_topic_extraction_milvus_sink.py

# BERTopic topic extraction example
python altk/pre_llm/routing/retrieval_augmented_thinking/examples/run_berttopic_topic_extraction.py

# TFIDF words topic extraction example
python altk/pre_llm/routing/retrieval_augmented_thinking/examples/run_tfidf_words_topic_extraction.py
```

### Topic Extraction cli
The component provides the cli `altk.pre_llm.routing.retrieval_augmented_thinking.topic_extractor.cli` that allows to:

* extract topics using an LLM topic extractor from a set of collections stored in a local Chroma DB
* store the extracted topics in a local Chroma DB

A json file with the topic extraction settings must be provided.

In the following example:
```
python -m altk.pre_llm.routing.retrieval_augmented_thinking.topic_extractor.cli --topic_extractor llm --topic_extraction_config topic_extraction.json
```
using these topic extraction settings form the `topic_extraction.json` file:
```json
{
    "model_id": "ibm/granite-3-3-8b-instruct",
    "provider": "watsonx",
    "levels_of_expertise": true,
    "content_provider": {
        "name": "altk.pre_llm.routing.retrieval_augmented_thinking.chroma.topic_sink_content_provider.ChromaDBProvider",
        "config": {
            "collections": [
                "tool_1",
                "tool_2",
                "tool_3"
            ],
            "instance": {
                "db_path": "/path/to/chroma"
            }
        }
    },
    "topics_sink": {
        "name": "altk.pre_llm.routing.retrieval_augmented_thinking.chroma.topic_sink_content_provider.ChromaDBProvider",
        "config": {
            "collection": "topics",
            "instance": {
                "db_path": "/path/to/chroma"
            }
        }
    }
}
```

The topic extractor component will extract topics from collections that have documents about the expertise of `tool_1`, `tool_2` and `tool_3`, that are stored in the local chroma db in `/path/to/chroma`. The topics will be extracted using the LLM `ibm/granite-3-3-8b-instruct` and the level of expertise will also be set for each topic. The extracted topics are stored in the `topics` collection in the local chroma db in `/path/to/chroma`.
The following env vars are required by the ALTK LLM Client Library to use the the watsonx LLM provider:
```
WX_API_KEY=
WX_PROJECT_ID=
WX_URL=https://us-south.ml.cloud.ibm.com
```

### Built-in Content Providers
#### `ChromaDBProvider`
A `ContentProvider` that gets the content chunks from a ChromaDB vector store. It requires the following parameters:

* `collection_name`. The name of the ChromaDB collection containing the documents returned in the iterator.
* `dest_collection_name`. You can use the same `ChromaDBProvider` instance as a `ContentProvider` and `TopicsSink`, in which case this parameter indicates the collection where the extracted topics will be saved.
* `db_path`. For a local ChromaDB instance, this is the directory containing the ChromaDB files.
* `host`, `port`. The host and port of a remote ChromaDB instance.
* `client`. An already instantiated ChromaDB client that is an instance of `ClientAPI` can be provided instead. This is mostly used for testing.
* `n_docs`. Number of documents that are processed. If not specified, all the documents are processed.


### Custom Content Provider implementation
To create a custom content provider follow these steps:
1. Define a Pydantic model that serves as a config object for the custom content provider implementation, e.g. `MyContentProviderSettings`. You can refer to the [ChromaDBProviderSettings](https://github.com/AgentToolkit/agent-lifecycle-toolkit/tree/main/altk/pre_llm/routing/retrieval_augmented_thinking/chroma/topic_sink_content_provider.py#L37) object as an example.
2. Create the class that implements the [`ContentProvider` protocol](https://github.com/AgentToolkit/agent-lifecycle-toolkit/tree/main/altk/pre_llm/routing/retrieval_augmented_thinking/core/toolkit.py#L99). The class must have a method `def get_content(self) -> Iterator[str]` that provides a stream of content chunks.
3. The class must also have a class method named `create_content_provider` that receives the config object and creates an instance of the topic sink
   ```python
    @classmethod
    def create_content_provider(cls, settings: MyContentProviderSettings | Dict) -> "MyContentProvider":
   ```
4. Register the implementation class using the `@TopicExtractionMiddleware.register_content_provider()` decorator:
   ```python
      @TopicExtractionMiddleware.register_content_provider()
      class MyContentProvider:
          ...
   ```

### Built-in Topics Sinks
#### `ChromaDBProvider`
A `ChromaDBProvider` object can also be used as a `TopicsSink`. If the same ChromaDB instance is used as the `ContentProvider` and the `TopicsSink` make sure that the ChromaDB collection used for the `TopicsSink` is different than the one used for the `ContentProvider`. If you're using the *same* ChromaDBProvider object then the collection used for the `TopicsSink` must be specified in the `dest_collection_name` parameter.

#### `MilvusProvider`
`TopicsSink` implementation to store the topics in a Milvus vector store. It supports the following settings:

* `milvus_uri`: Milvus instante URI
* `milvus_token`: Milvus token
* `milvus_db`: Milvus database
* `collection_name`: collection name where the topics will be stored
* `full_text_search_config`: if specified the topics will be stored so they can be queried using [Milvus full text search](https://milvus.io/docs/full-text-search.md). The following settings can be specified:
  - `topic_field_max_length`: length of the field that stores the "topic" text
  - `subject_field_max_length`: length of the field that stores the "subject" text
  - `sparse_index_params`: dictionary with the sparse index parameters. You can look at the [default config object](https://github.com/AgentToolkit/agent-lifecycle-toolkit/tree/main/altk/pre_llm/routing/retrieval_augmented_thinking/milvus/common.py#L19-L23) to see what settings can be set.
* `ann_search_config`: if specified the topics will be stored so they can be queried using the usual semantic search. The following settings can be specified:
  - `topic_field_max_length`: length of the field that stores the "topic" text
  - `subject_field_max_length`: length of the field that stores the "subject" text
  - `embedding_function_provider`: the [embedding function](https://milvus.io/docs/embeddings.md) implementation. It can be "default" that uses the default embedding function provided by Milvus (`dense.onnx.OnnxEmbeddingFunction`) or "sentence_transformer" that uses a Sentence Transformer model.
  - `embedding_function_config`: a dictionary with the embedding function parameters
  - `embedding_function`: instead of passing the embedding function implementation and config object you can pass an already instantiated embedding function in this parameter, like `model.dense.SentenceTransformerEmbeddingFunction()`.
  - `vector_dimensions`: Number of dimensions stored in the vector field. By default it uses the number of dimensions returned by the embedding function.
  - `metric_type`: metric used during search. By default it uses `COSINE`.


### Custom Topics Sink implementation
To create a custom topic sink follow these steps:
1. Define a Pydantic model that serves as a config object for the custom Topic Sink implementation. You can refer to the [`ChromaDBProviderSettings` object](https://github.com/AgentToolkit/agent-lifecycle-toolkit/tree/main/altk/pre_llm/routing/retrieval_augmented_thinking/chroma/topic_sink_content_provider.py#L36-L93) as an example.
2. Create the class that implements the [`TopicSink` protocol](https://github.com/AgentToolkit/agent-lifecycle-toolkit/tree/main/altk/pre_llm/routing/retrieval_augmented_thinking/core/toolkit.py#L87-L95). The class must implement the method `def add_topics(self, topics: List[TopicInfo])` that stores the `TopicInfo` objects in whatever storage mechanism your custom implementation has.
3. The class must have a class method named `create_topics_sink` that receives the config object and creates an instance of the topic sink
   ```python
    @classmethod
    def create_topics_sink(cls, settings: MyTopicsSinkConfig | Dict) -> "MyTopicsSink":
   ```
4. Register the implementation class using the `@TopicExtractionMiddleware.register_topics_sink()` decorator:
   ```python
      @TopicExtractionMiddleware.register_topics_sink()
      class MyTopicsSink:
          ...
   ```

### Creating a Topic Extraction component from settings
`settings.json`:
```json
{
    "subject": "sound",
    "topic_extractor": {
        "name": "llm",
        "config": {
            "model_id": "ibm/granite-3-3-8b-instruct",
            "provider": "watsonx",
            "content_provider": {
                "name": "altk.pre_llm.routing.retrieval_augmented_thinking.chroma.topic_sink_content_provider.ChromaDBProvider",
                "config": {
                    "collection": "sound",
                    "dest_collection": "sound.topics",
                    "instance": {
                        "db_path": "/path/to/chroma/with/source/documents"
                    }
                }
            }
        }
    },
    "topics_sink": {
        "name": "chromadb",
        "config": {
            "collection": "sound_topics",
            "instance": {
                "db_path": "/path/to/chroma/with/topics"
            },
            "embedding_function_provider": "sentence_transformer",
            "embedding_function_config": {
                "model_name": "all-MiniLM-L6-v2"
            }
        }
    }
}
```
```python
topic_extractor = TopicExtractionMiddleware.from_settings(json.loads(Path("settings.json").read_text()))
topic_extraction_output: TopicExtractionBuildOutput = topic_extractor.process(data=None, phase=AgentPhase.BUILDTIME)
```
The WatsonX API key, project id and URL, necessary to configure the LLM Client needed by the LLM Topic Extractor, are read from the env vars `WX_API_KEY`, `WX_PROJECT_ID` and `WX_URL` respectively.


## Topic Loading
If you alredy have generated topics and don't need to extract them using a Topic Extractor, they can be loaded directly into the vector store using the `TopicLoadingMiddleware` component.
We'll explain the topic loading using the following example:

```python
from sentence_transformers import SentenceTransformer
from altk.core.toolkit import AgentPhase
from altk.pre_llm.routing.retrieval_augmented_thinking.core.toolkit import EmbeddedTopic, TopicInfo, TopicLoadingInput
from altk.pre_llm.routing.retrieval_augmented_thinking.topic_loading.topic_loading import TopicLoadingMiddleware
from altk.pre_llm.routing.retrieval_augmented_thinking.topic_extractor.chromadb import ChromaDBProvider
from chromadb.utils import embedding_functions

embedding_model_name = "ibm-granite/granite-embedding-107m-multilingual"
embedding_model = SentenceTransformer(embedding_model_name)

topics = [
    EmbeddedTopic(
        topic=TopicInfo(
            topic="Job tasks",
            subject="job_offering",
            metadata={"env": "dark_lunch"},
        ),
        embeddings=embedding_model.encode("Job tasks").tolist(),
    ),
    EmbeddedTopic(
        topic=TopicInfo(
            topic="Job skills",
            subject="job_offering",
            metadata={"env": "testing"},
        ),
        embeddings=embedding_model.encode("Job skills").tolist(),
    ),
]

topic_loading = TopicLoadingMiddleware(
    topics_sink=ChromaDBProvider(collection="topics", db_path="/path/to/local/chromadb")
)
topic_loading.process(
    data=TopicLoadingInput(topics=topics),
    phase=AgentPhase.BUILDTIME
)
```

* The preembedded topics are provided using the `EmbeddedTopic` object that contains a topic (represented by the `TopicInfo` object) along with its embeddings
* The preembedded topics are loaded into a vector store using a persistent ChromaDB `TopicsSink` whose files reside in the folder `/path/to/local/chromadb`
* Topics can have an optional dictionary containing metadata fields that can be used to filter the topics [during topic retrieval](#topic-filtering).
* During topic loader, you can optionally configure an `embedding_function` for adding pre-embedded topics. Embedding functions can be imported from chromaDB, and will default to `all-MiniLM-L6-v2` if excluded.

Alternatively instead of calculating the embeddings beforehand, the embedding function can be specified in the `TopicsSink`:
```python
from altk.core.toolkit import AgentPhase
from altk.pre_llm.routing.retrieval_augmented_thinking.core.toolkit import EmbeddedTopic, TopicInfo, TopicLoadingInput
from altk.pre_llm.routing.retrieval_augmented_thinking.topic_loading.topic_loading import TopicLoadingMiddleware
from altk.pre_llm.routing.retrieval_augmented_thinking.topic_extractor.chromadb import ChromaDBProvider
from chromadb.utils import embedding_functions

topics = [
    TopicInfo(
        topic="Job tasks",
        subject="job_offering",
        metadata={"env": "dark_lunch"},
    ),
    TopicInfo(
        topic="Job skills",
        subject="job_offering",
        metadata={"env": "testing"},
    ),
]

topic_loading = TopicLoadingMiddleware(
    topics_sink=ChromaDBProvider(
        collection="topics",
        db_path=tmpdir,
        embedding_function=SentenceTransformerEmbeddingFunction(
            "ibm-granite/granite-embedding-107m-multilingual"
        ),
    )
)

topic_loading.process(
    data=TopicLoadingInput(topics=topics),
    phase=AgentPhase.BUILDTIME
)
```

### Creating a Topic Loading component from settings
A Topic Loading component is essentially a Topic Sink where to store the loaded topics.

`settings.json`:
```json
{
    "topics_sink": {
        "name": "chromadb",
        "config": {
            "collection": "sound_topics",
            "instance": {
                "db_path": "/path/to/chroma/with/topics"
            },
            "embedding_function_provider": "sentence_transformer",
            "embedding_function_config": {
                "model_name": "all-MiniLM-L6-v2"
            }
        }
    }
}
```
```python
topic_loading = TopicLoadingMiddleware.from_settings(Path("settings.json").read_text())
topics = [...]
topic_loading.process(data=TopicLoadingInput(topics=topics), phase=AgentPhase.BUILDTIME)
```

## Topic Retrieval
The topic retriever is a run time component that retrieves the topics from different vector stores using a `TopicRetriever` object. The retrieved topics can be used to create hints on which agent collaborator or tool to call for the given user query. The hints is usually a text fragment that is injected into the agent's prompt.

In the following example a `ChromaDBTopicRetriever` will do a semantic search on the topics stored in the `topics` collection for the query "What are my job responsibilities?".

```python
from altk.pre_llm.routing.retrieval_augmented_thinking.chroma.topic_retriever import (
    ChromaDBTopicRetriever,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.core.toolkit import (
    TopicRetrievalRunInput,
    TopicRetrievalRunOutput,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.topic_retriever.topic_retriever import (
    TopicRetrievalMiddleware,
)
from altk.core.toolkit import AgentPhase
from langchain_core.messages import HumanMessage


topic_retriever = TopicRetrievalMiddleware(
    topic_retriever=ChromaDBTopicRetriever(
        collection="topics", db_path="/path/to/local/chromadb"
    )
)
topic_retriever_ouput: TopicRetrievalRunOutput = topic_retriever.process(
    data=TopicRetrievalRunInput(
        messages=[{"role": "user", "content": "What are my job responsibilities?"}]
    ),
    phase=AgentPhase.RUNTIME,
)
print(f"{topic_retriever_ouput.topics}")
```

In the next example a `MilvusTopicRetriever` is used to retrieve topics from a Milvus vector store.
```python
from altk.pre_llm.routing.retrieval_augmented_thinking.core.toolkit import (
    TopicRetrievalRunInput,
    TopicRetrievalRunOutput,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.milvus.topic_retriever import (
    MilvusTopicRetriever,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.topic_retriever.topic_retriever import (
    TopicRetrievalMiddleware,
)
from altk.core.toolkit import AgentPhase
from langchain_core.messages import HumanMessage


topic_retriever = TopicRetrievalMiddleware(
    topic_retriever=MilvusTopicRetriever(
        collection_name="topics", milvus_uri="/path/to/local/milvus/files"
    )
)
topic_retriever_ouput: TopicRetrievalRunOutput = topic_retriever.process(
    data=TopicRetrievalRunInput(
        messages=[{"role": "user", "content": "What are my job responsibilities?"}]
    ),
    phase=AgentPhase.RUNTIME,
)
print(f"{topic_retriever_ouput.topics}")
```
By default the Milvus retriever will use [full text search](https://milvus.io/docs/full-text-search.md) to query the topics. If the topics were stored to be queried using semantic search instead, you need to provide the semantic search config in the `ann_search_config` parameter:
```python
from altk.pre_llm.routing.retrieval_augmented_thinking.core.toolkit import (
    TopicRetrievalRunInput,
    TopicRetrievalRunOutput,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.milvus.common import (
    AnnSearchConfig,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.milvus.topic_retriever import (
    MilvusTopicRetriever,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.topic_retriever.topic_retriever import (
    TopicRetrievalMiddleware,
)
from altk.core.toolkit import AgentPhase
from langchain_core.messages import HumanMessage
from pymilvus import model


topic_retriever = TopicRetrievalMiddleware(
    topic_retriever=MilvusTopicRetriever(
        collection_name="topics",
        milvus_uri="/path/to/local/milvus/files",
        ann_search_config=AnnSearchConfig(
            embedding_function=model.dense.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2", device="cpu"
            ),
        ),
    )
)
topic_retriever_ouput: TopicRetrievalRunOutput = topic_retriever.process(
    data=TopicRetrievalRunInput(
        messages=[{"role": "user", "content": "What are my job responsibilities?"}]
    ),
    phase=AgentPhase.RUNTIME,
)
print(f"{topic_retriever_ouput.topics}")
```

The following is a prompt fragment with tool hints using the retrieved topics that can be injected into the agent's prompt:
```python
hints = "\n".join(
    {
        retrieved_topic.topic.subject + ": " + retrieved_topic.topic.topic
        for retrieved_topic in topic_retriever_ouput.topics
    }
)
hints_prompt_fragment = f"Here are some hints to use when thinking about which tool might be best to help:\n{hints}"
```

### Topic Filtering
When using the Topic Retriever, topics can be filtered by their `subject` and `expertise` fields and also by their `metadata` fields. The filter expression is a dictionary with keyworded arguments that are passed directly to the underlying topic retriever implementation. For a ChromaDB Topic Retiever those kwargs are passed directly to the [ChromaDB `collection.query` method](https://docs.trychroma.com/docs/querying-collections/metadata-filtering). For a Milvus Topic Retriever the kwargs are passed to the [`client.search`](https://milvus.io/docs/single-vector-search.md#Single-Vector-Search) method.

In the following example ChromaDB is used first to load the topics and then to retrieve them. The topics have metadata fields representing an hypothetical software development environment where they can be used. During topic retrieval a ChromaDB metadata filtering expression is used to get the topics that can be used in any of the environments `["live", "dark_lunch"]`.
```python
from sentence_transformers import SentenceTransformer
from altk.pre_llm.routing.retrieval_augmented_thinking.chroma.topic_retriever import ChromaDBTopicRetriever
from altk.pre_llm.routing.retrieval_augmented_thinking.chroma.topic_sink_content_provider import ChromaDBProvider
from altk.core.toolkit import AgentPhase
from altk.pre_llm.routing.retrieval_augmented_thinking.core.toolkit import (
    EmbeddedTopic,
    TopicInfo,
    TopicLoadingInput,
    TopicRetrievalRunInput,
    TopicRetrievalRunOutput,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.topic_loading.topic_loading import TopicLoadingMiddleware
from altk.pre_llm.routing.retrieval_augmented_thinking.topic_retriever.topic_retriever import TopicRetrievalMiddleware
from chromadb import PersistentClient

embedding_model_name = "ibm-granite/granite-embedding-107m-multilingual"
embedding_model = SentenceTransformer(embedding_model_name)

topics = [
    EmbeddedTopic(
        topic=TopicInfo(
            topic="Job tasks",
            subject="job_offering",
            metadata={"env_1": "live", "env_2": "dark_lunch"},
        ),
        embeddings=embedding_model.encode("Job tasks").tolist(),
    ),
    EmbeddedTopic(
        topic=TopicInfo(
            topic="Job responsibilities",
            subject="job_offering",
            metadata={"env_1": "staging", "env_2": "testing"},
        ),
        embeddings=embedding_model.encode("Job responsibilities").tolist(),
    ),
]
topic_loading = TopicLoadingMiddleware(
    topics_sink=ChromaDBProvider(collection="topics", db_path="/path/to/local/chromadb")
)
topic_loading.process(
    data=TopicLoadingInput(topics=topics), phase=AgentPhase.BUILDTIME
)

topic_retriever = TopicRetrievalMiddleware(
    topic_retriever=ChromaDBTopicRetriever(
        collection="topics", chroma_client=PersistentClient(path="/path/to/local/chromadb")
    )
)

# Get topics having metadata fields `env_1` or `env_2` containing any of the values ["live", "dark_lunch"]
topic_retriever_ouput: TopicRetrievalRunOutput = topic_retriever.process(
    data=TopicRetrievalRunInput(
        messages=[{"role": "user", "content": "What are my job responsibilities?"}],
        query_kwargs={
            "where": {
                "$or": [
                    {"env_1": {"$in": ["live", "dark_lunch"]}},
                    {"env_2": {"$in": ["live", "dark_lunch"]}},
                ]
            }
        },
    ),
    phase=AgentPhase.RUNTIME,
)
print(topic_retriever_ouput.topics)
```

In the following example the topics are loaded and retrieved from a Milvus vector store. During retrieval Milvus first applies the filter condition and then does the full text search on the topics that match the condition:
```python
from altk.pre_llm.routing.retrieval_augmented_thinking.core.toolkit import (
    TopicInfo,
    TopicLoadingInput,
    TopicRetrievalRunInput,
    TopicRetrievalRunOutput,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.milvus.topic_retriever import (
    MilvusTopicRetriever,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.milvus.topic_sink import (
    MilvusProvider,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.topic_loading.topic_loading import (
    TopicLoadingMiddleware,
)
from altk.pre_llm.routing.retrieval_augmented_thinking.topic_retriever.topic_retriever import (
    TopicRetrievalMiddleware,
)
from altk.core.toolkit import AgentPhase
from langchain_core.messages import HumanMessage


topics = [
    TopicInfo(
        topic="Job 1",
        subject="HR Job Area",
        metadata={"env": "testing", "prop_1": 1},
    ),
    TopicInfo(
        topic="Job 2",
        subject="HR Job Area",
        metadata={"env": "prod", "prop_1": 2},
    ),
]
topic_loading = TopicLoadingMiddleware(
    topics_sink=MilvusProvider(
        collection_name="topics", milvus_uri="/path/to/local/milvus/files"
    )
)
topic_loading.process(data=TopicLoadingInput(topics=topics), phase=AgentPhase.BUILDTIME)


topic_retriever = TopicRetrievalMiddleware(
    topic_retriever=MilvusTopicRetriever(
        milvus_uri="/path/to/local/milvus/files", metadata_fields=["env", "prop_1"]
    )
)
topic_retriever_ouput: TopicRetrievalRunOutput = topic_retriever.process(
    data=TopicRetrievalRunInput(
        messages=[{"role": "user", "content": "Get job positions"}],
        query_kwargs={"filter": 'env == "prod"'},
    ),
    phase=AgentPhase.RUNTIME,
)
```

### Built-in Topics Retrievers
#### `ChromaDBTopicRetriever`
Retrieves topics from a ChromaDB instance.
To use a persistent ChromaDB that runs in the same process where your code runs:
```python
from altk.pre_llm.routing.retrieval_augmented_thinking.chroma.topic_retriever import (
    ChromaDBTopicRetriever,
)


topic_retriever = ChromaDBTopicRetriever(
    collection="topics", db_path="/path/to/local/chromadb"
)
```
To use a remote ChromaDB:
```python
from altk.pre_llm.routing.retrieval_augmented_thinking.chroma.topic_retriever import (
    ChromaDBTopicRetriever,
)


topic_retriever = ChromaDBTopicRetriever(
    collection="topics", host="localhost", port=8000
)
```
An EphemeralClient ChromaDB that is detroyed when the process ends can be used for quickly prototyping:
```python
from altk.pre_llm.routing.retrieval_augmented_thinking.chroma.topic_retriever import (
    ChromaDBTopicRetriever,
)
from chromadb import EphemeralClient


client = EphemeralClient()
topic_retriever = ChromaDBTopicRetriever(collection="topics", client=client)
```

#### `MilvusTopicRetriever`
Retrieves topics objects from a Milvus vector store.

To use a Milvus Lite instance:
```python
from altk.pre_llm.routing.retrieval_augmented_thinking.milvus.topic_retriever import (
    MilvusTopicRetriever,
)


topic_retriever = MilvusTopicRetriever(
    "/path/to/milvus/files", collection_name="topics"
)

```
To use a remote Milvus instance:
```python
from altk.pre_llm.routing.retrieval_augmented_thinking.milvus.topic_retriever import (
    MilvusTopicRetriever,
)


topic_retriever = MilvusTopicRetriever(
    "http://localhost:19530", collection_name="topics"
)
```

### Custom Topic Retriever implementation
To create a custom Topic Retriever follow these steps:

1. Define a Pydantic model that serves as a config object, you can refer to the [`MilvusTopicRetrieverConfig` object](https://github.com/AgentToolkit/agent-lifecycle-toolkit/tree/main/altk/pre_llm/routing/retrieval_augmented_thinking/milvus/topic_retriever.py#L24) as an example
2. The class must have a class method that receives the config object and creates an instance of the topic retriever
   ```python
   @classmethod
   def from_settings(cls, settings: MyTopicRetrieverConfig) -> TopicRetriever:
   ```
3. The class must implement the [`TopicRetriever` protocol](https://github.com/AgentToolkit/agent-lifecycle-toolkit/tree/main/altk/pre_llm/routing/retrieval_augmented_thinking/core/toolkit.py#L121) that requires a method `def get_topics(self, query: str, n_results: int = 10) -> List[TopicInfo]` that returns the topics for a user utterance
4. Register the implementation with a name, decorating the class like in the following example, where the implementation is registered under the name `my_topic_retriever`:
   ```python
      @topic_retriever.register("my_topic_retriever")
      class MyTopicRetriever:
          ...
   ```

### Creating a Topic Retrieval component from settings

`settings.json`:
```json
{
    "name": "chromadb",
    "config": {
        "collection": "sound_topics",
        "instance": {
            "db_path": "/path/to/chroma/with/topics"
        }
    }
}
```

```python

topic_retriever = TopicRetrievalMiddleware.from_settings(Path("settings.json").read_text())
topic_retriever_ouput: TopicRetrievalRunOutput = topic_retriever.process(
    data=TopicRetrievalRunInput(
        messages=[{"role": "user", "content": "Get job positions"}],
        query_kwargs={"filter": 'env == "prod"'},
    ),
    phase=AgentPhase.RUNTIME,
)
```
