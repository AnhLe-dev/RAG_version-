from dataclasses import dataclass

from app.contracts.models import PageProcessingStatus
from app.rag.models import ExtractedPage


@dataclass(frozen=True)
class ContractPageClassification:
    """Group contract pages by their processing result."""

    processed_pages: tuple[int, ...]
    ignored_pages: tuple[int, ...]
    ocr_required_pages: tuple[int, ...]


def classify_contract_page(
    page: ExtractedPage,
    *,
    selected_text_pages: frozenset[int],
    ignored_cover_pages: frozenset[int],
) -> PageProcessingStatus:
    """Classify one page according to the selected review scope."""

    if page.page_number in ignored_cover_pages:
        return PageProcessingStatus.IGNORED_COVER

    if page.page_number not in selected_text_pages:
        return PageProcessingStatus.IGNORED_OUT_OF_SCOPE

    if page.blocks:
        return PageProcessingStatus.TEXT

    return PageProcessingStatus.OCR_REQUIRED


def classify_contract_pages(
    pages: tuple[ExtractedPage, ...],
    *,
    selected_text_pages: frozenset[int],
    ignored_cover_pages: frozenset[int],
) -> ContractPageClassification:
    """Classify all pages while preserving full page coverage."""

    if selected_text_pages & ignored_cover_pages:
        raise ValueError(
            "Selected pages and cover pages must not overlap"
        )

    available_pages = {
        page.page_number
        for page in pages
    }
    configured_pages = (
        selected_text_pages
        | ignored_cover_pages
    )

    if not configured_pages <= available_pages:
        raise ValueError(
            "Configured page is outside the PDF"
        )

    processed_pages: list[int] = []
    ignored_pages: list[int] = []
    ocr_required_pages: list[int] = []

    for page in pages:
        status = classify_contract_page(
            page,
            selected_text_pages=selected_text_pages,
            ignored_cover_pages=ignored_cover_pages,
        )

        if status == PageProcessingStatus.TEXT:
            processed_pages.append(page.page_number)
        elif status == PageProcessingStatus.OCR_REQUIRED:
            ocr_required_pages.append(page.page_number)
        else:
            ignored_pages.append(page.page_number)

    return ContractPageClassification(
        processed_pages=tuple(processed_pages),
        ignored_pages=tuple(ignored_pages),
        ocr_required_pages=tuple(ocr_required_pages),
    )