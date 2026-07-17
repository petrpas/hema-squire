"""baseline

Revision ID: 666ccfb15cd3
Revises: 
Create Date: 2026-07-17 23:06:16.963611

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = '666ccfb15cd3'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
