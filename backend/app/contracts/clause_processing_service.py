from pathlib import Path
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.contracts.db_models import (
    ContractClauseRecord,
    ContractClauseSpanRecord,
    ContractTextBlockRecord,
)
from app.contracts.models import (
    ContractClause,
    ContractStatus,
)
from app.contracts.mt700_item_parser import (
    parse_mt700_numbered_items,
)
from app.contracts.mt700_parser import parse_mt700_fields
from app.contracts.reading_order import order_contract_pages
from app.contracts.repository import ContractDocumentRepository
from app.contracts.storage import calculate_file_sha256
from app.rag.ingestion.pdf_extractor import extract_pdf_pages


class ContractClauseProcessingService:
    """Parse and persist traceable MT700 clauses."""

    def __init__(
        self,
        *,
        session: Session,
    ) -> None:
        self._session = session
        self._repository = ContractDocumentRepository(
            session
        )

    def _load_block_lookup(
        self,
        contract_id: UUID,
    ) -> dict[tuple[int, int], ContractTextBlockRecord]:
        """Load stored blocks by page and original block index."""

        statement = select(
            ContractTextBlockRecord
        ).where(
            ContractTextBlockRecord.contract_id
            == contract_id
        )

        blocks = self._session.scalars(
            statement
        ).all()

        return {
            (block.page_number, block.block_index): block
            for block in blocks
        }

    def _create_clause_record(
        self,
        *,
        clause: ContractClause,
        block_lookup: dict[
            tuple[int, int],
            ContractTextBlockRecord,
        ],
    ) -> ContractClauseRecord:
        """Convert one parsed clause into database records."""

        span_records: list[
            ContractClauseSpanRecord
        ] = []

        for span_order, span in enumerate(
            clause.source_spans
        ):
            lookup_key = (
                span.page_number,
                span.block_index,
            )
            block = block_lookup.get(lookup_key)

            if block is None:
                raise ValueError(
                    "Clause source block does not exist "
                    "in the stored contract"
                )

            span_records.append(
                ContractClauseSpanRecord(
                    clause_id=clause.clause_id,
                    span_order=span_order,
                    block_id=block.block_id,
                    char_start=span.char_start,
                    char_end=span.char_end,
                )
            )

        return ContractClauseRecord(
            clause_id=clause.clause_id,
            contract_id=clause.contract_id,
            parent_clause_id=clause.parent_clause_id,
            label=clause.label,
            title=clause.title,
            raw_text=clause.raw_text,
            kind=clause.kind,
            order_index=clause.order_index,
            page_start=clause.page_start,
            page_end=clause.page_end,
            spans=span_records,
        )

    def process_contract(
        self,
        *,
        contract_id: UUID,
        access_scope: str,
        file_path: Path,
        selected_page_numbers: frozenset[int],
        item_field_labels: frozenset[str],
    ) -> tuple[ContractClause, ...]:
        """Parse and replace all stored clauses for one contract."""

        document = self._repository.get_by_id(
            contract_id=contract_id,
            access_scope=access_scope,
        )

        if document is None:
            raise LookupError("Contract document was not found")

        resolved_path = file_path.resolve()

        if (
            calculate_file_sha256(resolved_path)
            != document.checksum_sha256
        ):
            raise ValueError(
                "Contract PDF checksum does not match "
                "the stored document"
            )

        try:
            pages = order_contract_pages(
                extract_pdf_pages(resolved_path)
            )

            fields = parse_mt700_fields(
                contract_id=contract_id,
                pages=pages,
                selected_page_numbers=selected_page_numbers,
            )
            items = parse_mt700_numbered_items(
                pages=pages,
                parent_fields=fields,
                item_field_labels=item_field_labels,
            )

            block_lookup = self._load_block_lookup(
                contract_id
            )

            self._session.execute(
                delete(ContractClauseRecord).where(
                    ContractClauseRecord.contract_id
                    == contract_id
                ),
                execution_options={
                    "synchronize_session": False,
                },
            )
            self._session.flush()

            field_records = [
                self._create_clause_record(
                    clause=field,
                    block_lookup=block_lookup,
                )
                for field in fields
            ]

            self._session.add_all(field_records)
            self._session.flush()

            item_records = [
                self._create_clause_record(
                    clause=item,
                    block_lookup=block_lookup,
                )
                for item in items
            ]

            self._session.add_all(item_records)

            document.status = ContractStatus.READY
            document.error_code = None
            document.error_message = None

            self._session.commit()

            return fields + items
        except Exception as error:
            self._session.rollback()

            failed_document = self._repository.get_by_id(
                contract_id=contract_id,
                access_scope=access_scope,
            )

            if failed_document is not None:
                failed_document.status = ContractStatus.FAILED
                failed_document.error_code = (
                    "clause_processing_failed"
                )
                failed_document.error_message = str(error)[:2000]
                self._session.commit()

            raise
