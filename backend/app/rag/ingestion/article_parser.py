import re

from app.rag.models import (
    ExtractedPage,
    LegalArticle,
    LocatedTextBlock,
    PageTextBlock,
)


_ARTICLE_HEADING_PATTERN = re.compile(
    r"^Article\s+([1-9]|[12]\d|3[0-9])$",
    re.IGNORECASE,
)
_FIRST_PARAGRAPH_PATTERN = re.compile(
    r"(?m)^[ \t]*a\.[ \t]+"
)

def _locate_block(
    page_number: int,
    block: PageTextBlock,
) -> LocatedTextBlock:
    """Attach a source page number to an extracted block."""

    return LocatedTextBlock(
        page_number=page_number,
        block_index=block.block_index,
        text=block.text,
        bbox=block.bbox,
    )

def _replace_block_text(
    block: LocatedTextBlock,
    text: str,
) -> LocatedTextBlock:
    """Copy a located block while replacing only its text."""

    return LocatedTextBlock(
        page_number=block.page_number,
        block_index=block.block_index,
        text=text,
        bbox=block.bbox,
    )

def _build_article(
    article_number: int,
    heading: LocatedTextBlock,
    content_blocks: list[LocatedTextBlock],
) -> LegalArticle:
    """Build one article after validating its title and content."""

    if not content_blocks:
        raise ValueError(
            f"Article {article_number} does not contain any content"
        )

    title, body_blocks = _split_article_title(
        content_blocks
    )

    return LegalArticle(
        article_number=article_number,
        title=title,
        heading=heading,
        content_blocks=tuple(body_blocks),
    )
def parse_ucp600_articles(
    pages: tuple[ExtractedPage, ...],
) -> tuple[LegalArticle, ...]:
    """Parse an ordered UCP 600 document into Articles 1 through 39."""

    articles: list[LegalArticle] = []

    current_number: int | None = None
    current_heading: LocatedTextBlock | None = None
    current_content: list[LocatedTextBlock] = []

    for page in pages:
        for block in page.blocks:
            normalized_text = " ".join(block.text.split())
            heading_match = _ARTICLE_HEADING_PATTERN.fullmatch(
                normalized_text
            )

            located_block = _locate_block(
                page.page_number,
                block,
            )

            if heading_match:
                if (
                    current_number is not None
                    and current_heading is not None
                ):
                    articles.append(
                        _build_article(
                            current_number,
                            current_heading,
                            current_content,
                        )
                    )

                current_number = int(heading_match.group(1))
                current_heading = located_block
                current_content = []
                continue

            if current_heading is not None:
                current_content.append(located_block)

    if current_number is not None and current_heading is not None:
        articles.append(
            _build_article(
                current_number,
                current_heading,
                current_content,
            )
        )

    actual_numbers = [
        article.article_number
        for article in articles
    ]
    expected_numbers = list(range(1, 40))

    if actual_numbers != expected_numbers:
        raise ValueError(
            "UCP 600 article sequence is invalid: "
            f"expected {expected_numbers}, got {actual_numbers}"
        )

    return tuple(articles)

def _split_article_title(
    content_blocks: list[LocatedTextBlock],
) -> tuple[str, list[LocatedTextBlock]]:
    """Separate an article title from its body blocks."""

    if not content_blocks:
        raise ValueError(
            "Cannot extract an article title without content"
        )

    first_block = content_blocks[0]
    paragraph_match = _FIRST_PARAGRAPH_PATTERN.search(
        first_block.text
    )

    if paragraph_match:
        title = " ".join(
            first_block.text[
                :paragraph_match.start()
            ].split()
        )
        body_text = first_block.text[
            paragraph_match.start():
        ].strip()
    else:
        lines = first_block.text.splitlines()

        title = lines[0].strip() if lines else ""
        body_text = "\n".join(lines[1:]).strip()

    if not title:
        raise ValueError("Article title is empty")

    body_blocks = list(content_blocks[1:])

    if body_text:
        body_blocks.insert(
            0,
            _replace_block_text(
                first_block,
                body_text,
            ),
        )

    if not body_blocks:
        raise ValueError(
            f"Article '{title}' does not contain body text"
        )

    return title, body_blocks