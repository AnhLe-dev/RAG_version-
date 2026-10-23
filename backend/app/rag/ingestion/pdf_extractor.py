from pathlib import Path

import pymupdf

from app.rag.ingestion.source_loader import validate_pdf_path
from app.rag.models import ExtractedPage, PageTextBlock

def _extract_page(
    page: pymupdf.Page,
    page_number: int,
) -> ExtractedPage:
    """Extract positioned text blocks from one PDF page."""

    text_blocks: list[PageTextBlock] = []

    for raw_block in page.get_text("blocks", sort=True):
        x0, y0, x1, y1, text, block_number, block_type = raw_block[:7]

        if block_type != 0:
            continue

        stripped_text = str(text).strip()

        if not stripped_text:
            continue

        text_blocks.append(
            PageTextBlock(
                block_index=int(block_number),
                text=stripped_text,
                bbox=(
                    float(x0),
                    float(y0),
                    float(x1),
                    float(y1),
                ),
            )
        )

    return ExtractedPage(
        page_number=page_number,
        width=float(page.rect.width),
        height=float(page.rect.height),
        blocks=tuple(text_blocks),
    )

def extract_pdf_pages(
    file_path: str | Path,
) -> tuple[ExtractedPage, ...]:
    """Extract layout-aware text blocks from a PDF."""

    resolved_path = Path(file_path)
    validate_pdf_path(resolved_path)

    try:
        with pymupdf.open(str(resolved_path)) as document:
            if document.needs_pass:
                raise ValueError(
                    "Encrypted PDF documents are not supported"
                )

            pages = tuple(
                _extract_page(page, page_index + 1)
                for page_index, page in enumerate(document)
            )
    except pymupdf.FileDataError as error:
        raise ValueError(
            f"PDF structure is invalid: {resolved_path}"
        ) from error

    if not pages:
        raise ValueError("PDF document does not contain any pages")

    if not any(page.blocks for page in pages):
        raise ValueError(
            "PDF document contains no extractable text; OCR is required"
        )

    return pages