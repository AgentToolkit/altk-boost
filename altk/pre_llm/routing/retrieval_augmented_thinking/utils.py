from docling.document_converter import DocumentConverter
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)


def generate_chunks_from_file(doc_src: str, chunk_size=100000, chunk_overlap=500):
    markdown_doc = (
        DocumentConverter().convert(source=doc_src).document.export_to_markdown()
    )

    # Split the markdown into large blocks, one block per H1, H2, and H3 headers
    markdown_splitter = MarkdownHeaderTextSplitter(
        [("#", "Header 1"), ("##", "Header 2"), ("###", "Header 3")]
    )
    md_header_splits = markdown_splitter.split_text(str(markdown_doc))

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    return [doc.page_content for doc in text_splitter.split_documents(md_header_splits)]
