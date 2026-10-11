"""a tournament's logo records its hue band, for the card's cover tint

Revision ID: d4f7a9c1e2b3
Revises: c3e8f1a2b4d6
Create Date: 2026-10-11 00:00:00.000000

Adds `tournaments.logo_tint` (spec tournament-admin, A logo's hue band is
recorded on upload) and derives it once for every logo already stored. The
band function is copied here rather than imported from `app`: a migration
must keep meaning what it meant when it was written, whatever later becomes
of the application's own copy.
"""

import colorsys
import io
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from PIL import Image

# revision identifiers, used by Alembic.
revision: str = "d4f7a9c1e2b3"
down_revision: str | Sequence[str] | None = "c3e8f1a2b4d6"
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
    opaque = colored = 0
    for pixel in sample.get_flattened_data():
        if not isinstance(pixel, tuple):
            continue
        red, green, blue, alpha = pixel
        if alpha < 128:
            continue
        opaque += 1
        hue, saturation, value = colorsys.rgb_to_hsv(red / 255, green / 255, blue / 255)
        if saturation < 0.25 or not 0.2 <= value <= 0.97:
            continue
        colored += 1
        weights[_band(hue * 360)] += saturation
    if opaque == 0 or colored / opaque < 0.1:
        return None
    return max(weights, key=lambda band: weights[band])


def upgrade() -> None:
    with op.batch_alter_table("tournaments", schema=None) as batch_op:
        batch_op.add_column(sa.Column("logo_tint", sa.String(length=10), nullable=True))

    connection = op.get_bind()
    rows = connection.execute(
        sa.text("SELECT id, logo_bytes FROM tournaments WHERE logo_bytes IS NOT NULL")
    ).all()
    for tournament_id, logo in rows:
        try:
            band = _logo_hue_band(Image.open(io.BytesIO(logo)))
        except OSError:
            # a stored logo that no longer decodes keeps no band, and its
            # card falls back to the slug as before
            continue
        if band is not None:
            connection.execute(
                sa.text("UPDATE tournaments SET logo_tint = :band WHERE id = :id"),
                {"band": band, "id": tournament_id},
            )


def downgrade() -> None:
    with op.batch_alter_table("tournaments", schema=None) as batch_op:
        batch_op.drop_column("logo_tint")
