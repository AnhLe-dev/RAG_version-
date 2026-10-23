import re

from app.rag.models import (
    LegalArticle,
    LegalParagraph,
    LocatedTextBlock,
)


_PARAGRAPH_PATTERN = re.compile(
    r"^[ \t]*([a-z])\.[ \t]+",
    re.IGNORECASE,
)

def _replace_block_text(
    block: LocatedTextBlock,
    text: str,
) -> LocatedTextBlock:
    """Copy a source block while replacing its text."""

    return LocatedTextBlock(
        page_number=block.page_number,
        block_index=block.block_index,
        text=text,
        bbox=block.bbox,
    )
#tạo paragraph
def _build_paragraph(
    article_number: int,
    label: str | None,
    content_blocks: list[LocatedTextBlock],
) -> LegalParagraph:
    """Build a paragraph after validating its content."""

    if not content_blocks:
        display_label = label if label is not None else "unlabeled"

        raise ValueError(
            f"Article {article_number} paragraph "
            f"'{display_label}' does not contain content"
        )

    return LegalParagraph(
        article_number=article_number,
        label=label,
        content_blocks=tuple(content_blocks),
    )
# hàm xử lý Article không có nhãn 
def _has_top_level_paragraphs(
    article: LegalArticle,
) -> bool:
    """Return whether an article starts with paragraph a."""

    first_block = article.content_blocks[0]
    first_match = _PARAGRAPH_PATTERN.match(first_block.text)

    return (
        first_match is not None
        and first_match.group(1).casefold() == "a"
    )

def parse_article_paragraphs(
    article: LegalArticle,
) -> tuple[LegalParagraph, ...]:
    """Parse top-level lettered paragraphs from one article."""

    if not _has_top_level_paragraphs(article):
        return (
            _build_paragraph(
                article.article_number,
                None,
                list(article.content_blocks),
            ),
        )

    paragraphs: list[LegalParagraph] = []

    current_label: str | None = None
    current_blocks: list[LocatedTextBlock] = []
    expected_label = "a"

    for block in article.content_blocks:
        paragraph_match = _PARAGRAPH_PATTERN.match(
            block.text
        )

        detected_label = (
            paragraph_match.group(1).casefold()
            if paragraph_match is not None
            else None
        )

        if detected_label == expected_label:
            if current_label is not None:
                paragraphs.append(
                    _build_paragraph(
                        article.article_number,
                        current_label,
                        current_blocks,
                    )
                )

            body_text = block.text[
                paragraph_match.end():
            ].strip()

            current_label = detected_label
            current_blocks = []

            if body_text:
                current_blocks.append(
                    _replace_block_text(
                        block,
                        body_text,
                    )
                )

            expected_label = chr(
                ord(expected_label) + 1
            )
            continue

        current_blocks.append(block)

    if current_label is not None:
        paragraphs.append(
            _build_paragraph(
                article.article_number,
                current_label,
                current_blocks,
            )
        )

    return tuple(paragraphs)

def parse_ucp600_paragraphs(
    articles: tuple[LegalArticle, ...],
) -> tuple[LegalParagraph, ...]:
    """Parse paragraphs from all UCP 600 articles."""

    return tuple(
        paragraph
        for article in articles
        for paragraph in parse_article_paragraphs(article)
    )