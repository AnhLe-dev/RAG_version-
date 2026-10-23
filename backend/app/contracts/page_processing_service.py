from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.contracts.reading_order import order_contract_pages
from app.contracts.db_models import (
    ContractDocumentRecord,
    ContractPageRecord,
    ContractTextBlockRecord,
)
from app.contracts.models import (
    ContractStatus,
    PageProcessingStatus,
)
from app.contracts.page_classifier import (
    classify_contract_page,
    classify_contract_pages,
)
from app.contracts.repository import ContractDocumentRepository
from app.contracts.storage import calculate_file_sha256
from app.rag.ingestion.pdf_extractor import extract_pdf_pages


class ContractPageProcessingService:
    """Extract and persist positioned text from selected pages."""

    def __init__(
        self,
        *,
        session: Session,
    ) -> None:
        self._session = session
        self._repository = ContractDocumentRepository(
            session
        )

    def process_contract(
        self,
        *,
        contract_id: UUID,
        access_scope: str,
        file_path: Path,
        selected_text_pages: frozenset[int],
        ignored_cover_pages: frozenset[int],
    ) -> ContractDocumentRecord:
        """Persist page metadata and selected text blocks."""

        record = self._repository.get_by_id(
            contract_id=contract_id,
            access_scope=access_scope,
        )

        if record is None:
            raise LookupError("Contract document was not found")

        resolved_path = file_path.resolve()
        actual_checksum = calculate_file_sha256(
            resolved_path
        )

        if actual_checksum != record.checksum_sha256:
            raise ValueError(
                "Contract PDF checksum does not match "
                "the stored document"
            )

        extracted_pages = order_contract_pages(
            extract_pdf_pages(resolved_path)
        )

        if len(extracted_pages) != record.page_count:
            raise ValueError(
                "Extracted page count does not match "
                "the stored document"
            )

        classification = classify_contract_pages(
            extracted_pages,
            selected_text_pages=selected_text_pages,
            ignored_cover_pages=ignored_cover_pages,
        )

        record.status = ContractStatus.PROCESSING
        record.error_code = None
        record.error_message = None
        self._session.commit()

        try:
            record.pages.clear()
            self._session.flush()

            for page in extracted_pages:
                page_status = classify_contract_page(
                    page,
                    selected_text_pages=selected_text_pages,
                    ignored_cover_pages=ignored_cover_pages,
                )

                stored_blocks = (
                    page.blocks
                    if page_status
                    == PageProcessingStatus.TEXT
                    else ()
                )

                page_record = ContractPageRecord(
                    contract_id=contract_id,
                    page_number=page.page_number,
                    width=page.width,
                    height=page.height,
                    processing_status=page_status,
                    text_block_count=len(stored_blocks),
                )

                for sort_index, block in enumerate(
                    stored_blocks
                ):
                    x0, y0, x1, y1 = block.bbox

                    page_record.blocks.append(
                        ContractTextBlockRecord(
                            contract_id=contract_id,
                            page_number=page.page_number,
                            block_index=block.block_index,
                            sort_index=sort_index,
                            raw_text=block.text,
                            x0=x0,
                            y0=y0,
                            x1=x1,
                            y1=y1,
                            is_content=True,
                        )
                    )

                record.pages.append(page_record)

            record.processed_pages = list(
                classification.processed_pages
            )
            record.ignored_pages = list(
                classification.ignored_pages
            )
            record.ocr_required_pages = list(
                classification.ocr_required_pages
            )

            record.status = (
                ContractStatus.PARTIAL
                if classification.ocr_required_pages
                else ContractStatus.READY
            )

            self._session.commit()

            return record
        except Exception as error:
            self._session.rollback()

            failed_record = self._repository.get_by_id(
                contract_id=contract_id,
                access_scope=access_scope,
            )

            if failed_record is not None:
                failed_record.status = ContractStatus.FAILED
                failed_record.error_code = (
                    "page_processing_failed"
                )
                failed_record.error_message = str(error)[:2000]
                self._session.commit()

            raise
