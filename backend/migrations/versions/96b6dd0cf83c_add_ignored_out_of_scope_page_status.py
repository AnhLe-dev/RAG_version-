"""add ignored out of scope page status

Revision ID: 96b6dd0cf83c
Revises: 02b65599686f
"""

from collections.abc import Sequence

from alembic import op


revision: str = "96b6dd0cf83c"
down_revision: str | None = "02b65599686f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add a status for pages excluded from review scope."""

    op.execute(
        """
        ALTER TYPE page_processing_status
        ADD VALUE IF NOT EXISTS
        'ignored_out_of_scope'
        AFTER 'ignored_cover'
        """
    )


def downgrade() -> None:
    """Remove the status by rebuilding the PostgreSQL enum."""

    op.execute(
        """
        UPDATE contract_pages
        SET processing_status = 'ignored_cover'
        WHERE processing_status = 'ignored_out_of_scope'
        """
    )

    op.execute(
        """
        ALTER TYPE page_processing_status
        RENAME TO page_processing_status_old
        """
    )

    op.execute(
        """
        CREATE TYPE page_processing_status AS ENUM (
            'text',
            'ignored_cover',
            'ocr_required'
        )
        """
    )

    op.execute(
        """
        ALTER TABLE contract_pages
        ALTER COLUMN processing_status
        TYPE page_processing_status
        USING processing_status::text::page_processing_status
        """
    )

    op.execute(
        """
        DROP TYPE page_processing_status_old
        """
    )