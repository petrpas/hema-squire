"""API-level tests for the `bank_account` field: acceptance of either input
form, normalization to a canonical IBAN, and checksum rejection (design
`accept-czech-account-format`)."""

CZ_IBAN = "CZ6508000000192000145399"
CZ_DOMESTIC = "19-2000145399/0800"


def make_tournament(client, organizer, slug="cup"):
    client.post(
        "/api/tournaments",
        json={"slug": slug, "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    return slug


def test_domestic_account_is_stored_as_iban(client, auth_headers):
    organizer = auth_headers()
    slug = make_tournament(client, organizer)
    response = client.patch(
        f"/api/tournaments/{slug}", json={"bank_account": CZ_DOMESTIC}, headers=organizer
    )
    assert response.status_code == 200, response.text
    assert response.json()["bank_account"] == CZ_IBAN


def test_valid_iban_is_stored_unchanged(client, auth_headers):
    organizer = auth_headers()
    slug = make_tournament(client, organizer)
    response = client.patch(
        f"/api/tournaments/{slug}", json={"bank_account": CZ_IBAN}, headers=organizer
    )
    assert response.status_code == 200, response.text
    assert response.json()["bank_account"] == CZ_IBAN


def test_iban_grouped_with_spaces_is_accepted(client, auth_headers):
    """An IBAN typed as conventionally displayed, grouped in 4s, normalizes
    to the same compact form as the ungrouped input."""
    organizer = auth_headers()
    slug = make_tournament(client, organizer)
    response = client.patch(
        f"/api/tournaments/{slug}",
        json={"bank_account": "CZ65 0800 0000 1920 0014 5399"},
        headers=organizer,
    )
    assert response.status_code == 200, response.text
    assert response.json()["bank_account"] == CZ_IBAN


def test_bad_iban_checksum_refused(client, auth_headers):
    organizer = auth_headers()
    slug = make_tournament(client, organizer)
    response = client.patch(
        f"/api/tournaments/{slug}",
        json={"bank_account": "CZ0008000000192000145399"},
        headers=organizer,
    )
    assert response.status_code == 422
    assert response.json()["detail"] == {
        "errors": [{"field": "bank_account", "code": "iban_checksum", "params": {}}]
    }


def test_bad_account_checksum_refused(client, auth_headers):
    organizer = auth_headers()
    slug = make_tournament(client, organizer)
    response = client.patch(
        f"/api/tournaments/{slug}",
        json={"bank_account": "20-2000145399/0800"},
        headers=organizer,
    )
    assert response.status_code == 422
    assert response.json()["detail"] == {
        "errors": [{"field": "bank_account", "code": "account_checksum", "params": {}}]
    }


def test_both_forms_of_one_account_normalize_identically(client, auth_headers):
    organizer = auth_headers()
    slug = make_tournament(client, organizer)
    client.patch(f"/api/tournaments/{slug}", json={"bank_account": CZ_DOMESTIC}, headers=organizer)
    from_domestic = client.get(f"/api/tournaments/{slug}", headers=organizer).json()["bank_account"]

    client.patch(f"/api/tournaments/{slug}", json={"bank_account": CZ_IBAN}, headers=organizer)
    from_iban = client.get(f"/api/tournaments/{slug}", headers=organizer).json()["bank_account"]

    assert from_domestic == from_iban == CZ_IBAN


def test_account_stored_before_this_change_is_readable_unvalidated(client, auth_headers, engine):
    """A checksum-invalid value already in the column (stored before this
    validation existed) is neither re-validated nor rejected on read."""
    organizer = auth_headers()
    slug = make_tournament(client, organizer)

    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from app.models import Tournament

    with Session(engine) as session:
        tournament = session.scalar(select(Tournament).where(Tournament.slug == slug))
        tournament.bank_account = "CZ0008000000192000145399"  # bad checksum, written directly
        session.commit()

    response = client.get(f"/api/tournaments/{slug}", headers=organizer)
    assert response.status_code == 200
    assert response.json()["bank_account"] == "CZ0008000000192000145399"
