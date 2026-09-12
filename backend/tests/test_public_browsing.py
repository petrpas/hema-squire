"""Spec `public-browsing` — what a visitor with no account may read.

The list and a tournament's fencer-facing detail answer without a credential;
a credential that was presented and rejected is still refused; and the payload
an anonymous request gets back carries no claim about an account that does not
exist.
"""

from datetime import timedelta

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.auth import create_token, current_fencer, optional_fencer
from app.config import settings
from app.models import Fencer, Role
from tests.conftest import publish, today_utc

# a valid account number, so the PATCH that sets it actually takes
IBAN = "CZ6508000000192000145399"


def make_published(client, organizer, slug, **overrides):
    """A setup-complete, published tournament — the shape every public read in
    this module is asserted against."""
    payload = {
        "slug": slug,
        "display_name": slug.title(),
        "date": str(today_utc() + timedelta(days=30)),
    }
    payload.update({k: v for k, v in overrides.items() if k in ("slug", "display_name", "date")})
    client.post("/api/tournaments", json=payload, headers=organizer)
    patch = {"location": "Brno", "organizers": [{"name": "Org", "link": None}]}
    patch.update({k: v for k, v in overrides.items() if k not in ("slug", "display_name", "date")})
    client.patch(f"/api/tournaments/{slug}", json=patch, headers=organizer)
    client.post(
        f"/api/tournaments/{slug}/disciplines",
        json={"slug": "LS", "weapon": "LS", "capacity": 8, "fee": 800},
        headers=organizer,
    )
    publish(client, organizer, slug)


