from argparse import ArgumentParser

from app.core.config import get_settings
from app.rag.embedding.openai_embedder import (
    create_embedding_client,
)
from app.rag.generation.answer_generator import (
    create_answer_model,
    generate_answer,
)
from app.rag.generation.context_builder import (
    build_context,
)
from app.rag.generation.prompt_builder import (
    build_rag_prompt,
)
from app.rag.retrieval.dense_retriever import (
    search_dense,
)
from app.rag.vector_store.qdrant_store import (
    create_qdrant_client,
)
from app.rag.generation.citation_validator import (
    validate_answer_citations,
)

def parse_arguments():
    """Read one question from the command line."""

    parser = ArgumentParser(
        description="Answer a UCP 600 question with RAG"
    )

    parser.add_argument(
        "question",
        help="Question to answer",
    )

    return parser.parse_args()


def main() -> None:
    """Run the complete RAG Version 1 question pipeline."""

    arguments = parse_arguments()
    question = arguments.question.strip()

    if not question:
        raise ValueError(
            "Question must not be empty"
        )

    settings = get_settings()

    print("1. Embedding question...")

    embedding_client = create_embedding_client(
        settings
    )

    query_vector = embedding_client.embed_query(
        question
    )

    print("2. Retrieving relevant chunks...")

    qdrant_client = create_qdrant_client(
        settings
    )

    try:
        results = search_dense(
            qdrant_client,
            collection_name=(
                settings.qdrant_collection_name
            ),
            query_vector=query_vector,
            access_scope="public",
            limit=settings.final_top_n,
            expected_dimensions=(
                settings.embedding_dimensions
            ),
        )
    finally:
        qdrant_client.close()

    print("3. Building context...")

    context = build_context(results)

    print("4. Building prompt...")

    prompt = build_rag_prompt(
        question=question,
        context=context,
    )

    print("5. Generating answer...")

    answer_model = create_answer_model(
        settings
    )

    answer = generate_answer(
        prompt=prompt,
        model=answer_model,
    )

    print("6. Validating citations...")

    used_citations = validate_answer_citations( 
        answer=answer,
        context=context,
)

    print()
    print("=" * 60)
    print("ANSWER")
    print("=" * 60)
    print(answer)

    print()
    print("=" * 60)
    print("RETRIEVED SOURCES")
    print("=" * 60)
    print()
    print(f"Validated citations: {used_citations}")

    for source_number, result in enumerate(
        results,
        start=1,
    ):
        print(
            f"[S{source_number}] "
            f"{' > '.join(result.structure_path)}, "
            f"pages {result.page_start}-{result.page_end}, "
            f"score={result.score:.4f}"
        )


if __name__ == "__main__":
    main()

# PYTHONPATH=backend python3 -m scripts.rag_pipeline.stage_05_generation \
# "Do banks deal with documents or with goods, services and performance?"

# PYTHONPATH=backend python3 -m scripts.rag_pipeline.stage_05_generation \
# "Khi nào ngân hàng được phép từ chối thanh toán bộ chứng từ theo UCP 600, và ngân hàng phải thông báo việc từ chối trong thời hạn bao lâu? Hãy trích dẫn điều khoản liên quan."