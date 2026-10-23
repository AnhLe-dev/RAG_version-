from hashlib import sha256
from pathlib import Path

from app.rag.models import SourceDocument


_READ_BUFFER_SIZE = 1024 * 1024
_PDF_SIGNATURE = b"%PDF-"

def validate_pdf_path(file_path: Path) -> None:
    """Validate basic requirements for an ingestion PDF."""

    if not file_path.exists():
        raise FileNotFoundError(
            f"Source document does not exist: {file_path}"
        )

    if not file_path.is_file():
        raise ValueError(
            f"Source document is not a file: {file_path}"
        )

    if file_path.suffix.casefold() != ".pdf":
        raise ValueError(
            f"Source document must have a .pdf extension: {file_path}"
        )

    if file_path.stat().st_size == 0:
        raise ValueError(
            f"Source document is empty: {file_path}"
        )

    with file_path.open("rb") as source_file:
        signature = source_file.read(len(_PDF_SIGNATURE))

    if signature != _PDF_SIGNATURE:
        raise ValueError(
            f"Source document does not have a valid PDF signature: {file_path}"
        )

def _calculate_sha256(file_path: Path) -> str:
    """Calculate the SHA-256 checksum without loading the full file."""

    digest = sha256()

    with file_path.open("rb") as source_file:
        while file_block := source_file.read(_READ_BUFFER_SIZE):
            digest.update(file_block)

    return digest.hexdigest()

def create_source_document(
    file_path: str | Path,
    *,
    source_id: str,
    source_version: str,
    access_scope: str,
) -> SourceDocument:
    """Validate a PDF and create its source metadata."""

    resolved_path = Path(file_path)

    validate_pdf_path(resolved_path)

    return SourceDocument(
        source_id=source_id,
        filename=resolved_path.name,
        source_version=source_version,
        checksum_sha256=_calculate_sha256(resolved_path),
        access_scope=access_scope,
    )