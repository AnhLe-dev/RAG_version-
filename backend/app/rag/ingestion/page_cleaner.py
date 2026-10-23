import re
from collections import Counter
from math import ceil

from app.rag.models import ExtractedPage, PageTextBlock


_TOP_MARGIN_RATIO = 0.15
_BOTTOM_MARGIN_RATIO = 0.15
_REPEAT_RATIO = 0.60

def _create_text_fingerprint(text: str) -> str:
    """Create a comparable fingerprint for repeated margin text."""

    normalized_text = " ".join(text.casefold().split())

    return re.sub(r"\d+", "<number>", normalized_text)

def _is_margin_block(
    page: ExtractedPage,
    block: PageTextBlock,
) -> bool:
    """Return whether a block is inside the header or footer region."""

    _, y0, _, y1 = block.bbox

    top_limit = page.height * _TOP_MARGIN_RATIO
    bottom_limit = page.height * (1 - _BOTTOM_MARGIN_RATIO)

    is_header = y1 <= top_limit
    is_footer = y0 >= bottom_limit

    return is_header or is_footer

def _find_repeated_margin_fingerprints(
    pages: tuple[ExtractedPage, ...],
) -> set[str]:
    """Find margin text repeated across most pages."""

    if len(pages) < 3:
        return set()

    fingerprint_counts: Counter[str] = Counter()

    for page in pages:
        page_fingerprints = {
            _create_text_fingerprint(block.text)
            for block in page.blocks
            if _is_margin_block(page, block)
        }

        fingerprint_counts.update(page_fingerprints)

    minimum_page_count = max(
        2,
        ceil(len(pages) * _REPEAT_RATIO),
    )

    return {
        fingerprint
        for fingerprint, count in fingerprint_counts.items()
        if count >= minimum_page_count
    }

def remove_repeated_margin_blocks(
    pages: tuple[ExtractedPage, ...],
) -> tuple[ExtractedPage, ...]:
    """Remove repeated headers and footers while preserving source mapping."""

    repeated_fingerprints = _find_repeated_margin_fingerprints(pages)

    if not repeated_fingerprints:
        return pages

    cleaned_pages: list[ExtractedPage] = []

    for page in pages:
        retained_blocks = tuple(
            block
            for block in page.blocks
            if not (
                _is_margin_block(page, block)
                and _create_text_fingerprint(block.text)
                in repeated_fingerprints
            )
        )

        cleaned_pages.append(
            ExtractedPage(
                page_number=page.page_number,
                width=page.width,
                height=page.height,
                blocks=retained_blocks,
            )
        )

    return tuple(cleaned_pages)