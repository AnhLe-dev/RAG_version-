from app.rag.models import DocumentChunk


def build_embedding_text(
    chunk: DocumentChunk,
) -> str:
    """Build context-rich text used for embedding."""

    structure_context = " > ".join(
        chunk.structure_path
    )

    return (
        f"{structure_context}\n"
        f"{chunk.text}"
    ).strip()


def build_embedding_texts(
    chunks: tuple[DocumentChunk, ...],
) -> tuple[str, ...]:
    """Build embedding input text for all chunks."""

    texts = tuple(
        build_embedding_text(chunk)
        for chunk in chunks
    )

    if len(texts) != len(chunks):
        raise ValueError(
            "Embedding text count does not match chunk count"
        )

    if any(not text.strip() for text in texts):
        raise ValueError(
            "Embedding text must not be empty"
        )

    return texts