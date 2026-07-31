"""Tournament currency: model defaults, save-time invariants, conversion, and
the migration that introduces the columns.

The governing rule is that everything about currency is inert until an organizer
opts in — a tournament that predates the change must price and bill exactly as
it did before.
"""

import datetime
import io
import os
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from app import pricing
from app.db import Base
from app.mail import get_mailer
from app.main import app
from app.models import Currency, Discipline, ExtraCategory, ExtraItem, Tournament
from tests.test_tournaments import make_tournament as make_api_tournament

BACKEND_ROOT = Path(__file__).resolve().parents[1]


class CollectingMailer:
    def __init__(self):
        self.sent = []

    def send(self, message):
        self.sent.append(message)


@pytest.fixture
def mailbox():
    mailer = CollectingMailer()
    app.dependency_overrides[get_mailer] = lambda: mailer
    yield mailer
    app.dependency_overrides.pop(get_mailer, None)


def _import_rows(client, headers, rows):
    header = (
        "ID pohybu;Datum;Objem;Měna;VS;KS;SS;Zpráva pro příjemce;Název protiúčtu;Protiúčet"
    )
    csv = ("meta;data\n\n" + header + "\n" + "\n".join(rows) + "\n").encode()
    return client.post(
        "/api/tournaments/na-duel-2026/payments/import-statement",
        files={"file": ("v.csv", io.BytesIO(csv), "text/csv")},
        headers=headers,
    ).json()


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def make_tournament(**kwargs) -> Tournament:
    defaults = dict(
        slug="na-duel-2026",
        display_name="Na Duel!",
        date=datetime.date(2026, 10, 3),
        vs_year=2026,
        vs_series=1,
    )
    return Tournament(**{**defaults, **kwargs})


# --- 1.6 defaults reproduce pre-change behavior ---------------------------------


def test_tournament_defaults_to_czk_without_eur(session):
    tournament = make_tournament()
    session.add(tournament)
    session.commit()
    session.refresh(tournament)

    assert tournament.primary_currency == Currency.CZK
    assert tournament.eur_payments_enabled is False
    assert tournament.eur_rate is None
    assert tournament.shows_eur is False
    assert tournament.registration_instructions is None


def test_legacy_totals_unchanged_by_currency_columns(session):
    """A pre-itemized tournament's total is the legacy computation, untouched."""
    tournament = make_tournament(weapon_rental_fee=50, afterparty_fee=400)
    longsword = Discipline(
        tournament=tournament, code="LS", name="Longsword Open Steel", capacity=32, fee=500
    )
    session.add(tournament)
    session.commit()

    total = pricing.selection_total(
        tournament,
        disciplines=[longsword],
        extras=[],
        weapon_rentals=["LS"],
        afterparty=True,
        at=datetime.date(2026, 9, 1),
    )
    assert total == 950


def test_extra_item_declares_no_option_by_default(session):
    tournament = make_tournament()
    item = ExtraItem(
        tournament=tournament,
        name="t-shirt",
        category=ExtraCategory.MERCH,
        price=300,
        max_qty=5,
    )
    session.add(tournament)
    session.commit()
    session.refresh(item)

    assert item.option_label is None
    assert item.option_choices == []
    assert item.takes_option is False


# --- 1.5 the migration itself ---------------------------------------------------


def _alembic(db_path: Path, *args: str) -> None:
    """Run alembic against a throwaway SQLite file, out-of-process so the
    revision scripts execute exactly as they will in a deployment."""
    subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_ROOT,
        check=True,
        capture_output=True,
        env=os.environ
        | {
            "HEMA_SQUIRE_DATABASE_URL": f"sqlite:///{db_path}",
            "HEMA_SQUIRE_SCHEDULER_ENABLED": "false",
            "HEMA_SQUIRE_HR_AUTO_REFRESH": "false",
        },
    )


