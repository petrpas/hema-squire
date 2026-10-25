"""a tournament's cover may wear a photo, and red joins the cover tints

Revision ID: a7c1d2e3f4b5
Revises: f6b9c3d4e5a7
Create Date: 2026-10-25 00:00:00.000000

Adds `tournaments.cover_photo_bytes` and `tournaments.cover_photo_mime` (spec
tournament-admin, The cover photo is stored bounded and bare). `cover_tint`
needs no data change: every stored value stays valid, and the column is wide
enough for `red` and `photo`. The downgrade returns either of those to null,
which follows the logo, since the older code knows neither.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7c1d2e3f4b5"
down_revision: str | Sequence[str] | None = "f6b9c3d4e5a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("tournaments") as batch_op:
        batch_op.add_column(sa.Column("cover_photo_bytes", sa.LargeBinary(), nullable=True))
        batch_op.add_column(sa.Column("cover_photo_mime", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.execute("UPDATE tournaments SET cover_tint = NULL WHERE cover_tint IN ('red', 'photo')")
    with op.batch_alter_table("tournaments") as batch_op:
        batch_op.drop_column("cover_photo_mime")
        batch_op.drop_column("cover_photo_bytes")
