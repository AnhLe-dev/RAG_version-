from dataclasses import dataclass
from pathlib import Path

from app.core.config import Settings
from app.rag.ingestion.article_parser import (
    parse_ucp600_articles,
)
from app.rag.ingestion.chunk_builder import (
    build_document_chunks,
)
from app.rag.ingestion.item_parser import (
    parse_ucp600_items,
)
from app.rag.ingestion.page_cleaner import (
    remove_repeated_margin_blocks,
)
from app.rag.ingestion.paragraph_parser import (
    parse_ucp600_paragraphs,
)
from app.rag.ingestion.pdf_extractor import (
    extract_pdf_pages,
)
from app.rag.ingestion.reading_order import (
    order_two_column_pages,
)
from app.rag.ingestion.source_loader import (
    create_source_document,
)
from app.rag.models import (
    DocumentChunk,
    LegalArticle,
    LegalItem,
    LegalParagraph,
    SourceDocument,
)


BACKEND_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_PDF_PATH = (
    BACKEND_ROOT
    / "data"
    / "raw"
    / "ucp600"
    / "UCP600.pdf"
)

UCP600_SOURCE_ID = "ucp600"
UCP600_SOURCE_VERSION = "1"
UCP600_ACCESS_SCOPE = "public"


@dataclass(frozen=True)
class PreparedCorpus:
    """Contain the prepared UCP 600 source and structures."""

    source: SourceDocument
    articles: tuple[LegalArticle, ...]
    paragraphs: tuple[LegalParagraph, ...]
    items: tuple[LegalItem, ...]
    chunks: tuple[DocumentChunk, ...]


def prepare_ucp600_corpus(
    settings: Settings,
    pdf_path: Path = DEFAULT_PDF_PATH,
) -> PreparedCorpus:
    """Run the complete UCP 600 ingestion pipeline."""

    source = create_source_document(
        pdf_path,
        source_id=UCP600_SOURCE_ID,
        source_version=UCP600_SOURCE_VERSION,
        access_scope=UCP600_ACCESS_SCOPE,
    )

    pages = extract_pdf_pages(pdf_path)

    cleaned_pages = remove_repeated_margin_blocks(
        pages
    )

    ordered_pages = order_two_column_pages(
        cleaned_pages
    )

    articles = parse_ucp600_articles(
        ordered_pages
    )

    paragraphs = parse_ucp600_paragraphs(
        articles
    )

    items = parse_ucp600_items(
        paragraphs
    )

    chunks = build_document_chunks(
        source,
        articles,
        items,
        max_characters=settings.max_chunk_characters,
    )

    return PreparedCorpus(
        source=source,
        articles=articles,
        paragraphs=paragraphs,
        items=items,
        chunks=chunks,
    )