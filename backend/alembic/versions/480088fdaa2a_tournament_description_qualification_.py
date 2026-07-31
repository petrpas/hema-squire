"""tournament description, qualification, and organizers with links

Revision ID: 480088fdaa2a
Revises: b4d9c1e07a52
Create Date: 2026-07-29 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import column, table

# revision identifiers, used by Alembic.
revision: str = '480088fdaa2a'
down_revision: Union[str, Sequence[str], None] = 'b4d9c1e07a52'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add description and qualification fields, and rewrite organizer_names
    (list of strings) into organizers (list of {name, link})."""
    with op.batch_alter_table('tournaments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('description', sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column(
                'qualification_open', sa.Boolean(), nullable=False, server_default=sa.true()
            )
        )
        batch_op.add_column(sa.Column('qualification_criteria', sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column('organizers', sa.JSON(), nullable=False, server_default='[]')
        )

    conn = op.get_bind()
    tournaments = table(
        'tournaments',
        column('id', sa.Integer),
        column('organizer_names', sa.JSON),
        column('organizers', sa.JSON),
    )
    rows = conn.execute(sa.select(tournaments.c.id, tournaments.c.organizer_names)).fetchall()
    for row in rows:
        organizers = [{'name': name, 'link': None} for name in (row.organizer_names or [])]
        conn.execute(
            tournaments.update().where(tournaments.c.id == row.id).values(organizers=organizers)
        )

    with op.batch_alter_table('tournaments', schema=None) as batch_op:
        batch_op.drop_column('organizer_names')
        batch_op.alter_column('qualification_open', server_default=None)
        batch_op.alter_column('organizers', server_default=None)


def downgrade() -> None:
    """Restore organizer_names from organizers, keeping each entry's name and
    losing only the link."""
    with op.batch_alter_table('tournaments', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('organizer_names', sa.JSON(), nullable=False, server_default='[]')
        )

    conn = op.get_bind()
    tournaments = table(
        'tournaments',
        column('id', sa.Integer),
        column('organizer_names', sa.JSON),
        column('organizers', sa.JSON),
    )
    rows = conn.execute(sa.select(tournaments.c.id, tournaments.c.organizers)).fetchall()
    for row in rows:
        names = [
            (entry.get('name') if isinstance(entry, dict) else entry)
            for entry in (row.organizers or [])
        ]
        conn.execute(
            tournaments.update()
            .where(tournaments.c.id == row.id)
            .values(organizer_names=names)
        )

    with op.batch_alter_table('tournaments', schema=None) as batch_op:
        batch_op.drop_column('organizers')
        batch_op.drop_column('qualification_criteria')
        batch_op.drop_column('qualification_open')
        batch_op.drop_column('description')
        batch_op.alter_column('organizer_names', server_default=None)
