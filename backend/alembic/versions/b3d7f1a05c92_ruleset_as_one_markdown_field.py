"""ruleset as one markdown field

Revision ID: b3d7f1a05c92
Revises: c8f5a2e17b30
Create Date: 2026-08-27 00:00:00.000000

A discipline's ruleset was a short name plus one optional URL, which could point
at the rules in a single language. It becomes one inline-markdown field
(`organizer-prose`), so an organizer can link the rules in as many languages as
they publish them in.

The existing pair is folded into markdown before the URL column is dropped: a
name with a link becomes `[name](url)`, a link with no name becomes the link as
its own label, and a name with no link is already what it needs to be. Only then
is `ruleset_name` renamed and `ruleset_url` dropped, so nothing an organizer
typed is lost. The downgrade splits an exact `[label](url)` value back into the
two columns and leaves anything else as the name — best-effort, as a downgrade
past a widening always is.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3d7f1a05c92"
down_revision: str | Sequence[str] | None = "c8f5a2e17b30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "UPDATE disciplines SET ruleset_name = '[' || ruleset_name || '](' "
            "|| ruleset_url || ')' "
            "WHERE ruleset_url IS NOT NULL AND ruleset_url <> '' "
            "AND ruleset_name IS NOT NULL AND ruleset_name <> ''"
        )
    )
    conn.execute(
        sa.text(
            "UPDATE disciplines SET ruleset_name = ruleset_url "
            "WHERE ruleset_url IS NOT NULL AND ruleset_url <> '' "
            "AND (ruleset_name IS NULL OR ruleset_name = '')"
        )
    )

    with op.batch_alter_table("disciplines", schema=None) as batch_op:
        batch_op.alter_column(
            "ruleset_name",
            new_column_name="ruleset",
            existing_type=sa.String(length=100),
            type_=sa.String(length=500),
            existing_nullable=True,
        )
        batch_op.drop_column("ruleset_url")


def downgrade() -> None:
    with op.batch_alter_table("disciplines", schema=None) as batch_op:
        batch_op.add_column(sa.Column("ruleset_url", sa.String(length=500), nullable=True))
        batch_op.alter_column(
            "ruleset",
            new_column_name="ruleset_name",
            existing_type=sa.String(length=500),
            type_=sa.String(length=100),
            existing_nullable=True,
        )

    # only a value that is exactly one markdown link splits cleanly back apart
    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT id, ruleset_name FROM disciplines WHERE ruleset_name LIKE '[%](%)'")
    ).fetchall()
    for discipline_id, value in rows:
        label, _, rest = value[1:].partition("](")
        if not rest.endswith(")") or "](" in rest[:-1]:
            continue
        conn.execute(
            sa.text(
                "UPDATE disciplines SET ruleset_name = :name, ruleset_url = :url "
                "WHERE id = :id"
            ),
            {"name": label[:100], "url": rest[:-1][:500], "id": discipline_id},
        )
