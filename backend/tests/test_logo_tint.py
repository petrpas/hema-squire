"""A logo's hue band (spec tournament-admin, A logo's hue band is recorded on
upload): saturated opaque pixels vote by band, the ground and lettering do
not, and a logo with too little color has no band."""

import io

from PIL import Image, ImageDraw

from app.logo_tint import logo_hue_band
from app.models import Tournament


def shield(color: tuple[int, int, int], ground: tuple[int, int, int, int]) -> Image.Image:
    image = Image.new("RGBA", (200, 200), ground)
    ImageDraw.Draw(image).ellipse((20, 20, 180, 180), fill=(*color, 255))
    return image


def test_green_shield_on_transparent_is_green():
    assert logo_hue_band(shield((40, 150, 60), (0, 0, 0, 0))) == "green"


def test_red_on_white_is_warm():
    assert logo_hue_band(shield((200, 30, 40), (255, 255, 255, 255))) == "warm"


def test_blue_is_blue():
    assert logo_hue_band(shield((30, 70, 180), (255, 255, 255, 255))) == "blue"


def test_black_on_white_has_no_band():
    assert logo_hue_band(shield((20, 20, 20), (255, 255, 255, 255))) is None


def test_a_small_colored_mark_among_lettering_does_not_decide():
    image = Image.new("RGBA", (200, 200), (255, 255, 255, 255))
    ImageDraw.Draw(image).rectangle((20, 60, 180, 140), fill=(20, 20, 20, 255))
    ImageDraw.Draw(image).rectangle((0, 0, 10, 10), fill=(200, 30, 40, 255))
    assert logo_hue_band(image) is None


def test_a_grey_ground_does_not_dilute_the_color():
    """A logo drawn on a light grey field — the field is the logo's ground,
    not its content, however much of the image it covers."""
    image = Image.new("RGBA", (200, 200), (225, 225, 225, 255))
    ImageDraw.Draw(image).rectangle((90, 40, 110, 160), fill=(200, 30, 40, 255))
    assert logo_hue_band(image) == "warm"


def png(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_upload_records_the_band_and_delete_clears_it(client, auth_headers, engine):
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    organizer = auth_headers()
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2030-01-01"},
        headers=organizer,
    )
    upload = client.post(
        "/api/tournaments/cup/logo",
        files={"file": ("logo.png", png(shield((40, 150, 60), (0, 0, 0, 0))), "image/png")},
        headers=organizer,
    )
    assert upload.status_code == 200, upload.text

    def band() -> str | None:
        with Session(engine) as session:
            return (
                session.scalars(select(Tournament).where(Tournament.slug == "cup")).one().logo_tint
            )

    assert band() == "green"
    client.delete("/api/tournaments/cup/logo", headers=organizer)
    assert band() is None


def test_the_chosen_cover_tint_outlives_the_logo_and_null_returns_to_it(
    client, auth_headers, engine
):
    """spec tournament-admin, The organizer chooses the cover tint."""
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    organizer = auth_headers()
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2030-01-01"},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/cup/logo",
        files={"file": ("logo.png", png(shield((40, 150, 60), (0, 0, 0, 0))), "image/png")},
        headers=organizer,
    )
    chosen = client.patch("/api/tournaments/cup", json={"cover_tint": "blue"}, headers=organizer)
    assert chosen.status_code == 200, chosen.text
    assert (chosen.json()["cover_tint"], chosen.json()["logo_tint"]) == ("blue", "green")

    def stored() -> tuple[str | None, str | None]:
        with Session(engine) as session:
            tournament = session.scalars(select(Tournament).where(Tournament.slug == "cup")).one()
            return tournament.cover_tint, tournament.logo_tint

    client.delete("/api/tournaments/cup/logo", headers=organizer)
    assert stored() == ("blue", None)

    client.patch("/api/tournaments/cup", json={"cover_tint": None}, headers=organizer)
    assert stored() == (None, None)
