"""source row unique per tournament

Revision ID: a4d8f2c6e1b9
Revises: f6b8d0a2c4e7
Create Date: 2026-11-15 21:30:00.000000

`registrations.source_row_id` names the fencer-list row an issued registration
stands in for, and a row's id is unique only within its tournament: an `imp:`
key is a content fingerprint, so two tournaments that imported the same row and
issued it both carry it, and so does a tournament restored beside its original
(design export-tournament-settings D3). The deployment-wide unique index made
the second of those fail; this replaces it with a constraint per tournament.

No data moves. Every reader already filters by tournament, and no pair can be
duplicated under the old, wider index, so the narrower one cannot fail to
build. Downgrade restores the wide index and fails where two tournaments have
since come to share a row id — which is the situation it cannot represent.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a4d8f2c6e1b9"
down_revision: str | Sequence[str] | None = "f6b8d0a2c4e7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_registrations_source_row_id", table_name="registrations")
    with op.batch_alter_table("registrations") as batch:
        batch.create_unique_constraint(
            "uq_registrations_tournament_id_source_row_id", ["tournament_id", "source_row_id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("registrations") as batch:
        batch.drop_constraint("uq_registrations_tournament_id_source_row_id", type_="unique")
    op.create_index(
        "ix_registrations_source_row_id", "registrations", ["source_row_id"], unique=True
    )
