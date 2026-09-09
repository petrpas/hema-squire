"""the amendment rule kind stops being about disciplines alone

Revision ID: c4f2a91b7e30
Revises: b3d90a1f5c47
Create Date: 2026-09-06 00:00:00.000000

`discipline_amendment` becomes `registration_amendment`, carrying the field it
amends — the disciplines, or what the row borrows. Rules are replayed by kind,
so a stored rule left under the old name would simply stop being applied: the
registration would keep the total the amendment gave it with nothing in the
table saying why, and the manual-edits log would lose the entry that could
undo it.

Data only. `rules.kind` is a string column and its shape does not change.

The rule journal is left exactly as it was written. It records what happened at
the time it happened, and an entry saying a `discipline_amendment` was created
is a true statement about a day when that is what the kind was called.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4f2a91b7e30"
down_revision: str | Sequence[str] | None = "b3d90a1f5c47"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "UPDATE rules SET kind = 'registration_amendment' WHERE kind = 'discipline_amendment'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE rules SET kind = 'discipline_amendment' WHERE kind = 'registration_amendment'"
    )
