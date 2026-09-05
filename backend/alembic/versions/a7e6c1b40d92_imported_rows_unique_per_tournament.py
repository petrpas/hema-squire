"""an imported row belongs to the tournament, not to the upload

Revision ID: a7e6c1b40d92
Revises: c4d17ea90b52
Create Date: 2026-09-05 12:00:00.000000

Uploads accumulate rather than replace. A row whose content the tournament has
already imported is now recognised at intake and not taken in again, so a key
names one source row per tournament (spec `table-import`, Intake takes in only
rows new to the tournament).

Existing data predates that. Under the old model every upload took in every row
it carried, so a tournament that uploaded the same form export three times holds
each unchanged row three times, under one key in three batches. The rows of a
group are byte-identical by construction — the key is a fingerprint of the raw
content — so collapsing the group loses nothing but the record that a later file
also carried the row.

The survivor is the earliest (lowest batch_id): that is the arrival the fixed
fencer number was allocated against, and the one whose `_source` names the file
the row first came on.

Nothing references `imported_rows.id`. Parse decisions, match proposals and
dedup classifications key on `key`; rules and registrations name the string
"imp:<key>"; `importclear` deletes by tournament.

The downgrade restores the old constraint and leaves the collapsed rows
collapsed. Re-uploading the files is what brings them back, which is what the
union does anyway.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7e6c1b40d92"
down_revision: str | Sequence[str] | None = "c4d17ea90b52"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    # every row a lower-batch row of the same tournament and key precedes
    connection.execute(
        sa.text(
            "DELETE FROM imported_rows WHERE id NOT IN ("
            " SELECT MIN(id) FROM imported_rows GROUP BY tournament_id, key)"
        )
    )
    # batch mode because the deployment runs on SQLite, which rebuilds the
    # table rather than altering a constraint in place
    with op.batch_alter_table("imported_rows", schema=None) as batch_op:
        batch_op.drop_constraint("uq_imported_rows_batch_id", type_="unique")
        batch_op.create_unique_constraint(
            "uq_imported_rows_tournament_id", ["tournament_id", "key"]
        )


def downgrade() -> None:
    with op.batch_alter_table("imported_rows", schema=None) as batch_op:
        batch_op.drop_constraint("uq_imported_rows_tournament_id", type_="unique")
        batch_op.create_unique_constraint("uq_imported_rows_batch_id", ["batch_id", "key"])
