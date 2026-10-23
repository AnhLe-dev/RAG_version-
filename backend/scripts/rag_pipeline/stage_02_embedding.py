from app.core.config import get_settings
from app.rag.embedding.openai_embedder import (
    create_embedding_client,
    embed_document_chunks,
)
from scripts.rag_pipeline.common import (
    prepare_ucp600_corpus,
)


def main() -> None:
    """Run ingestion and generate embedding vectors."""

    settings = get_settings()

    print("Preparing UCP 600 corpus...")

    corpus = prepare_ucp600_corpus(
        settings
    )

    print(
        f"Embedding {len(corpus.chunks)} chunks..."
    )

    embedding_client = create_embedding_client(
        settings
    )

    vectors = embed_document_chunks(
        corpus.chunks,
        embedding_client,
        expected_dimensions=(
            settings.embedding_dimensions
        ),
    )

    print({
        "chunks": len(corpus.chunks),
        "vectors": len(vectors),
        "vector_dimensions": len(vectors[0]),
        "all_dimensions_valid": all(
            len(vector)
            == settings.embedding_dimensions
            for vector in vectors
        ),
        "first_vector_preview": vectors[0][:5],
    })


if __name__ == "__main__":
    main()

# PYTHONPATH=backend python3 -m scripts.rag_pipeline.stage_02_embedding