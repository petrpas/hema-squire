"""fixed row numbers, and the Import / Fencers phase split

Revision ID: d2a71f4b83c6
Revises: b3d7f1a05c92
Create Date: 2026-08-28 00:00:00.000000

Two things the console needs at once.

`sheet_row_numbers` gives every row of a tournament's table a number that never
moves: allocated when the row enters the tournament, keyed by its sheet row id
("reg:<id>" or "imp:<fingerprint>"), and never reissued. Existing tournaments
are backfilled in the order the table will display — registrations by
registration moment, then the latest imported batch in file order.

The `load` and `parsing` phases are replaced by `import` and `fencers`, so
stored rules carrying the old names are rewritten. The mapping goes by what a
rule targets, not by its old name alone: a rule on an imported row corrected how
a file was read and belongs to the Import log, while a rule on a registration
was a decision about a fencer and belongs to the fencer list's log. Filing the
second kind under Import would blur exactly the distinction the split draws.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d2a71f4b83c6"
down_revision: str | Sequence[str] | None = "b3d7f1a05c92"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sheet_row_numbers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tournament_id", sa.Integer(), nullable=False),
        sa.Column("row_id", sa.String(length=50), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tournament_id", "row_id"),
        sa.UniqueConstraint("tournament_id", "number"),
    )

    connection = op.get_bind()
    tournaments = [
        row[0] for row in connection.execute(sa.text("SELECT id FROM tournaments"))
    ]
    for tournament_id in tournaments:
        row_ids = [
            f"reg:{row[0]}"
            for row in connection.execute(
                sa.text(
                    "SELECT id FROM registrations WHERE tournament_id = :t "
                    "ORDER BY registered_at, id"
                ),
                {"t": tournament_id},
            )
        ]
        latest_batch = connection.execute(
            sa.text(
                "SELECT id FROM import_batches WHERE tournament_id = :t "
                "ORDER BY uploaded_at DESC, id DESC LIMIT 1"
            ),
            {"t": tournament_id},
        ).scalar()
        if latest_batch is not None:
            row_ids += [
                f"imp:{row[0]}"
                for row in connection.execute(
                    sa.text(
                        "SELECT key FROM imported_rows WHERE batch_id = :b "
                        "ORDER BY row_number"
                    ),
                    {"b": latest_batch},
                )
            ]
        for number, row_id in enumerate(row_ids, start=1):
            connection.execute(
                sa.text(
                    "INSERT INTO sheet_row_numbers (tournament_id, row_id, number) "
                    "VALUES (:t, :r, :n)"
                ),
                {"t": tournament_id, "r": row_id, "n": number},
            )

    connection.execute(sa.text("UPDATE rules SET phase = 'import' WHERE phase = 'load'"))
    connection.execute(
        sa.text(
            "UPDATE rules SET phase = 'import' "
            "WHERE phase = 'parsing' AND target LIKE 'imp:%'"
        )
    )
    connection.execute(
        sa.text(
            "UPDATE rules SET phase = 'fencers' "
            "WHERE phase = 'parsing' AND target NOT LIKE 'imp:%'"
        )
    )


def downgrade() -> None:
    connection = op.get_bind()
    # the split is not reversible row by row — an Import rule may have been a
    # Load rule or a Parsing one — so both names go back to the phase that
    # owned the operation each targets
    connection.execute(
        sa.text("UPDATE rules SET phase = 'load' WHERE phase = 'import'")
    )
    connection.execute(
        sa.text("UPDATE rules SET phase = 'parsing' WHERE phase = 'fencers'")
    )
    op.drop_table("sheet_row_numbers")
