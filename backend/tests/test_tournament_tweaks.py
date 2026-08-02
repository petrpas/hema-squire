"""Tests for tournament subtitle/logo and discipline/extra descriptive fields
added by the tournament-layout-tweaks change."""

import io

from PIL import Image

from tests.test_tournaments import make_tournament


def _png_bytes(size=(40, 40), color=(10, 20, 30, 255)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGBA", size, color).save(buffer, format="PNG")
    return buffer.getvalue()


def _jpeg_bytes(size=(3000, 2000), color=(200, 60, 40)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format="JPEG", quality=95)
    return buffer.getvalue()


def test_subtitle_round_trip_and_default_absent(client, auth_headers):
    headers = auth_headers()
    created = make_tournament(client, headers)
    # absent by default, and flagged as having no logo
    assert created["subtitle"] is None
    assert created["has_logo"] is False

    patch = {"subtitle": "A long descriptive subtitle, longer than the name itself"}
    response = client.patch("/api/tournaments/na-duel-2026", json=patch, headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["subtitle"] == patch["subtitle"]

    detail = client.get("/api/tournaments/na-duel-2026", headers=headers)
    assert detail.json()["subtitle"] == patch["subtitle"]


def test_discipline_schedule_and_ruleset_round_trip(client, auth_headers):
    headers = auth_headers()
    make_tournament(client, headers)
    body = {
        "slug": "LS",
        "weapon": "LS",
        "capacity": 32,
        "fee": 300,
        "schedule_when": "Saturday",
        "schedule_where": "Main Hall — Kurtzstrasse 21",
        "ruleset_name": "Right of Way",
        "ruleset_url": "https://example.org/ruleset.pdf",
    }
    response = client.post(
        "/api/tournaments/na-duel-2026/disciplines", json=body, headers=headers
    )
    assert response.status_code == 201, response.text
    out = response.json()
    assert out["schedule_when"] == "Saturday"
    assert out["schedule_where"] == "Main Hall — Kurtzstrasse 21"
    assert out["ruleset_name"] == "Right of Way"
    assert out["ruleset_url"] == "https://example.org/ruleset.pdf"

    # empty fields on a second discipline stay null
    plain = client.post(
        "/api/tournaments/na-duel-2026/disciplines",
        json={"slug": "SA", "weapon": "SA", "capacity": 16, "fee": 200},
        headers=headers,
    )
    assert plain.status_code == 201, plain.text
    assert plain.json()["schedule_when"] is None
    assert plain.json()["ruleset_name"] is None


def test_extra_item_descriptive_fields_do_not_change_price(client, auth_headers):
    headers = auth_headers()
    make_tournament(client, headers)
    client.post(
        "/api/tournaments/na-duel-2026/disciplines",
        json={"slug": "LS", "weapon": "LS", "capacity": 32, "fee": 300},
        headers=headers,
    )
    item = client.post(
        "/api/tournaments/na-duel-2026/extra-items",
        json={
            "name": "Saturday seminar",
            "category": "seminar",
            "price": 150,
            "max_qty": 1,
            "schedule_when": "Saturday 09:00",
            "schedule_where": "Room B",
            "remark": "Bring your own mask",
        },
        headers=headers,
    )
    assert item.status_code == 201, item.text
    body = item.json()
    assert body["schedule_when"] == "Saturday 09:00"
    assert body["remark"] == "Bring your own mask"

    preview = client.post(
        "/api/tournaments/na-duel-2026/price-preview",
        json={"disciplines": ["LS"], "extras": [{"extra_item_id": body["id"], "qty": 1}]},
        headers=headers,
    )
    assert preview.status_code == 200, preview.text
    # 300 (discipline) + 150 (seminar); descriptive fields do not affect it
    assert preview.json()["total"] == 450


def test_logo_upload_serve_and_delete(client, auth_headers):
    headers = auth_headers()
    make_tournament(client, headers)

    upload = client.post(
        "/api/tournaments/na-duel-2026/logo",
        files={"file": ("logo.png", _png_bytes(), "image/png")},
        headers=headers,
    )
    assert upload.status_code == 200, upload.text
    assert upload.json()["has_logo"] is True

    served = client.get("/api/tournaments/na-duel-2026/logo")
    assert served.status_code == 200
    assert served.headers["content-type"] == "image/png"
    # re-encoded to a valid PNG
    Image.open(io.BytesIO(served.content)).verify()

    deleted = client.delete("/api/tournaments/na-duel-2026/logo", headers=headers)
    assert deleted.status_code == 204
    assert client.get("/api/tournaments/na-duel-2026/logo").status_code == 404


def test_logo_upload_accepts_multi_megapixel_jpeg(client, auth_headers):
    headers = auth_headers()
    make_tournament(client, headers)
    response = client.post(
        "/api/tournaments/na-duel-2026/logo",
        files={"file": ("photo.jpg", _jpeg_bytes(), "image/jpeg")},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["has_logo"] is True


def test_logo_upload_rejects_oversized(client, auth_headers):
    headers = auth_headers()
    make_tournament(client, headers)
    too_big = b"\x89PNG\r\n\x1a\n" + b"0" * (8 * 1024 * 1024 + 1)
    response = client.post(
        "/api/tournaments/na-duel-2026/logo",
        files={"file": ("logo.png", too_big, "image/png")},
        headers=headers,
    )
    assert response.status_code == 413
    assert response.json()["detail"] == "logo_too_large"


def test_logo_upload_rejects_non_image(client, auth_headers):
    headers = auth_headers()
    make_tournament(client, headers)
    response = client.post(
        "/api/tournaments/na-duel-2026/logo",
        files={"file": ("note.txt", b"not an image", "text/plain")},
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "logo_not_an_image"
