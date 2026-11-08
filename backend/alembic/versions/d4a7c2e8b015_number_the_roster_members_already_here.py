"""number the roster members that were on a roster before members were numbered

Revision ID: d4a7c2e8b015
Revises: c7f1a3b9e2d4
Create Date: 2026-11-08 00:00:00.000000

A roster member is a row of the fencer list and carries a fixed number, which
`app.roster` now allocates where a member is added. Members added before that
hold none, and the fencer list reads a dash where their number belongs — on a
team tournament that is most of the start field.

So they are numbered here, once, in the order `rownumbers.arrival_order` would
have numbered them: per tournament, by member id, taking the lowest numbers
nothing holds. That matches what an allocation on the day would have produced
for rosters nobody has touched since, which pre-launch is all of them, and it
keeps the one rule the numbers live by — a number nothing holds is free, a
number something holds is never reissued (spec etl-console, Fixed fencer
number).

Irreversible by design: a number, once allocated, is not taken back. The
downgrade therefore drops the rows it added, which is the only sense in which
numbering can be undone — it releases numbers no member would hold under the
old code either.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4a7c2e8b015"
down_revision: str | Sequence[str] | None = "c7f1a3b9e2d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# live and removed alike: a removed member keeps its number, so numbering it
# now is what keeps a restore from minting a second one for the same id
_MEMBERS = sa.text(
    """
    SELECT teams.tournament_id AS tournament_id, team_members.id AS member_id
    FROM team_members
    JOIN teams ON teams.id = team_members.team_id
    ORDER BY teams.tournament_id, team_members.id
    """
)

_TAKEN = sa.text(
    "SELECT tournament_id, row_id, number FROM sheet_row_numbers ORDER BY tournament_id, number"
)

_INSERT = sa.text(
    "INSERT INTO sheet_row_numbers (tournament_id, row_id, number)"
    " VALUES (:tournament_id, :row_id, :number)"
)


def upgrade() -> None:
    connection = op.get_bind()
    taken: dict[int, set[int]] = {}
    held: set[tuple[int, str]] = set()
    for tournament_id, row_id, number in connection.execute(_TAKEN):
        taken.setdefault(tournament_id, set()).add(number)
        held.add((tournament_id, row_id))

    candidates: dict[int, int] = {}
    for tournament_id, member_id in connection.execute(_MEMBERS):
        row_id = f"mem:{member_id}"
        if (tournament_id, row_id) in held:
            continue  # added after the allocation reached the roster diff
        used = taken.setdefault(tournament_id, set())
        number = candidates.get(tournament_id, 1)
        while number in used:
            number += 1
        connection.execute(
            _INSERT,
            {"tournament_id": tournament_id, "row_id": row_id, "number": number},
        )
        used.add(number)
        candidates[tournament_id] = number + 1


def downgrade() -> None:
    op.get_bind().execute(sa.text("DELETE FROM sheet_row_numbers WHERE row_id LIKE 'mem:%'"))
