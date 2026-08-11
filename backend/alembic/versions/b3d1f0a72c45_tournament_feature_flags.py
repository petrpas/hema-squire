"""tournament feature flags

Revision ID: b3d1f0a72c45
Revises: 8cea4fd092f9
Create Date: 2026-08-11 00:00:00.000000

Adds the four feature flags that make up a tournament's mode —
`feature_schedule`, `feature_payments`, `feature_teams`, `feature_extras` —
and backfills them in the same revision, so no tournament is ever observable
in the wrong mode (design tournament-modes D9).

The derivation is generous: any evidence at all turns a feature on, so the
worst case for an existing organizer is a console that looks exactly as it
does today. A never-configured draft lands in easy mode, which is the point.
It runs once here and is never a rule the application maintains.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3d1f0a72c45"
down_revision: str | Sequence[str] | None = "8cea4fd092f9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FLAGS = ("feature_schedule", "feature_payments", "feature_teams", "feature_extras")

# each flag against the evidence that turns it on, as sub-selects over the
# tournament being updated
DERIVATIONS = {
    "feature_schedule": """
        EXISTS (
            SELECT 1 FROM disciplines d
            WHERE d.tournament_id = tournaments.id
              AND (
                  (d.schedule_when IS NOT NULL AND d.schedule_when != '')
                  OR (d.schedule_where IS NOT NULL AND d.schedule_where != '')
              )
        )
    """,
    "feature_payments": """
        (tournaments.bank_account IS NOT NULL AND tournaments.bank_account != '')
        OR tournaments.payment_mode != 'immediate'
        OR EXISTS (
            SELECT 1 FROM bank_transactions t
            WHERE t.tournament_id = tournaments.id
        )
    """,
    "feature_teams": """
        EXISTS (
            SELECT 1 FROM disciplines d
            WHERE d.tournament_id = tournaments.id AND d.kind = 'team'
        )
    """,
    "feature_extras": """
        EXISTS (
            SELECT 1 FROM extra_items e
            WHERE e.tournament_id = tournaments.id
        )
    """,
}


def upgrade() -> None:
    with op.batch_alter_table("tournaments", schema=None) as batch_op:
        for flag in FLAGS:
            batch_op.add_column(
                sa.Column(flag, sa.Boolean(), nullable=False, server_default=sa.false())
            )

    conn = op.get_bind()
    for flag, evidence in DERIVATIONS.items():
        conn.execute(
            sa.text(f"UPDATE tournaments SET {flag} = 1 WHERE {evidence}")  # noqa: S608
        )

    # the default existed only to backfill; the ORM supplies it from here on
    with op.batch_alter_table("tournaments", schema=None) as batch_op:
        for flag in FLAGS:
            batch_op.alter_column(flag, server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("tournaments", schema=None) as batch_op:
        for flag in FLAGS:
            batch_op.drop_column(flag)
