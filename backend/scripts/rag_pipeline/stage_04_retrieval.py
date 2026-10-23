from app.rag.retrieval.dense_retriever import (
    search_dense,
)
from argparse import ArgumentParser

from app.core.config import get_settings
from app.rag.embedding.openai_embedder import (
    create_embedding_client,
)
from app.rag.vector_store.qdrant_store import (
    create_qdrant_client,
)
from app.rag.generation.context_builder import (
    build_context,
)

def parse_arguments():
    """Read the question from the command line."""

    parser = ArgumentParser(
        description="Search UCP 600 with dense retrieval"
    )

    parser.add_argument(
        "question",
        help="Question to search for",
    )

    return parser.parse_args()


def main() -> None:
    """Embed a question and retrieve relevant chunks."""

    arguments = parse_arguments()
    question = arguments.question.strip()

    if not question:
        raise ValueError(
            "Question must not be empty"
        )

    settings = get_settings()

    embedding_client = create_embedding_client(
        settings
    )

    print("Embedding question...")

    query_vector = embedding_client.embed_query(
        question
    )

    qdrant_client = create_qdrant_client(
        settings
    )

    try:
        print("Searching Qdrant...")

        results = search_dense(
            qdrant_client,
            collection_name=(
                settings.qdrant_collection_name
            ),
            query_vector=query_vector,
            access_scope="public",
            source_id="ucp600",
            source_version="1",
            limit=settings.final_top_n,
            expected_dimensions=(
                settings.embedding_dimensions
            ),
        )
    finally:
        qdrant_client.close()
    context = build_context(results)

    print()
    print("=" * 60)
    print("LLM CONTEXT")
    print("=" * 60)
    print(context)
    print({
        "question": question,
        "result_count": len(results),
    })

    for rank, result in enumerate(
        results,
        start=1,
    ):
        print()
        print(f"Result {rank}")
        print(f"Score: {result.score:.4f}")
        print(
            "Structure:",
            " > ".join(result.structure_path),
        )
        print(
            f"Pages: {result.page_start}"
            f"-{result.page_end}"
        )
        print(f"Text: {result.text[:500]}")
    

if __name__ == "__main__":
    main()

# PYTHONPATH=backend python3 -m scripts.rag_pipeline.stage_04_retrieval \
# "What do banks deal with under UCP 600?"