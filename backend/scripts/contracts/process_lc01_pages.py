from argparse import ArgumentParser
from pathlib import Path
from uuid import UUID

from app.contracts.page_processing_service import (
    ContractPageProcessingService,
)
from app.core.config import get_settings
from app.db.session import (
    create_database_engine,
    create_session_factory,
)


BACKEND_ROOT = Path(__file__).resolve().parents[2]
LC01_PATH = BACKEND_ROOT / "data/raw/contracts/LC01.pdf"


def parse_contract_id() -> UUID:
    """Read and validate the contract ID from the command line."""

    parser = ArgumentParser()
    parser.add_argument(
        "contract_id",
        type=UUID,
        help="Contract UUID returned by the upload step",
    )

    arguments = parser.parse_args()

    return arguments.contract_id


def main() -> None:
    """Persist LC01 page metadata and page 2-3 text blocks."""

    contract_id = parse_contract_id()
    settings = get_settings()
    engine = create_database_engine(settings)
    session_factory = create_session_factory(engine)

    try:
        with session_factory() as session:
            service = ContractPageProcessingService(
                session=session,
            )

            record = service.process_contract(
                contract_id=contract_id,
                access_scope="public",
                file_path=LC01_PATH,
                selected_text_pages=frozenset({2, 3}),
                ignored_cover_pages=frozenset({1}),
            )

            stored_block_count = sum(
                page.text_block_count
                for page in record.pages
            )

            print("LC01 page processing passed")
            print(f"status={record.status.value}")
            print(
                f"processed_pages="
                f"{record.processed_pages}"
            )
            print(
                f"ignored_pages="
                f"{record.ignored_pages}"
            )
            print(
                f"ocr_required_pages="
                f"{record.ocr_required_pages}"
            )
            print(
                f"stored_page_count="
                f"{len(record.pages)}"
            )
            print(
                f"stored_block_count="
                f"{stored_block_count}"
            )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
