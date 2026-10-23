from app.rag.models import ExtractedPage, PageTextBlock


_ROW_TOLERANCE = 1.5


def _block_top(
    block: PageTextBlock,
) -> float:
    """Return the top coordinate of one block."""

    return block.bbox[1]


def _order_row(
    blocks: list[PageTextBlock],
) -> list[PageTextBlock]:
    """Order blocks on the same visual row left to right."""

    return sorted(
        blocks,
        key=lambda block: (
            block.bbox[0],
            block.block_index,
        ),
    )


def order_contract_page_blocks(
    page: ExtractedPage,
) -> ExtractedPage:
    """Restore row-based reading order for one MT700 page."""

    vertically_sorted = sorted(
        page.blocks,
        key=lambda block: (
            _block_top(block),
            block.bbox[0],
            block.block_index,
        ),
    )

    ordered_blocks: list[PageTextBlock] = []
    current_row: list[PageTextBlock] = []
    current_row_top: float | None = None

    for block in vertically_sorted:
        block_top = _block_top(block)

        if (
            current_row_top is None
            or abs(block_top - current_row_top)
            <= _ROW_TOLERANCE
        ):
            current_row.append(block)

            if current_row_top is None:
                current_row_top = block_top

            continue

        ordered_blocks.extend(
            _order_row(current_row)
        )
        current_row = [block]
        current_row_top = block_top

    if current_row:
        ordered_blocks.extend(
            _order_row(current_row)
        )

    return ExtractedPage(
        page_number=page.page_number,
        width=page.width,
        height=page.height,
        blocks=tuple(ordered_blocks),
    )


def order_contract_pages(
    pages: tuple[ExtractedPage, ...],
) -> tuple[ExtractedPage, ...]:
    """Restore MT700 reading order without UCP column rules."""

    return tuple(
        order_contract_page_blocks(page)
        for page in pages
    )