def test_migration_adds_and_drops_currency_columns(tmp_path):
    db_path = tmp_path / "migrate.sqlite"

    _alembic(db_path, "upgrade", "480088fdaa2a")
    engine = create_engine(f"sqlite:///{db_path}")
    before = {c["name"] for c in inspect(engine).get_columns("tournaments")}
    assert "primary_currency" not in before
    engine.dispose()

    _alembic(db_path, "upgrade", "90aeb7ba0f10")
    engine = create_engine(f"sqlite:///{db_path}")
    inspector = inspect(engine)
    tournaments = {c["name"]: c for c in inspector.get_columns("tournaments")}
    assert tournaments["primary_currency"]["nullable"] is False
    assert tournaments["eur_payments_enabled"]["nullable"] is False
    assert tournaments["eur_rate"]["nullable"] is True
    assert "registration_instructions" in tournaments
    items = {c["name"] for c in inspector.get_columns("extra_items")}
    assert {"option_label", "option_choices"} <= items
    selections = {c["name"] for c in inspector.get_columns("registration_extras")}
    assert "option_value" in selections
    engine.dispose()

    _alembic(db_path, "downgrade", "480088fdaa2a")
    engine = create_engine(f"sqlite:///{db_path}")
    after = {c["name"] for c in inspect(engine).get_columns("tournaments")}
    assert "primary_currency" not in after
    assert "registration_instructions" not in after
    engine.dispose()


# --- 2.3 conversion helpers ----------------------------------------------------


def test_to_eur_rounds_half_up_to_cents(session):
    tournament = make_tournament(
        primary_currency=Currency.CZK, eur_payments_enabled=True, eur_rate=Decimal("25.5")
    )
    session.add(tournament)
    session.commit()

    assert tournament.shows_eur is True
    assert pricing.to_eur(1750, tournament) == Decimal("68.63")


def test_to_eur_none_without_a_rate(session):
    tournament = make_tournament()
    session.add(tournament)
    session.commit()

    assert pricing.to_eur(1750, tournament) is None


def test_to_eur_none_for_eur_priced_tournament(session):
    """An EUR tournament's primary figure already is the EUR one."""
    tournament = make_tournament(primary_currency=Currency.EUR, eur_payments_enabled=True)
    session.add(tournament)
    session.commit()

    assert tournament.shows_eur is False
    assert pricing.to_eur(70, tournament) is None


def _patch(client, headers, **fields):
    return client.patch("/api/tournaments/na-duel-2026", json=fields, headers=headers)


# --- 2.2/2.5 save-time invariants through the API ------------------------------


def test_new_tournament_reports_czk_without_eur(client, auth_headers):
    headers = auth_headers()
    created = make_api_tournament(client, headers)

    assert created["primary_currency"] == "CZK"
    assert created["eur_payments_enabled"] is False
    assert created["eur_rate"] is None
    assert created["registration_instructions"] is None


def test_enabling_eur_payments_requires_a_rate(client, auth_headers):
    headers = auth_headers()
    make_api_tournament(client, headers)

    response = _patch(client, headers, eur_payments_enabled=True)
    assert response.status_code == 422
    assert response.json()["detail"] == "eur_rate_required"

    # nothing was stored
    detail = client.get("/api/tournaments/na-duel-2026", headers=headers).json()
    assert detail["eur_payments_enabled"] is False
    assert detail["eur_rate"] is None


def test_eur_payments_with_a_rate_saves(client, auth_headers):
    headers = auth_headers()
    make_api_tournament(client, headers)

    response = _patch(client, headers, eur_payments_enabled=True, eur_rate="25.5")
    assert response.status_code == 200, response.text
    out = response.json()
    assert out["eur_payments_enabled"] is True
    assert Decimal(out["eur_rate"]) == Decimal("25.5")


@pytest.mark.parametrize("rate", ["0", "-1", "-25.5"])
def test_non_positive_rate_rejected(client, auth_headers, rate):
    headers = auth_headers()
    make_api_tournament(client, headers)

    response = _patch(client, headers, eur_payments_enabled=True, eur_rate=rate)
    assert response.status_code == 422


def test_eur_primary_forces_enabled_and_clears_rate(client, auth_headers):
    headers = auth_headers()
    make_api_tournament(client, headers)
    _patch(client, headers, eur_payments_enabled=True, eur_rate="25.5")

    response = _patch(client, headers, primary_currency="EUR")
    assert response.status_code == 200, response.text
    out = response.json()
    assert out["primary_currency"] == "EUR"
    assert out["eur_payments_enabled"] is True
    assert out["eur_rate"] is None


def test_disabling_eur_payments_clears_the_rate(client, auth_headers):
    headers = auth_headers()
    make_api_tournament(client, headers)
    _patch(client, headers, eur_payments_enabled=True, eur_rate="25.5")

    response = _patch(client, headers, eur_payments_enabled=False)
    assert response.status_code == 200, response.text
    out = response.json()
    assert out["eur_payments_enabled"] is False
    assert out["eur_rate"] is None


