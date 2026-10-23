from app.core.config import get_settings
from app.rag.embedding.openai_embedder import (
    create_embedding_client,
    embed_document_chunks,
)
from app.rag.vector_store.qdrant_store import (
    create_qdrant_client,
    ensure_collection,
    upsert_chunks,
)
from scripts.rag_pipeline.common import (
    prepare_ucp600_corpus,
)


def main() -> None:
    """Embed UCP 600 and index it into Qdrant."""

    settings = get_settings()

    print("Preparing corpus...")
    corpus = prepare_ucp600_corpus(settings)

    print(f"Embedding {len(corpus.chunks)} chunks...")
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

    print("Connecting to Qdrant...")
    qdrant_client = create_qdrant_client(
        settings
    )

    try:
        ensure_collection(
            qdrant_client,
            collection_name=(
                settings.qdrant_collection_name
            ),
            vector_size=(
                settings.embedding_dimensions
            ),
        )

        uploaded_count = upsert_chunks(
            qdrant_client,
            collection_name=(
                settings.qdrant_collection_name
            ),
            chunks=corpus.chunks,
            vectors=vectors,
            batch_size=64,
        )

        stored_count = qdrant_client.count(
            collection_name=(
                settings.qdrant_collection_name
            ),
            exact=True,
        ).count

        print({
            "collection": (
                settings.qdrant_collection_name
            ),
            "uploaded": uploaded_count,
            "stored": stored_count,
            "expected": len(corpus.chunks),
            "complete": (
                stored_count == len(corpus.chunks)
            ),
        })
    finally:
        qdrant_client.close()


if __name__ == "__main__":
    main()
# PYTHONPATH=backend python3 -m scripts.rag_pipeline.stage_03_qdrant_index