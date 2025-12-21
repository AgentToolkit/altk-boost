import builtins
from chromadb.api import ClientAPI
from chromadb.api.types import GetResult
import pytest


def test_metadata(chroma: ClientAPI):
    # Chroma DB metadata can contain only primitive data type fields: bool, int, float, str
    with pytest.raises(builtins.TypeError) as exc_info:
        _ = chroma.create_collection(
            "topic", metadata={"topic_custom_fields": ["f1", "f2"]}
        )
    assert (
        "argument 'metadata': failed to extract enum MetadataValue ('Bool | Int | Float | Str"
        in str(exc_info.value)
    )

    # As a workaround, list fields can be encoded using csv but this has limitations
    # This workaround can be used to store custom metadata fields associated with a topic document
    topic_coll = chroma.create_collection(
        "topic", metadata={"topic_custom_fields": "f1,f2"}
    )

    topic_coll.add(
        ids=["1", "2"],
        documents=["doc_1", "doc_2"],
        metadatas=[{"f1": "f1_v", "f2": 2}, {"f1": 1, "f2": 2}],
    )

    # the topic custom metadata fields can be obtained from the collection metadata during topic retrieval
    # to construct the filter expression
    custom_fields = topic_coll.metadata["topic_custom_fields"].split(",")
    filters = [1]
    where = {
        "$or": [{custom_field: {"$in": filters}} for custom_field in custom_fields]
    }
    result: GetResult = topic_coll.get(where=where)
    assert len(result["documents"]) == 1
    assert result["documents"][0] == "doc_2"
    assert result["metadatas"][0] == {"f1": 1, "f2": 2}

    filters = [2]
    where = {
        "$or": [{custom_field: {"$in": filters}} for custom_field in custom_fields]
    }
    result: GetResult = topic_coll.get(where=where)
    assert len(result["documents"]) == 2
    assert result["documents"][0] == "doc_1"
    assert result["documents"][1] == "doc_2"


def test_metadata_with_different_fields_per_document(chroma: ClientAPI):
    # As a workaround, list fields can be encoded using csv but this has limitations
    # This workaround can be used to store custom metadata fields associated with a topic document
    topic_coll = chroma.create_collection("topic", metadata={"flags_field": "f1,f2"})

    topic_coll.add(
        ids=["1", "2"],
        documents=["doc_1", "doc_2"],
        metadatas=[{"f1": "f1_v1"}, {"f1": "f1_v2", "f2": "f2_v1"}],
    )

    # the topic custom metadata fields can be obtained from the collection metadata during topic retrieval
    # to construct the filter expression
    custom_fields = topic_coll.metadata["flags_field"].split(",")
    filters = ["f1_v2", "other_value"]
    where = {
        "$or": [{custom_field: {"$in": filters}} for custom_field in custom_fields]
    }
    result: GetResult = topic_coll.get(where=where)
    assert len(result["documents"]) == 1
    assert result["documents"][0] == "doc_2"
    assert result["metadatas"][0] == {"f1": "f1_v2", "f2": "f2_v1"}

    filters = ["f1_v2", "other_value", "f1_v1"]
    where = {
        "$or": [{custom_field: {"$in": filters}} for custom_field in custom_fields]
    }
    result: GetResult = topic_coll.get(where=where)
    assert len(result["documents"]) == 2
    assert result["documents"][0] == "doc_1"
    assert result["metadatas"][0] == {"f1": "f1_v1"}
    assert result["documents"][1] == "doc_2"
    assert result["metadatas"][1] == {"f1": "f1_v2", "f2": "f2_v1"}
