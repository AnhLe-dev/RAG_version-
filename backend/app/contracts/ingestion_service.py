from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from app.contracts.db_models import ContractDocumentRecord
from app.contracts.models import ContractStatus
from app.contracts.repository import ContractDocumentRepository
from app.contracts.storage import (
    ContractObjectStorage,
    calculate_file_sha256,
)
from app.rag.ingestion.pdf_extractor import extract_pdf_pages


class ContractIngestionService:
    """Store an original contract and its initial metadata."""

    def __init__(
        self,
        *,
        session: Session,
        storage: ContractObjectStorage,
    ) -> None:
        self._session = session
        self._storage = storage
        self._repository = ContractDocumentRepository(
            session
        )

    def upload_contract(
        self,
        *,
        file_path: Path,
        access_scope: str,
    ) -> ContractDocumentRecord:
        """Upload one PDF and persist its initial database record."""

        resolved_path = file_path.resolve()
        checksum = calculate_file_sha256(resolved_path)

        existing_record = self._repository.get_by_checksum(
            checksum_sha256=checksum,
            access_scope=access_scope,
        )

        if existing_record is not None:
            return existing_record

        extracted_pages = extract_pdf_pages(resolved_path)
        contract_id = uuid4()

        object_key: str | None = None

        try:
            object_key = self._storage.upload_pdf(
                contract_id=contract_id,
                access_scope=access_scope,
                file_path=resolved_path,
                expected_checksum=checksum,
            )

            record = ContractDocumentRecord(
                contract_id=contract_id,
                filename=resolved_path.name,
                version=1,
                checksum_sha256=checksum,
                object_key=object_key,
                document_type="swift_mt700",
                status=ContractStatus.UPLOADED,
                access_scope=access_scope,
                page_count=len(extracted_pages),
                processed_pages=[],
                ignored_pages=[],
                ocr_required_pages=[],
                error_code=None,
                error_message=None,
            )

            self._repository.add(record)
            self._session.commit()

            return record
        except Exception:
            self._session.rollback()

            if object_key is not None:
                self._storage.delete_object(object_key)

            raise
