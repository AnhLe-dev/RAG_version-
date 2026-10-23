from app.rag.models import ExtractedPage, PageTextBlock


_COLUMN_SPLIT_RATIO = 0.5

def _create_reading_order_key(
    block: PageTextBlock,
    page_width: float,
) -> tuple[int, float, float]:
    """Create a sort key for a two-column page."""

    x0, y0, x1, _ = block.bbox
    column_split = page_width * _COLUMN_SPLIT_RATIO
    block_center_x = (x0 + x1) / 2

    column_index = 0 if block_center_x < column_split else 1
    return column_index, y0, x0

def _order_page_blocks(page: ExtractedPage) -> ExtractedPage:
    """Order one page from the left column to the right column."""

    ordered_blocks = tuple(
        sorted(
            page.blocks,
            key=lambda block: _create_reading_order_key(
                block,
                page.width,
            ),
        )
    )

    return ExtractedPage(
        page_number=page.page_number,
        width=page.width,
        height=page.height,
        blocks=ordered_blocks,
    )

def order_two_column_pages(
    pages: tuple[ExtractedPage, ...],
) -> tuple[ExtractedPage, ...]:
    """Restore reading order for a two-column PDF."""

    return tuple(
        _order_page_blocks(page)
        for page in pages
    )