from hashlib import sha256
from pathlib import Path
from re import fullmatch
from typing import Protocol
from uuid import UUID

from minio import Minio
from pydantic import SecretStr

from app.core.config import Settings
from app.rag.ingestion.source_loader import (
    validate_pdf_path,
)


class ContractObjectStorage(Protocol):
    """Define storage operations required by contract ingestion."""

    def verify_bucket(self) -> None:
        """Verify that the configured bucket is accessible."""

    def upload_pdf(
        self,
        *,
        contract_id: UUID,
        access_scope: str,
        file_path: Path,
        expected_checksum: str,
    ) -> str:
        """Upload one PDF and return its object key."""

    def delete_object(
        self,
        object_key: str,
    ) -> None:
        """Delete one stored object."""


def calculate_file_sha256(
    file_path: Path,
) -> str:
    """Calculate SHA-256 without loading the full file in memory."""

    digest = sha256()

    with file_path.open("rb") as source_file:
        while block := source_file.read(1024 * 1024):
            digest.update(block)

    return digest.hexdigest()


def require_secret(
    value: SecretStr | None,
    variable_name: str,
) -> str:
    """Return a configured secret without logging its value."""

    if value is None:
        raise ValueError(
            f"{variable_name} is not configured"
        )

    secret_value = value.get_secret_value()

    if not secret_value:
        raise ValueError(
            f"{variable_name} is not configured"
        )

    return secret_value


class MinioContractStorage:
    """Store original contract PDFs in a private MinIO bucket."""

    def __init__(
        self,
        *,
        client: Minio,
        bucket_name: str,
    ) -> None:
        self._client = client
        self._bucket_name = bucket_name

    def verify_bucket(self) -> None:
        """Fail clearly when the configured bucket is unavailable."""

        if not self._client.bucket_exists(
            self._bucket_name
        ):
            raise RuntimeError(
                "Configured contract bucket does not exist"
            )

    def upload_pdf(
        self,
        *,
        contract_id: UUID,
        access_scope: str,
        file_path: Path,
        expected_checksum: str,
    ) -> str:
        """Validate and upload one immutable source PDF."""

        resolved_path = file_path.resolve()
        validate_pdf_path(resolved_path)

        normalized_scope = access_scope.strip()

        if not fullmatch(
            r"[A-Za-z0-9._-]+",
            normalized_scope,
        ):
            raise ValueError(
                "ACCESS_SCOPE contains unsupported characters"
            )

        if not fullmatch(
            r"[0-9a-f]{64}",
            expected_checksum,
        ):
            raise ValueError(
                "EXPECTED_CHECKSUM must be a SHA-256 hex digest"
            )

        actual_checksum = calculate_file_sha256(
            resolved_path
        )

        if actual_checksum != expected_checksum:
            raise ValueError(
                "PDF checksum does not match expected checksum"
            )

        object_key = (
            f"{normalized_scope}/"
            f"{contract_id}/"
            f"{actual_checksum}.pdf"
        )

        self._client.fput_object(
            bucket_name=self._bucket_name,
            object_name=object_key,
            file_path=str(resolved_path),
            content_type="application/pdf",
            metadata={
                "sha256": actual_checksum,
            },
        )

        stored_object = self._client.stat_object(
            bucket_name=self._bucket_name,
            object_name=object_key,
        )

        stored_checksum = (
            stored_object.metadata.get(
                "x-amz-meta-sha256"
            )
            or stored_object.metadata.get(
                "sha256"
            )
        )

        if stored_checksum != actual_checksum:
            self._client.remove_object(
                bucket_name=self._bucket_name,
                object_name=object_key,
            )
            raise RuntimeError(
                "Stored PDF checksum metadata is invalid"
            )

        return object_key

    def delete_object(
        self,
        object_key: str,
    ) -> None:
        """Delete an object during failure compensation."""

        normalized_key = object_key.strip()

        if not normalized_key:
            raise ValueError(
                "OBJECT_KEY must not be empty"
            )

        self._client.remove_object(
            bucket_name=self._bucket_name,
            object_name=normalized_key,
        )


def create_contract_object_storage(
    settings: Settings,
) -> MinioContractStorage:
    """Build MinIO storage from validated application settings."""

    endpoint = settings.minio_endpoint

    if endpoint is None or not endpoint.strip():
        raise ValueError(
            "MINIO_ENDPOINT is not configured"
        )

    access_key = require_secret(
        settings.minio_access_key,
        "MINIO_ACCESS_KEY",
    )
    secret_key = require_secret(
        settings.minio_secret_key,
        "MINIO_SECRET_KEY",
    )

    client = Minio(
        endpoint=endpoint.strip(),
        access_key=access_key,
        secret_key=secret_key,
        secure=settings.minio_secure,
    )

    return MinioContractStorage(
        client=client,
        bucket_name=settings.minio_bucket,
    )