from argparse import ArgumentParser
from pathlib import Path
from uuid import UUID

from app.contracts.clause_processing_service import (
    ContractClauseProcessingService,
)
from app.contracts.models import ClauseKind
from app.core.config import get_settings
from app.db.session import (
    create_database_engine,
    create_session_factory,
)


BACKEND_ROOT = Path(__file__).resolve().parents[2]
LC01_PATH = BACKEND_ROOT / "data/raw/contracts/LC01.pdf"


def parse_contract_id() -> UUID:
    """Read the contract UUID from the command line."""

    parser = ArgumentParser()
    parser.add_argument(
        "contract_id",
        type=UUID,
    )

    return parser.parse_args().contract_id


def main() -> None:
    """Parse and persist LC01 MT700 clauses."""

    contract_id = parse_contract_id()
    settings = get_settings()
    engine = create_database_engine(settings)
    session_factory = create_session_factory(engine)

    try:
        with session_factory() as session:
            service = ContractClauseProcessingService(
                session=session,
            )

            clauses = service.process_contract(
                contract_id=contract_id,
                access_scope="public",
                file_path=LC01_PATH,
                selected_page_numbers=frozenset({2, 3}),
                item_field_labels=frozenset(
                    {"46A", "47A"}
                ),
            )

            field_count = sum(
                clause.kind == ClauseKind.SWIFT_FIELD
                for clause in clauses
            )
            item_count = sum(
                clause.kind == ClauseKind.SWIFT_ITEM
                for clause in clauses
            )

            clause_lookup = {
                clause.label: clause
                for clause in clauses
            }

            print("LC01 clause processing passed")
            print(f"field_count={field_count}")
            print(f"item_count={item_count}")
            print(f"total_clause_count={len(clauses)}")

            for label in ("46A", "47A"):
                clause = clause_lookup[label]

                print(
                    f"{label}_page_range="
                    f"{clause.page_start}-"
                    f"{clause.page_end}"
                )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
