"""Which of the three cover tints a tournament's logo belongs with (spec
tournament-admin, A logo's hue band is recorded on upload).

The answer is a hue *band*, never a color: the card renders one of its three
pastel tokens and nothing taken from the logo itself, so the palette stays
the one in tokens.css."""

import colorsys
from typing import Literal

from PIL import Image

LogoBand = Literal["blue", "green", "warm"]

# The cover tints an organizer may choose outright, overriding the band; null
# follows the logo (spec tournament-admin, The organizer chooses the cover
# ground). Named for the tint rendered, where the band is named for the hue
# read. Red is only ever chosen: no band and no slug gives it.
CoverTint = Literal["blue", "green", "yellow", "red"]
# what the cover's band stands on: one of the tints, or the organizer's cover
# photo, which may be chosen only while one is stored
CoverGround = Literal[CoverTint, "photo"]

# a pixel votes only when it carries a color: transparent, grey, near-white
# and near-black pixels are the logo's ground and lettering, not its color
_MIN_ALPHA = 128
_MIN_SATURATION = 0.25
_MIN_VALUE = 0.2
_MAX_VALUE = 0.97
# a light pixel with no color is the logo's ground — a white or grey field,
# often textured — and is not counted at all: a logo drawn on a grey card is
# no less colored for the card around it
_GROUND_MIN_VALUE = 0.7
# under this share of voting pixels among the logo's own pixels (opaque, and
# not ground) the logo is achromatic, and the card falls back to the slug
_MIN_COLORED_SHARE = 0.1
_SAMPLE = 32


def _band(hue_degrees: float) -> LogoBand:
    if 170 <= hue_degrees < 290:
        return "blue"
    if 70 <= hue_degrees < 170:
        return "green"
    # magenta, pink, red, orange and yellow
    return "warm"


def logo_hue_band(image: Image.Image) -> LogoBand | None:
    """The band the logo's saturated pixels vote for, each weighted by its
    saturation, or None where too few of the logo's own pixels carry a
    color."""
    sample = image.convert("RGBA")
    sample.thumbnail((_SAMPLE, _SAMPLE))
    weights: dict[LogoBand, float] = {"blue": 0.0, "green": 0.0, "warm": 0.0}
    opaque = colored = 0
    for pixel in sample.get_flattened_data():
        # an RGBA image yields 4-tuples; PIL's stubs also admit the scalar
        # pixels of single-band modes, which a converted image never has
        if not isinstance(pixel, tuple):
            continue
        red, green, blue, alpha = pixel
        if alpha < _MIN_ALPHA:
            continue
        hue, saturation, value = colorsys.rgb_to_hsv(red / 255, green / 255, blue / 255)
        if saturation < _MIN_SATURATION and value >= _GROUND_MIN_VALUE:
            continue
        opaque += 1
        if saturation < _MIN_SATURATION or not _MIN_VALUE <= value <= _MAX_VALUE:
            continue
        colored += 1
        weights[_band(hue * 360)] += saturation
    if opaque == 0 or colored / opaque < _MIN_COLORED_SHARE:
        return None
    return max(weights, key=lambda band: weights[band])
