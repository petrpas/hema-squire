"""an organizer may choose a tournament's cover tint, and a logo's band no
longer counts the logo's ground

Revision ID: f6b9c3d4e5a7
Revises: e5a8b2d3f4c6
Create Date: 2026-10-11 00:00:00.000000

Adds `tournaments.cover_tint` (spec tournament-admin, The organizer chooses
the cover tint), null for every existing tournament, which keeps following its
logo. Re-derives `logo_tint` for every stored logo under the corrected rule:
light achromatic pixels are the logo's ground and no longer dilute its colored
share, which had left logos on a grey field without a band. The band function
is copied here rather than imported from `app`, as the previous derivation's
was.
"""

import colorsys
import io
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from PIL import Image

# revision identifiers, used by Alembic.
revision: str = "f6b9c3d4e5a7"
down_revision: str | Sequence[str] | None = "e5a8b2d3f4c6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _band(hue_degrees: float) -> str:
    if 170 <= hue_degrees < 290:
        return "blue"
    if 70 <= hue_degrees < 170:
        return "green"
    return "warm"


def _logo_hue_band(image: Image.Image) -> str | None:
    sample = image.convert("RGBA")
    sample.thumbnail((32, 32))
    weights = {"blue": 0.0, "green": 0.0, "warm": 0.0}
    own = colored = 0
    for pixel in sample.get_flattened_data():
        if not isinstance(pixel, tuple):
            continue
        red, green, blue, alpha = pixel
        if alpha < 128:
            continue
        hue, saturation, value = colorsys.rgb_to_hsv(red / 255, green / 255, blue / 255)
        if saturation < 0.25 and value >= 0.7:
            continue
        own += 1
        if saturation < 0.25 or not 0.2 <= value <= 0.97:
            continue
        colored += 1
        weights[_band(hue * 360)] += saturation
    if own == 0 or colored / own < 0.1:
        return None
    return max(weights, key=lambda band: weights[band])


def upgrade() -> None:
    with op.batch_alter_table("tournaments", schema=None) as batch_op:
        batch_op.add_column(sa.Column("cover_tint", sa.String(length=10), nullable=True))

    connection = op.get_bind()
    rows = connection.execute(
        sa.text("SELECT id, logo_bytes FROM tournaments WHERE logo_bytes IS NOT NULL")
    ).all()
    for tournament_id, logo in rows:
        try:
            band = _logo_hue_band(Image.open(io.BytesIO(logo)))
        except OSError:
            # a stored logo that no longer decodes keeps the band it has
            continue
        connection.execute(
            sa.text("UPDATE tournaments SET logo_tint = :band WHERE id = :id"),
            {"band": band, "id": tournament_id},
        )


def downgrade() -> None:
    # the re-derived bands stay: the earlier rule's answers are not kept, and
    # a band read under the corrected rule is no worse a choice of tint
    with op.batch_alter_table("tournaments", schema=None) as batch_op:
        batch_op.drop_column("cover_tint")