def test_rate_set_in_a_later_request_than_the_flag(client, auth_headers):
    """The invariant runs on merged state, so the flag cannot be left dangling
    by splitting the change across two requests."""
    headers = auth_headers()
    make_api_tournament(client, headers)

    assert _patch(client, headers, eur_payments_enabled=True).status_code == 422
    assert _patch(client, headers, eur_rate="25.5").status_code == 200
    # the rate alone does not enable EUR payments, and so is cleared again
    detail = client.get("/api/tournaments/na-duel-2026", headers=headers).json()
    assert detail["eur_payments_enabled"] is False
    assert detail["eur_rate"] is None


def test_registration_instructions_round_trip(client, auth_headers):
    headers = auth_headers()
    make_api_tournament(client, headers)
    text = "Zaplať do 10 dnů.\n\nQR kód najdeš v e-mailu."

    response = _patch(client, headers, registration_instructions=text)
    assert response.status_code == 200, response.text
    assert response.json()["registration_instructions"] == text


def test_from_eur_cents_inverts_to_eur(session):
    tournament = make_tournament(
        primary_currency=Currency.CZK, eur_payments_enabled=True, eur_rate=Decimal("25.5")
    )
    session.add(tournament)
    session.commit()

    # 68.63 EUR back into CZK lands within a unit of the original 1750
    converted = pricing.from_eur_cents(6863, tournament)
    assert converted is not None
    assert abs(converted - Decimal(1750)) < Decimal(1)


# --- 4.6/5.3 EUR payment instructions, emails, and matching ---------------------


def publish_with_eur(client, headers, *, eur=True, rate="25.5", fee=1750):
    make_api_tournament(client, headers)
    patch = {
        "location": "Brno",
        "organizers": [{"name": "Org", "link": None}],
        "bank_account": "CZ6508000000192000145399",
    }
    if eur:
        patch |= {"eur_payments_enabled": True, "eur_rate": rate}
    assert client.patch(
        "/api/tournaments/na-duel-2026", json=patch, headers=headers
    ).status_code == 200
    client.post(
        "/api/tournaments/na-duel-2026/disciplines",
        json={"code": "LS", "capacity": 10, "fee": fee},
        headers=headers,
    )


def enroll(client, auth_headers, email="f1@example.com"):
    fencer = auth_headers(email=email, name="F1")
    response = client.post(
        "/api/tournaments/na-duel-2026/register",
        json={"disciplines": ["LS"]},
        headers=fencer,
    )
    assert response.status_code == 201, response.text
    return fencer, response.json()["vs"]


def test_spayd_carries_eur_with_a_decimal_amount():
    from app.spayd import spayd_string

    result = spayd_string(
        "CZ6508000000192000145399", Decimal("68.63"), 1000001, "VS1000001 Cup", currency="EUR"
    )
    assert "AM:68.63" in result
    assert "CC:EUR" in result


def test_payment_instructions_carry_the_eur_pair(client, auth_headers):
    headers = auth_headers()
    publish_with_eur(client, headers)
    fencer, _ = enroll(client, auth_headers)

    data = client.get(
        "/api/tournaments/na-duel-2026/my-registration/payment", headers=fencer
    ).json()
    assert data["amount"] == 1750
    assert data["currency"] == "CZK"
    assert Decimal(data["eur_amount"]) == Decimal("68.63")
    assert "CC:CZK" in data["spayd"]
    assert "CC:EUR" in data["eur_spayd"]
    assert "AM:68.63" in data["eur_spayd"]
    assert data["eur_qr_png_base64"]


def test_payment_instructions_omit_eur_without_eur_payments(client, auth_headers):
    headers = auth_headers()
    publish_with_eur(client, headers, eur=False)
    fencer, _ = enroll(client, auth_headers)

    data = client.get(
        "/api/tournaments/na-duel-2026/my-registration/payment", headers=fencer
    ).json()
    assert data["eur_amount"] is None
    assert data["eur_spayd"] is None
    assert data["eur_qr_png_base64"] is None
    assert "CC:CZK" in data["spayd"]


