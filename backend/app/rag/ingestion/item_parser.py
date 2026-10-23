import re

from app.rag.models import (
    LegalItem,
    LegalParagraph,
    LocatedTextBlock,
)


_ROMAN_LABELS = (
    "i",
    "ii",
    "iii",
    "iv",
    "v",
    "vi",
    "vii",
    "viii",
    "ix",
    "x",
)

_ROMAN_ITEM_PATTERN = re.compile(
    r"^[ \t]*([ivx]+)\.(?=[ \t]+|[a-z]\))",
    re.IGNORECASE,
)
#helper giữ metadata nguồn
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

#helper tạo item
def _build_item(
    paragraph: LegalParagraph,
    label: str | None,
    content_blocks: list[LocatedTextBlock],
) -> LegalItem:
    """Build an item after validating its content."""

    if not content_blocks:
        display_label = label if label is not None else "unlabeled"

        raise ValueError(
            f"Article {paragraph.article_number}, "
            f"paragraph {paragraph.label}, "
            f"item '{display_label}' does not contain content"
        )

    return LegalItem(
        article_number=paragraph.article_number,
        paragraph_label=paragraph.label,
        label=label,
        content_blocks=tuple(content_blocks),
    )

#Parse item trong một paragraph
def parse_paragraph_items(
    paragraph: LegalParagraph,
) -> tuple[LegalItem, ...]:
    """Parse sequential Roman items from one paragraph."""

    items: list[LegalItem] = []

    current_label: str | None = None
    current_blocks: list[LocatedTextBlock] = []

    expected_index = 0
    found_roman_item = False

    for block in paragraph.content_blocks:
        item_match = _ROMAN_ITEM_PATTERN.match(
            block.text
        )

        detected_label = (
            item_match.group(1).casefold()
            if item_match is not None
            else None
        )

        expected_label = (
            _ROMAN_LABELS[expected_index]
            if expected_index < len(_ROMAN_LABELS)
            else None
        )

        if detected_label == expected_label:
            if current_blocks:
                items.append(
                    _build_item(
                        paragraph,
                        current_label,
                        current_blocks,
                    )
                )

            body_text = block.text[
                item_match.end():
            ].strip()

            current_label = detected_label
            current_blocks = []
            found_roman_item = True
            expected_index += 1

            if body_text:
                current_blocks.append(
                    _replace_block_text(
                        block,
                        body_text,
                    )
                )

            continue

        current_blocks.append(block)

    if current_blocks:
        items.append(
            _build_item(
                paragraph,
                current_label,
                current_blocks,
            )
        )

    if not found_roman_item:
        return (
            _build_item(
                paragraph,
                None,
                list(paragraph.content_blocks),
            ),
        )

    return tuple(items)

#Parse toàn bộ paragraphs
def parse_ucp600_items(
    paragraphs: tuple[LegalParagraph, ...],
) -> tuple[LegalItem, ...]:
    """Parse Roman items from all UCP 600 paragraphs."""

    return tuple(
        item
        for paragraph in paragraphs
        for item in parse_paragraph_items(paragraph)
    )