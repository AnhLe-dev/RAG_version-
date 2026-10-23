from argparse import ArgumentParser

from app.core.config import get_settings
from app.knowledge import (
    create_ucp600_reference_service,
)


def parse_article_number() -> int:
    """Read the UCP 600 article number."""

    parser = ArgumentParser(
        description=(
            "Read one complete UCP 600 article"
        )
    )

    parser.add_argument(
        "article_number",
        type=int,
    )

    return parser.parse_args().article_number


def main() -> None:
    """Read and display one complete UCP 600 article."""

    article_number = parse_article_number()
    settings = get_settings()

    service = create_ucp600_reference_service(
        settings
    )

    article = service.get_article(
        source_id="ucp600",
        source_version="1",
        article_number=article_number,
        access_scope="public",
    )

    print("UCP 600 reference clause passed")
    print(f"source_id={article.source_id}")
    print(
        f"source_version="
        f"{article.source_version}"
    )
    print(
        f"source_checksum_sha256="
        f"{article.source_checksum_sha256}"
    )
    print(
        f"article_number="
        f"{article.article_number}"
    )
    print(f"title={article.title}")
    print(
        f"page_range="
        f"{article.page_start}-"
        f"{article.page_end}"
    )
    print(
        f"source_span_count="
        f"{len(article.source_spans)}"
    )

    print("raw_text:")
    print(article.raw_text)

    print("source_spans:")

    for span_index, span in enumerate(
        article.source_spans
    ):
        print(
            f"span={span_index} "
            f"page={span.page_number} "
            f"block={span.block_index} "
            f"bbox={span.bbox}"
        )


if __name__ == "__main__":
    main()