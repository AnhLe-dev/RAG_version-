from math import isfinite

from langchain_openai import OpenAIEmbeddings

from app.core.config import Settings
from app.rag.embedding.text_builder import (
    build_embedding_texts,
)
from app.rag.models import DocumentChunk


def create_embedding_client(
    settings: Settings,
) -> OpenAIEmbeddings:
    """Create the configured OpenAI embedding client."""

    return OpenAIEmbeddings(
        model=settings.default_embedding_model,
        dimensions=settings.embedding_dimensions,
        api_key=(
            settings.openai_api_key.get_secret_value()
        ),
        max_retries=settings.max_retry_count,
        chunk_size=settings.embedding_batch_size,
    )


def embed_document_chunks(
    chunks: tuple[DocumentChunk, ...],
    embedding_client: OpenAIEmbeddings,
    *,
    expected_dimensions: int,
) -> tuple[tuple[float, ...], ...]:
    """Create and validate one embedding vector per chunk."""

    if not chunks:
        raise ValueError(
            "Cannot embed an empty chunk collection"
        )

    embedding_texts = build_embedding_texts(
        chunks
    )

    raw_vectors = embedding_client.embed_documents(
        list(embedding_texts)
    )

    if len(raw_vectors) != len(chunks):
        raise ValueError(
            "Embedding vector count does not match chunk count"
        )

    vectors = tuple(
        tuple(float(value) for value in vector)
        for vector in raw_vectors
    )

    for vector_index, vector in enumerate(vectors):
        if len(vector) != expected_dimensions:
            raise ValueError(
                "Embedding vector has an unexpected dimension: "
                f"index={vector_index}, "
                f"expected={expected_dimensions}, "
                f"actual={len(vector)}"
            )

        if not all(isfinite(value) for value in vector):
            raise ValueError(
                "Embedding vector contains a non-finite value: "
                f"index={vector_index}"
            )

    return vectors