from app.core.config import get_settings
from scripts.rag_pipeline.common import (
    prepare_ucp600_corpus,
)


def main() -> None:
    """Run and report the ingestion stage."""

    settings = get_settings()

    corpus = prepare_ucp600_corpus(
        settings
    )

    print({
        "source": corpus.source.source_id,
        "articles": len(corpus.articles),
        "paragraphs": len(corpus.paragraphs),
        "items": len(corpus.items),
        "chunks": len(corpus.chunks),
        "unique_chunk_ids": (
            len({
                chunk.chunk_id
                for chunk in corpus.chunks
            })
            == len(corpus.chunks)
        ),
    })


if __name__ == "__main__":
    main()

# PYTHONPATH=backend python3 -m scripts.rag_pipeline.stage_01_ingestion