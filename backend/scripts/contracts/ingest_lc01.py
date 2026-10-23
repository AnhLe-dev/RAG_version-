from pathlib import Path

from app.contracts.ingestion_service import (
    ContractIngestionService,
)
from app.contracts.storage import (
    create_contract_object_storage,
)
from app.core.config import get_settings
from app.db.session import (
    create_database_engine,
    create_session_factory,
)


BACKEND_ROOT = Path(__file__).resolve().parents[2]
LC01_PATH = BACKEND_ROOT / "data/raw/contracts/LC01.pdf"


def main() -> None:
    """Upload LC01 and persist its initial database record."""

    settings = get_settings()
    engine = create_database_engine(settings)
    session_factory = create_session_factory(engine)
    storage = create_contract_object_storage(settings)

    try:
        with session_factory() as session:
            service = ContractIngestionService(
                session=session,
                storage=storage,
            )

            record = service.upload_contract(
                file_path=LC01_PATH,
                access_scope="public",
            )

            print("LC01 ingestion passed")
            print(f"contract_id={record.contract_id}")
            print(f"filename={record.filename}")
            print(f"status={record.status.value}")
            print(f"page_count={record.page_count}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