def bearer(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


# --- the dependency itself (task 1.1) ---------------------------------------


def test_optional_fencer_is_none_without_a_credential(engine):
    with Session(engine) as session:
        assert optional_fencer(None, session) is None


def test_optional_fencer_resolves_a_good_credential(engine):
    with Session(engine) as session:
        fencer = Fencer(
            email="anon@example.com",
            display_name="Anon",
            password_hash="x",
            role=Role.FENCER,
        )
        session.add(fencer)
        session.commit()
        resolved = optional_fencer(bearer(create_token(fencer)), session)
        assert resolved is not None
        assert resolved.id == fencer.id


def test_optional_fencer_refuses_a_malformed_credential(engine):
    with Session(engine) as session:
        with pytest.raises(HTTPException) as refused:
            optional_fencer(bearer("not-a-jwt"), session)
        assert refused.value.status_code == 401
        assert refused.value.detail == "invalid_token"


def test_optional_fencer_refuses_a_token_whose_account_is_gone(engine):
    """The one case that would be silently downgraded by a dependency that
    treated every failure as anonymity."""
    token = jwt.encode({"sub": "9999"}, settings.secret_key, algorithm="HS256")
    with Session(engine) as session:
        with pytest.raises(HTTPException) as refused:
            optional_fencer(bearer(token), session)
        assert refused.value.status_code == 401
        assert refused.value.detail == "unknown_account"


def test_current_fencer_still_refuses_an_absent_credential(engine):
    with Session(engine) as session:
        with pytest.raises(HTTPException) as refused:
            current_fencer(None, session)
        assert refused.value.status_code == 401
        assert refused.value.detail == "not_authenticated"


# --- the public list scopes (tasks 1.3, 1.4, 1.5) ---------------------------


def test_open_list_answers_without_a_credential(client, auth_headers):
    organizer = auth_headers()
    make_published(client, organizer, "soon", date=str(today_utc() + timedelta(days=10)))
    make_published(client, organizer, "later", date=str(today_utc() + timedelta(days=40)))

    anonymous = client.get("/api/tournaments/open")
    assert anonymous.status_code == 200
    assert [t["slug"] for t in anonymous.json()] == ["soon", "later"]


def test_held_list_answers_without_a_credential(client, auth_headers):
    organizer = auth_headers()
    make_published(client, organizer, "old", date=str(today_utc() - timedelta(days=40)))
    make_published(client, organizer, "recent", date=str(today_utc() - timedelta(days=2)))

    anonymous = client.get("/api/tournaments/held")
    assert anonymous.status_code == 200
    assert [t["slug"] for t in anonymous.json()] == ["recent", "old"]


def test_anonymous_and_unbound_accounts_see_the_same_tournaments(client, auth_headers):
    """Same tournaments, same order — the list is one list (spec
    `fencer-home`, One list for every role)."""
    organizer = auth_headers()
    make_published(client, organizer, "one", date=str(today_utc() + timedelta(days=10)))
    make_published(client, organizer, "two", date=str(today_utc() + timedelta(days=20)))
    fencer = auth_headers(email="f@example.com", name="F", role=Role.FENCER)

    anonymous = [t["slug"] for t in client.get("/api/tournaments/open").json()]
    signed_in = [t["slug"] for t in client.get("/api/tournaments/open", headers=fencer).json()]
    assert anonymous == signed_in == ["one", "two"]


def test_anonymous_entry_omits_the_bond_fields(client, auth_headers):
    organizer = auth_headers()
    make_published(client, organizer, "cup")
    fencer = auth_headers(email="f@example.com", name="F", role=Role.FENCER)

    anonymous = client.get("/api/tournaments/open").json()[0]
    assert "my_registration_state" not in anonymous
    assert "organized" not in anonymous

    signed_in = client.get("/api/tournaments/open", headers=fencer).json()[0]
    assert signed_in["my_registration_state"] == "none"
    assert signed_in["organized"] is False

    owner = client.get("/api/tournaments/open", headers=organizer).json()[0]
    assert owner["organized"] is True


def test_anonymous_entry_keeps_every_tournament_field(client, auth_headers):
    """Only the caller's side of the payload drops out; the tournament's own
    fields, counts and queue lengths included, are identical."""
    organizer = auth_headers()
    make_published(client, organizer, "cup")
    fencer = auth_headers(email="f@example.com", name="F", role=Role.FENCER)

    anonymous = client.get("/api/tournaments/open").json()[0]
    signed_in = client.get("/api/tournaments/open", headers=fencer).json()[0]
    bond = {"my_registration_state", "organized"}
    # `server_time` is this response's own instant and differs by construction
    volatile = bond | {"server_time"}
    assert set(signed_in) - set(anonymous) == bond
    assert {k: v for k, v in anonymous.items() if k not in volatile} == {
        k: v for k, v in signed_in.items() if k not in volatile
    }
    assert anonymous["disciplines"] == signed_in["disciplines"]


@pytest.mark.parametrize("scope", ["open", "held"])
def test_a_rejected_credential_is_not_treated_as_anonymous(client, auth_headers, scope):
    organizer = auth_headers()
    make_published(client, organizer, "cup")

    refused = client.get(
        f"/api/tournaments/{scope}", headers={"Authorization": "Bearer not-a-jwt"}
    )
    assert refused.status_code == 401


def test_the_personal_list_still_needs_an_account(client, auth_headers):
    """`/mine` is an account's own list and stays authenticated."""
    organizer = auth_headers()
    make_published(client, organizer, "cup")

    assert client.get("/api/tournaments/mine").status_code == 401
    assert client.get("/api/tournaments/mine", headers=organizer).status_code == 200


def test_a_draft_is_not_in_the_public_list(client, auth_headers):
    organizer = auth_headers()
    client.post(
        "/api/tournaments",
        json={
            "slug": "draft",
            "display_name": "Draft",
            "date": str(today_utc() + timedelta(days=30)),
        },
        headers=organizer,
    )
    assert client.get("/api/tournaments/open").json() == []


def test_a_cancelled_tournament_is_not_in_the_public_list(client, auth_headers):
    organizer = auth_headers()
    make_published(client, organizer, "gone")
    client.post("/api/tournaments/gone/cancel", headers=organizer)
    assert client.get("/api/tournaments/open").json() == []


# --- the fencer-facing detail (tasks 2.3, 2.4, 2.5) -------------------------

# Every key the fencer-facing detail is allowed to carry. Asserted as a set, so
# a field added to `FencerTournamentOut` later fails this test instead of
# quietly becoming public (spec `public-browsing`, The public detail carries no
# organizer's business).
FENCER_DETAIL_KEYS = {
    "slug",
    "display_name",
    "subtitle",
    "has_logo",
    "date",
    "location",
    "description",
    "qualification_open",
    "qualification_criteria",
    "registration_instructions",
    "organizers",
    "disciplines",
    "extra_items",
    "discounts",
    "local_currency",
    "eur_payments_enabled",
    "currency_mode",
    "registration_opens",
    "registration_opens_time",
    "registration_closes",
    "amendments_close",
    "team_composition_deadline",
    "timezone",
    "registration_opens_at",
    "server_time",
    "registrations_kept_by",
    "external_registration_url",
    "feature_schedule",
    "feature_payments",
    "feature_teams",
    "feature_extras",
}

# The organizer's own configuration, named so the test says what it is guarding
# rather than only that a set matched.
WITHHELD_KEYS = {
    "bank_account",
    "fio_token_configured",
    "output_sheet_url",
    "vs_year",
    "vs_series",
    "vs_prefix",
    "vs_series_editable",
    "reservation_validity_days",
    "reminder_day",
    "amount_tolerance_percent",
    "unpaid_list_treatment",
    "hr_category_map",
    "setup_missing",
    "in_app_registrations",
    "owner_id",
    "expiry_grace_hours",
    "refundable_until",
    "seating_deadline",
    "seating_settled_at",
    "deposit_amount",
    "deposit_amount_eur",
    "payment_mode",
}


def test_fencer_detail_answers_without_a_credential(client, auth_headers):
    organizer = auth_headers()
    make_published(client, organizer, "cup")

    answer = client.get("/api/tournaments/cup/public")
    assert answer.status_code == 200
    assert answer.json()["display_name"] == "Cup"


def test_fencer_detail_carries_exactly_the_allowed_fields(client, auth_headers):
    organizer = auth_headers()
    make_published(client, organizer, "cup")
    client.patch("/api/tournaments/cup", json={"bank_account": IBAN}, headers=organizer)

    answer = client.get("/api/tournaments/cup/public").json()
    assert set(answer) == FENCER_DETAIL_KEYS
    assert set(answer) & WITHHELD_KEYS == set()


def test_fencer_detail_withholds_the_bank_account(client, auth_headers):
    """Named on its own because it is the field with the consequence."""
    organizer = auth_headers()
    make_published(client, organizer, "cup")
    client.patch("/api/tournaments/cup", json={"bank_account": IBAN}, headers=organizer)

    answer = client.get("/api/tournaments/cup/public").json()
    assert "bank_account" not in answer
    assert "fio_token_configured" not in answer
    assert IBAN not in str(answer)


def test_fencer_detail_withholds_the_setup_report(client, auth_headers):
    organizer = auth_headers()
    make_published(client, organizer, "cup")
    assert "setup_missing" not in client.get("/api/tournaments/cup/public").json()


@pytest.mark.parametrize("slug", ["draft", "gone", "no-such-tournament"])
def test_fencer_detail_is_not_found_for_what_is_not_public(client, auth_headers, slug):
    """A draft, a cancelled tournament and an unknown slug are one answer, so
    the URL discloses nothing about which tournaments exist."""
    organizer = auth_headers()
    client.post(
        "/api/tournaments",
        json={
            "slug": "draft",
            "display_name": "Draft",
            "date": str(today_utc() + timedelta(days=30)),
        },
        headers=organizer,
    )
    make_published(client, organizer, "gone")
    client.post("/api/tournaments/gone/cancel", headers=organizer)

    refused = client.get(f"/api/tournaments/{slug}/public")
    assert refused.status_code == 404
    assert refused.json()["detail"] == "tournament_not_found"


def test_the_console_detail_needs_console_access(client, auth_headers):
    organizer = auth_headers()
    make_published(client, organizer, "cup")
    outsider = auth_headers(email="f@example.com", name="F", role=Role.FENCER)

    assert client.get("/api/tournaments/cup").status_code == 401
    assert client.get("/api/tournaments/cup", headers=outsider).status_code == 403
    assert client.get("/api/tournaments/cup", headers=organizer).status_code == 200


def test_the_console_detail_still_carries_everything(client, auth_headers):
    """The split takes nothing from the console."""
    organizer = auth_headers()
    make_published(client, organizer, "cup")
    client.patch("/api/tournaments/cup", json={"bank_account": IBAN}, headers=organizer)

    answer = client.get("/api/tournaments/cup", headers=organizer).json()
    assert answer["bank_account"] == IBAN
    assert answer["setup_missing"] == []
    assert answer["fio_token_configured"] is False


# --- the organizer's index is not public ------------------------------------


def test_the_picker_index_needs_a_credential(client, auth_headers):
    organizer = auth_headers()
    make_published(client, organizer, "cup")

    assert client.get("/api/tournaments").status_code == 401
    listed = client.get("/api/tournaments", headers=organizer)
    assert listed.status_code == 200
    assert [t["slug"] for t in listed.json()] == ["cup"]


def test_the_index_hands_out_no_draft_and_no_bank_account(client, auth_headers):
    """The reason the index is gated, stated as the thing it must not do."""
    organizer = auth_headers()
    client.post(
        "/api/tournaments",
        json={
            "slug": "draft",
            "display_name": "Draft",
            "date": str(today_utc() + timedelta(days=30)),
        },
        headers=organizer,
    )
    client.patch("/api/tournaments/draft", json={"bank_account": IBAN}, headers=organizer)

    for path in ("/api/tournaments", "/api/tournaments/draft", "/api/tournaments/draft/public"):
        answer = client.get(path)
        assert answer.status_code in (401, 404), path
        assert IBAN not in answer.text, path
        assert "Draft" not in answer.text, path

    # and the organizer still sees their own draft in the picker
    assert [t["slug"] for t in client.get("/api/tournaments", headers=organizer).json()] == [
        "draft"
    ]