def test_price_preview_carries_the_eur_equivalent(client, auth_headers):
    headers = auth_headers()
    publish_with_eur(client, headers)
    fencer = auth_headers(email="f2@example.com", name="F2")

    data = client.post(
        "/api/tournaments/na-duel-2026/price-preview",
        json={"disciplines": ["LS"]},
        headers=fencer,
    ).json()
    assert data["total"] == 1750
    assert data["currency"] == "CZK"
    assert Decimal(data["eur_total"]) == Decimal("68.63")


def test_confirmation_email_carries_both_amounts_and_two_qrs(client, auth_headers, mailbox):
    headers = auth_headers()
    publish_with_eur(client, headers)
    enroll(client, auth_headers)

    message = mailbox.sent[-1]
    body = message.get_body(preferencelist=("plain",)).get_content()
    assert "1750 Kč" in body
    # Czech copy uses the decimal comma
    assert "68,63 €" in body
    assert "eurech" in body  # the EUR note pointing at the second QR
    attachments = [part.get_filename() for part in message.iter_attachments()]
    assert attachments == ["platba-qr.png", "platba-qr-eur.png"]


def test_confirmation_email_has_one_qr_without_eur(client, auth_headers, mailbox):
    headers = auth_headers()
    publish_with_eur(client, headers, eur=False)
    enroll(client, auth_headers)

    message = mailbox.sent[-1]
    body = message.get_body(preferencelist=("plain",)).get_content()
    assert "1750 Kč" in body
    assert "€" not in body
    attachments = [part.get_filename() for part in message.iter_attachments()]
    assert attachments == ["platba-qr.png"]


def test_eur_transaction_matches_a_czk_total(client, auth_headers, mailbox):
    headers = auth_headers()
    publish_with_eur(client, headers)
    fencer, vs = enroll(client, auth_headers)

    result = _import_rows(client, headers, [f"1;01.08.2026;68,63;EUR;{vs};;;;MUELLER;DE99"])
    assert result["matched"] == 1
    state = client.get(
        "/api/tournaments/na-duel-2026/my-registration", headers=fencer
    ).json()["state"]
    assert state == "paid"


def test_eur_transaction_without_a_rate_is_flagged_as_unconvertible(
    client, auth_headers, mailbox
):
    headers = auth_headers()
    publish_with_eur(client, headers, eur=False)
    fencer, vs = enroll(client, auth_headers)

    result = _import_rows(client, headers, [f"1;01.08.2026;68,63;EUR;{vs};;;;MUELLER;DE99"])
    assert result["flagged"] == 1
    queue = client.get(
        "/api/tournaments/na-duel-2026/payments/unmatched", headers=headers
    ).json()
    assert queue[0]["status_reason"] == "currency_unconvertible"
    state = client.get(
        "/api/tournaments/na-duel-2026/my-registration", headers=fencer
    ).json()["state"]
    assert state == "reserved"


def test_eur_payment_far_off_still_flags_on_amount(client, auth_headers, mailbox):
    """Conversion happens first, then the existing tolerance rule applies."""
    headers = auth_headers()
    publish_with_eur(client, headers)
    fencer, vs = enroll(client, auth_headers)

    result = _import_rows(client, headers, [f"1;01.08.2026;40,00;EUR;{vs};;;;MUELLER;DE99"])
    assert result["flagged"] == 1
    queue = client.get(
        "/api/tournaments/na-duel-2026/payments/unmatched", headers=headers
    ).json()
    assert queue[0]["status_reason"] == "amount_out_of_tolerance"


def test_same_currency_matching_unchanged(client, auth_headers, mailbox):
    headers = auth_headers()
    publish_with_eur(client, headers, eur=False)
    fencer, vs = enroll(client, auth_headers)

    result = _import_rows(client, headers, [f"1;01.08.2026;1 750,00;CZK;{vs};;;;Jan N;123"])
    assert result["matched"] == 1


def test_open_list_carries_the_primary_currency(client, auth_headers):
    """The fencer-facing list must name the currency, or a EUR tournament's
    amounts would render with the default unit."""
    headers = auth_headers()
    publish_with_eur(client, headers, eur=False)
    assert _patch(client, headers, primary_currency="EUR").status_code == 200
    fencer = auth_headers(email="f9@example.com", name="F9")

    listed = client.get("/api/tournaments/open", headers=fencer).json()
    entry = next(t for t in listed if t["slug"] == "na-duel-2026")
    assert entry["primary_currency"] == "EUR"
