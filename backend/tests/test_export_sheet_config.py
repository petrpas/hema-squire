"""The export's configuration as the console reads it: whether this server
holds Google credentials, and the address they act as (spec data-export, The
console states the export's service account)."""

import json

from app.config import settings

UNCONFIGURED = {"configured": False, "service_account": None, "output_sheet_url": None}


def draft(client, auth_headers):
    """A tournament that has not been published. The configuration read is not
    gated on publication, which is the point of several of these."""
    organizer = auth_headers()
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    return organizer


def credentials(tmp_path, name="creds.json", email="squire@proj.iam.gserviceaccount.com"):
    path = tmp_path / name
    path.write_text(json.dumps({"type": "service_account", "client_email": email}))
    return str(path)


def config(client, headers, expect=200):
    response = client.get("/api/tournaments/cup/export/sheet-config", headers=headers)
    assert response.status_code == expect, response.text
    return response.json()


def test_configured_server_states_its_service_account(client, auth_headers, tmp_path, monkeypatch):
    organizer = draft(client, auth_headers)
    monkeypatch.setattr(settings, "google_credentials_path", credentials(tmp_path))

    assert config(client, organizer) == {
        "configured": True,
        "service_account": "squire@proj.iam.gserviceaccount.com",
        "output_sheet_url": None,
    }


def test_without_credentials_nothing_is_configured(client, auth_headers, monkeypatch):
    organizer = draft(client, auth_headers)
    monkeypatch.setattr(settings, "google_credentials_path", "")

    assert config(client, organizer) == UNCONFIGURED


def test_an_unreadable_credentials_file_reads_as_unconfigured(
    client, auth_headers, tmp_path, monkeypatch
):
    """A malformed or absent file is the same state as no credentials: the
    console offers no export and says so, rather than answering 500 to a read
    the organizer cannot act on."""
    organizer = draft(client, auth_headers)
    broken = tmp_path / "broken.json"
    broken.write_text("{not json")
    monkeypatch.setattr(settings, "google_credentials_path", str(broken))
    assert config(client, organizer) == UNCONFIGURED

    monkeypatch.setattr(settings, "google_credentials_path", str(tmp_path / "absent.json"))
    assert config(client, organizer) == UNCONFIGURED


def test_a_credentials_file_without_an_address_is_not_configured(
    client, auth_headers, tmp_path, monkeypatch
):
    path = tmp_path / "keyless.json"
    path.write_text(json.dumps({"type": "service_account"}))
    organizer = draft(client, auth_headers)
    monkeypatch.setattr(settings, "google_credentials_path", str(path))

    assert config(client, organizer) == UNCONFIGURED


def test_the_address_is_not_offered_without_console_access(
    client, auth_headers, tmp_path, monkeypatch
):
    draft(client, auth_headers)
    monkeypatch.setattr(settings, "google_credentials_path", credentials(tmp_path))
    stranger = auth_headers(email="nobody@example.com", name="Nobody")

    config(client, stranger, expect=403)


def test_a_draft_states_its_configuration(client, auth_headers, tmp_path, monkeypatch):
    """Naming the destination is preparation, and it is done before the
    tournament is published — unlike the export itself, which publication
    gates."""
    organizer = draft(client, auth_headers)
    monkeypatch.setattr(settings, "google_credentials_path", credentials(tmp_path))

    assert config(client, organizer)["configured"] is True
    refused = client.post("/api/tournaments/cup/export/sheet", headers=organizer)
    assert refused.status_code == 409, refused.text


def test_the_destination_travels_with_the_configuration(
    client, auth_headers, tmp_path, monkeypatch
):
    """The Export rail is mounted inside the export band, which carries no
    tournament detail: the destination it states as a link comes from this one
    read rather than from a second."""
    organizer = draft(client, auth_headers)
    monkeypatch.setattr(settings, "google_credentials_path", credentials(tmp_path))
    client.patch(
        "/api/tournaments/cup",
        json={"output_sheet_url": "https://docs.google.com/spreadsheets/d/abc"},
        headers=organizer,
    )

    assert config(client, organizer)["output_sheet_url"] == (
        "https://docs.google.com/spreadsheets/d/abc"
    )
