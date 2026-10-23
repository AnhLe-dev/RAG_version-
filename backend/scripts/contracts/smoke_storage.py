from pathlib import Path
from uuid import uuid4

from app.contracts.storage import (
    calculate_file_sha256,
    create_contract_object_storage,
)
from app.core.config import get_settings


BACKEND_ROOT = Path(__file__).resolve().parents[2]
LC01_PATH = BACKEND_ROOT / "data/raw/contracts/LC01.pdf"


def main() -> None:
    """Verify the real MinIO upload and cleanup flow using LC01."""

    checksum = calculate_file_sha256(LC01_PATH)
    storage = create_contract_object_storage(get_settings())

    storage.verify_bucket()

    object_key = storage.upload_pdf(
        contract_id=uuid4(),
        access_scope="public",
        file_path=LC01_PATH,
        expected_checksum=checksum,
    )

    print("LC01 upload and checksum verification passed")

    storage.delete_object(object_key)

    print("Temporary LC01 object deleted")


if __name__ == "__main__":
    main()

