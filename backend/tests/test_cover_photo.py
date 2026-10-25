"""The cover photo (spec tournament-admin, The cover photo is stored bounded
and bare; The organizer chooses the cover ground): stored upright, bounded and
without metadata, chosen only while stored, and independent of the logo."""

import io

from PIL import Image

LOGO_PNG_SIDE = 40
# EXIF tags: Orientation, and the GPS IFD pointer
ORIENTATION = 0x0112
GPS_IFD = 0x8825


def phone_photo() -> bytes:
    """A 400×300 landscape frame stored sideways, as a phone held upright
    writes it, with an orientation tag saying so and a GPS position."""
    image = Image.new("RGB", (400, 300), (120, 90, 60))
    exif = Image.Exif()
    # 6: rotate 90° clockwise to view — the upright picture is 300×400
    exif[ORIENTATION] = 6
    exif.get_ifd(GPS_IFD)[2] = (50.0, 5.0, 0.0)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", exif=exif)
    return buffer.getvalue()


def big_photo() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (4000, 3000), (30, 60, 90)).save(buffer, format="JPEG")
    return buffer.getvalue()


def logo_png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGBA", (LOGO_PNG_SIDE, LOGO_PNG_SIDE), (40, 150, 60, 255)).save(buffer, "PNG")
    return buffer.getvalue()


def create(client, headers) -> None:
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2030-01-01"},
        headers=headers,
    )


def upload(client, headers, content: bytes, name: str = "photo.jpg"):
    return client.post(
        "/api/tournaments/cup/cover-photo",
        files={"file": (name, content, "image/jpeg")},
        headers=headers,
    )


def test_a_phone_photo_is_stored_upright_and_bare(client, auth_headers):
    organizer = auth_headers()
    create(client, organizer)
    response = upload(client, organizer, phone_photo())
    assert response.status_code == 200, response.text
    assert response.json()["has_cover_photo"] is True

    served = client.get("/api/tournaments/cup/cover-photo")
    assert served.status_code == 200
    assert served.headers["content-type"] == "image/jpeg"
    stored = Image.open(io.BytesIO(served.content))
    assert stored.size == (300, 400)
    assert len(stored.getexif()) == 0
    assert "exif" not in stored.info


def test_a_large_photo_is_bounded_on_its_longer_side(client, auth_headers):
    organizer = auth_headers()
    create(client, organizer)
    assert upload(client, organizer, big_photo()).status_code == 200
    stored = Image.open(io.BytesIO(client.get("/api/tournaments/cup/cover-photo").content))
    assert stored.size == (1600, 1200)


def test_failures_are_named_by_cause(client, auth_headers, monkeypatch):
    from app.routers import tournaments

    organizer = auth_headers()
    create(client, organizer)
    undecodable = upload(client, organizer, b"not an image at all")
    assert (undecodable.status_code, undecodable.json()["detail"]) == (
        422,
        "cover_photo_not_an_image",
    )
    monkeypatch.setattr(tournaments, "LOGO_MAX_UPLOAD_BYTES", 10)
    oversized = upload(client, organizer, big_photo())
    assert (oversized.status_code, oversized.json()["detail"]) == (413, "cover_photo_too_large")


def test_photo_cannot_be_chosen_while_none_is_stored(client, auth_headers):
    organizer = auth_headers()
    create(client, organizer)
    refused = client.patch("/api/tournaments/cup", json={"cover_tint": "photo"}, headers=organizer)
    assert (refused.status_code, refused.json()["detail"]) == (422, "cover_photo_missing")


def test_a_tint_over_a_stored_photo_keeps_it_and_removing_the_worn_photo_follows_the_logo(
    client, auth_headers
):
    organizer = auth_headers()
    create(client, organizer)
    upload(client, organizer, big_photo())
    worn = client.patch("/api/tournaments/cup", json={"cover_tint": "photo"}, headers=organizer)
    assert worn.json()["cover_tint"] == "photo"

    red = client.patch("/api/tournaments/cup", json={"cover_tint": "red"}, headers=organizer)
    assert (red.json()["cover_tint"], red.json()["has_cover_photo"]) == ("red", True)
    back = client.patch("/api/tournaments/cup", json={"cover_tint": "photo"}, headers=organizer)
    assert back.status_code == 200

    assert client.delete("/api/tournaments/cup/cover-photo", headers=organizer).status_code == 204
    detail = client.get("/api/tournaments/cup", headers=organizer).json()
    assert (detail["cover_tint"], detail["has_cover_photo"]) == (None, False)
    assert client.get("/api/tournaments/cup/cover-photo").status_code == 404


def test_removing_a_chosen_tints_photo_keeps_the_tint(client, auth_headers):
    organizer = auth_headers()
    create(client, organizer)
    upload(client, organizer, big_photo())
    client.patch("/api/tournaments/cup", json={"cover_tint": "green"}, headers=organizer)
    client.delete("/api/tournaments/cup/cover-photo", headers=organizer)
    assert client.get("/api/tournaments/cup", headers=organizer).json()["cover_tint"] == "green"


def test_photo_and_logo_are_independent(client, auth_headers):
    organizer = auth_headers()
    create(client, organizer)
    upload(client, organizer, big_photo())
    client.patch("/api/tournaments/cup", json={"cover_tint": "photo"}, headers=organizer)
    client.post(
        "/api/tournaments/cup/logo",
        files={"file": ("logo.png", logo_png(), "image/png")},
        headers=organizer,
    )
    client.delete("/api/tournaments/cup/logo", headers=organizer)
    detail = client.get("/api/tournaments/cup", headers=organizer).json()
    assert (detail["cover_tint"], detail["has_cover_photo"], detail["has_logo"]) == (
        "photo",
        True,
        False,
    )
