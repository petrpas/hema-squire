"""Tournament currency: model defaults, save-time invariants, dual pricing,
and the migration that introduces the columns.

The governing rule is that everything about currency is inert until an organizer
opts in — a tournament that predates the change must price and bill exactly as
it did before. Once EUR pricing is opted into, both figures are stored,
organizer-typed decisions; neither is ever derived from the other or from
eur_rate, which is a Setup convenience only (design Decision 3).
"""

import datetime
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
from tests.conftest import enable_payments, import_statement, publish
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
    return import_statement(client, headers, csv, slug="na-duel-2026")


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

    assert tournament.local_currency == Currency.CZK
    assert tournament.eur_payments_enabled is False
    assert tournament.eur_rate is None
    assert tournament.shows_eur is False
    assert tournament.registration_instructions is None


def test_legacy_totals_unchanged_by_currency_columns(session):
    """A pre-itemized tournament's total is the legacy computation, untouched."""
    tournament = make_tournament(weapon_rental_fee=50, afterparty_fee=400)
    longsword = Discipline(
        tournament=tournament,
        slug="LS",
        weapon="LS",
        gender="",
        material="",
        name="Longsword Open Steel",
        capacity=32,
        fee=500,
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


# --- dual pricing is independent and never derived ------------------------------


def test_eur_price_stored_independently_of_local_price(session):
    tournament = make_tournament(local_currency=Currency.CZK, eur_payments_enabled=True)
    longsword = Discipline(
        tournament=tournament,
        slug="LS",
        weapon="LS",
        gender="",
        material="",
        name="Longsword",
        capacity=32,
        fee=800,
        fee_eur=32,
    )
    session.add(tournament)
    session.commit()

    totals = pricing.selection_totals(
        tournament,
        disciplines=[longsword],
        extras=[],
        weapon_rentals=[],
        afterparty=False,
        at=datetime.date(2026, 9, 1),
    )
    assert totals.local == 800
    assert totals.eur == 32


def test_totals_need_not_correspond_at_any_rate(session):
    """The two prices are independent decisions; a mismatched implied ratio
    is accepted with no reconciliation (design Decision 1)."""
    tournament = make_tournament(
        local_currency=Currency.CZK, eur_payments_enabled=True, eur_rate=Decimal("25")
    )
    row1 = Discipline(
        tournament=tournament,
        slug="LS",
        weapon="LS",
        gender="",
        material="",
        name="LS",
        capacity=10,
        fee=800,
        fee_eur=32,
    )
    row2 = Discipline(
        tournament=tournament,
        slug="SA",
        weapon="SA",
        gender="",
        material="",
        name="SA",
        capacity=10,
        fee=700,
        fee_eur=30,
    )
    session.add(tournament)
    session.commit()

    totals = pricing.selection_totals(
        tournament,
        disciplines=[row1, row2],
        extras=[],
        weapon_rentals=[],
        afterparty=False,
        at=datetime.date(2026, 9, 1),
    )
    assert totals.local == 1500
    assert totals.eur == 62  # 32 + 30, not 1500 / 25 = 60


def test_eur_rate_change_does_not_move_any_stored_price(session):
    tournament = make_tournament(local_currency=Currency.CZK, eur_payments_enabled=True)
    longsword = Discipline(
        tournament=tournament,
        slug="LS",
        weapon="LS",
        gender="",
        material="",
        name="LS",
        capacity=10,
        fee=800,
        fee_eur=32,
    )
    session.add(tournament)
    session.commit()

    tournament.eur_rate = Decimal("1000")  # wildly implausible
    session.commit()

    totals = pricing.selection_totals(
        tournament,
        disciplines=[longsword],
        extras=[],
        weapon_rentals=[],
        afterparty=False,
        at=datetime.date(2026, 9, 1),
    )
    assert totals.local == 800
    assert totals.eur == 32


def test_eur_priced_tournament_shows_no_second_figure(session):
    """An EUR tournament's local figure already is the EUR one."""
    tournament = make_tournament(local_currency=Currency.EUR, eur_payments_enabled=True)
    session.add(tournament)
    session.commit()

    assert tournament.shows_eur is False


# --- 1.5/2.x the migration itself ------------------------------------------------


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


def test_migration_renames_currency_and_adds_eur_columns(tmp_path):
    db_path = tmp_path / "migrate_dual.sqlite"

    _alembic(db_path, "upgrade", "df6a74c06dfa")
    engine = create_engine(f"sqlite:///{db_path}")
    before = {c["name"] for c in inspect(engine).get_columns("tournaments")}
    assert "primary_currency" in before
    assert "local_currency" not in before
    engine.dispose()

    _alembic(db_path, "upgrade", "3ebc04d896eb")
    engine = create_engine(f"sqlite:///{db_path}")
    inspector = inspect(engine)
    tournaments = {c["name"] for c in inspector.get_columns("tournaments")}
    assert "local_currency" in tournaments
    assert "primary_currency" not in tournaments
    disciplines = {c["name"] for c in inspector.get_columns("disciplines")}
    assert {"fee_eur", "fee_early_eur"} <= disciplines
    items = {c["name"] for c in inspector.get_columns("extra_items")}
    assert "price_eur" in items
    registrations = {c["name"] for c in inspector.get_columns("registrations")}
    assert {"total_eur", "amount_paid_eur_cents"} <= registrations
    engine.dispose()

    _alembic(db_path, "downgrade", "df6a74c06dfa")
    engine = create_engine(f"sqlite:///{db_path}")
    after = {c["name"] for c in inspect(engine).get_columns("tournaments")}
    assert "primary_currency" in after
    assert "local_currency" not in after
    engine.dispose()


def test_migration_derives_eur_prices_only_for_eur_enabled_tournaments(tmp_path):
    db_path = tmp_path / "migrate_derive.sqlite"
    _alembic(db_path, "upgrade", "df6a74c06dfa")

    import sqlite3

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO tournaments
        (slug, display_name, date, language, reservation_validity_days, reminder_day,
         amount_tolerance_percent, unpaid_list_treatment, weapon_rental_fee, afterparty_fee,
         hr_category_map, discounts, organizers, primary_currency, eur_payments_enabled,
         eur_rate, expiry_grace_hours, vs_year, vs_series, vs_next_seq, qualification_open)
        VALUES ('eur-tour','EUR Tour','2026-10-03','cs',10,5,5,'greyed',0,0,'{}','[]','[]',
        'CZK',1,25.5,48,2026,1,1,1)"""
    )
    eur_tid = cur.lastrowid
    cur.execute(
        "INSERT INTO disciplines (tournament_id, code, name, capacity, fee, fee_early) "
        "VALUES (?, 'LS','Longsword',10,1750,1500)",
        (eur_tid,),
    )
    cur.execute(
        """INSERT INTO tournaments
        (slug, display_name, date, language, reservation_validity_days, reminder_day,
         amount_tolerance_percent, unpaid_list_treatment, weapon_rental_fee, afterparty_fee,
         hr_category_map, discounts, organizers, primary_currency, eur_payments_enabled,
         eur_rate, expiry_grace_hours, vs_year, vs_series, vs_next_seq, qualification_open)
        VALUES ('czk-tour','CZK Tour','2026-10-03','cs',10,5,5,'greyed',0,0,'{}','[]','[]',
        'CZK',0,NULL,48,2026,2,1,1)"""
    )
    czk_tid = cur.lastrowid
    cur.execute(
        "INSERT INTO disciplines (tournament_id, code, name, capacity, fee, fee_early) "
        "VALUES (?, 'LS','Longsword',10,900,NULL)",
        (czk_tid,),
    )
    conn.commit()
    conn.close()

    _alembic(db_path, "upgrade", "3ebc04d896eb")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    eur_fee = cur.execute(
        "SELECT fee_eur, fee_early_eur FROM disciplines WHERE tournament_id = ?", (eur_tid,)
    ).fetchone()
    assert eur_fee == (69, 59)  # 1750/25.5, 1500/25.5, half-up
    czk_fee = cur.execute(
        "SELECT fee_eur, fee_early_eur FROM disciplines WHERE tournament_id = ?", (czk_tid,)
    ).fetchone()
    assert czk_fee == (None, None)
    conn.close()


# --- 2.2/2.5 save-time invariants through the API ------------------------------


def test_new_tournament_reports_czk_without_eur(client, auth_headers):
    headers = auth_headers()
    created = make_api_tournament(client, headers)

    assert created["local_currency"] == "CZK"
    assert created["eur_payments_enabled"] is False
    assert created["eur_rate"] is None
    assert created["currency_mode"] == "local"
    assert created["registration_instructions"] is None


def _patch(client, headers, **fields):
    return client.patch("/api/tournaments/na-duel-2026", json=fields, headers=headers)


def test_enabling_eur_payments_does_not_require_a_rate(client, auth_headers):
    """eur_rate is a Setup convenience only (design Decision 3) — it is never
    required to accept EUR."""
    headers = auth_headers()
    make_api_tournament(client, headers)

    response = _patch(client, headers, eur_payments_enabled=True)
    assert response.status_code == 200, response.text
    out = response.json()
    assert out["eur_payments_enabled"] is True
    assert out["eur_rate"] is None
    assert out["currency_mode"] == "local_eur"


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


def test_eur_local_forces_enabled_and_clears_rate(client, auth_headers):
    headers = auth_headers()
    make_api_tournament(client, headers)
    _patch(client, headers, eur_payments_enabled=True, eur_rate="25.5")

    response = _patch(client, headers, local_currency="EUR")
    assert response.status_code == 200, response.text
    out = response.json()
    assert out["local_currency"] == "EUR"
    assert out["eur_payments_enabled"] is True
    assert out["eur_rate"] is None
    assert out["currency_mode"] == "eur"


def test_disabling_eur_payments_clears_the_rate(client, auth_headers):
    headers = auth_headers()
    make_api_tournament(client, headers)
    _patch(client, headers, eur_payments_enabled=True, eur_rate="25.5")

    response = _patch(client, headers, eur_payments_enabled=False)
    assert response.status_code == 200, response.text
    out = response.json()
    assert out["eur_payments_enabled"] is False
    assert out["eur_rate"] is None
    assert out["currency_mode"] == "local"


def test_mode_switch_retains_stored_prices(client, auth_headers):
    """Switching away from EUR and back must not clear stored prices (design
    Decision 8)."""
    headers = auth_headers()
    make_api_tournament(client, headers)
    _patch(client, headers, eur_payments_enabled=True)
    client.post(
        "/api/tournaments/na-duel-2026/disciplines",
        json={"slug": "LS", "weapon": "LS", "capacity": 10, "fee": 800, "fee_eur": 32},
        headers=headers,
    )

    assert _patch(client, headers, eur_payments_enabled=False).status_code == 200
    assert _patch(client, headers, eur_payments_enabled=True).status_code == 200

    detail = client.get("/api/tournaments/na-duel-2026", headers=headers).json()
    discipline = next(d for d in detail["disciplines"] if d["slug"] == "LS")
    assert discipline["fee"] == 800
    assert discipline["fee_eur"] == 32


def test_enabling_eur_blocked_by_legacy_fixed_fees(client, auth_headers):
    headers = auth_headers()
    make_api_tournament(client, headers)
    assert _patch(client, headers, weapon_rental_fee=50).status_code == 200

    response = _patch(client, headers, eur_payments_enabled=True)
    assert response.status_code == 422
    assert response.json()["detail"] == {
        "errors": [
            {"field": "eur_payments_enabled", "code": "legacy_fixed_fees_block_eur", "params": {}}
        ]
    }


def test_registration_instructions_round_trip(client, auth_headers):
    headers = auth_headers()
    make_api_tournament(client, headers)
    text = "Zaplať do 10 dnů.\n\nQR kód najdeš v e-mailu."

    response = _patch(client, headers, registration_instructions=text)
    assert response.status_code == 200, response.text
    assert response.json()["registration_instructions"] == text


# --- 4.6/5.3 EUR payment instructions, emails, and matching ---------------------


def publish_with_eur(client, headers, *, eur=True, fee=1750, fee_eur=70):
    make_api_tournament(client, headers)
    enable_payments(client, headers, "na-duel-2026")
    patch = {
        "location": "Brno",
        "organizers": [{"name": "Org", "link": None}],
        "bank_account": "CZ6508000000192000145399",
    }
    if eur:
        patch |= {"eur_payments_enabled": True}
    assert client.patch(
        "/api/tournaments/na-duel-2026", json=patch, headers=headers
    ).status_code == 200
    discipline = {"slug": "LS", "weapon": "LS", "capacity": 10, "fee": fee}
    if eur:
        discipline["fee_eur"] = fee_eur
    client.post(
        "/api/tournaments/na-duel-2026/disciplines",
        json=discipline,
        headers=headers,
    )
    publish(client, headers, "na-duel-2026")


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
        "CZ6508000000192000145399", Decimal("70.00"), 1000001, "VS1000001 Cup", currency="EUR"
    )
    assert "AM:70.00" in result
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
    assert data["eur_amount"] == 70
    assert "CC:CZK" in data["spayd"]
    assert "CC:EUR" in data["eur_spayd"]
    assert "AM:70.00" in data["eur_spayd"]
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
    assert data["eur_total"] == 70


def test_confirmation_email_carries_both_amounts_and_two_qrs(client, auth_headers, mailbox):
    headers = auth_headers()
    publish_with_eur(client, headers)
    enroll(client, auth_headers)

    message = mailbox.sent[-1]
    body = message.get_body(preferencelist=("plain",)).get_content()
    assert "1750 Kč" in body
    assert "70 €" in body
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


def test_eur_transaction_matches_the_stored_eur_total(client, auth_headers, mailbox):
    headers = auth_headers()
    publish_with_eur(client, headers)
    fencer, vs = enroll(client, auth_headers)

    result = _import_rows(client, headers, [f"1;01.08.2026;70,00;EUR;{vs};;;;MUELLER;DE99"])
    assert result["matched"] == 1
    state = client.get(
        "/api/tournaments/na-duel-2026/my-registration", headers=fencer
    ).json()["state"]
    assert state == "paid"


def test_eur_transaction_on_czk_only_tournament_is_flagged_not_accepted(
    client, auth_headers, mailbox
):
    headers = auth_headers()
    publish_with_eur(client, headers, eur=False)
    fencer, vs = enroll(client, auth_headers)

    result = _import_rows(client, headers, [f"1;01.08.2026;70,00;EUR;{vs};;;;MUELLER;DE99"])
    assert result["flagged"] == 1
    queue = client.get(
        "/api/tournaments/na-duel-2026/payments/unmatched", headers=headers
    ).json()
    assert queue[0]["status_reason"] == "currency_not_accepted"
    state = client.get(
        "/api/tournaments/na-duel-2026/my-registration", headers=fencer
    ).json()["state"]
    assert state == "reserved"


def test_eur_payment_far_off_credited_as_partial(client, auth_headers, mailbox):
    """A shortfall beyond tolerance is credited as a partial payment rather
    than flagged (design harden-payment-matching Decision 1)."""
    headers = auth_headers()
    publish_with_eur(client, headers)
    fencer, vs = enroll(client, auth_headers)

    result = _import_rows(client, headers, [f"1;01.08.2026;40,00;EUR;{vs};;;;MUELLER;DE99"])
    assert result["partial"] == 1
    queue = client.get(
        "/api/tournaments/na-duel-2026/payments/unmatched", headers=headers
    ).json()
    assert queue == []


def test_eur_rate_change_does_not_affect_matching(client, auth_headers, mailbox):
    headers = auth_headers()
    publish_with_eur(client, headers)
    fencer, vs = enroll(client, auth_headers)

    assert _patch(client, headers, eur_rate="1000").status_code == 200

    result = _import_rows(client, headers, [f"1;01.08.2026;70,00;EUR;{vs};;;;MUELLER;DE99"])
    assert result["matched"] == 1


def test_same_currency_matching_unchanged(client, auth_headers, mailbox):
    headers = auth_headers()
    publish_with_eur(client, headers, eur=False)
    fencer, vs = enroll(client, auth_headers)

    result = _import_rows(client, headers, [f"1;01.08.2026;1 750,00;CZK;{vs};;;;Jan N;123"])
    assert result["matched"] == 1


def test_open_list_carries_the_local_currency(client, auth_headers):
    """The fencer-facing list must name the currency, or a EUR tournament's
    amounts would render with the default unit."""
    headers = auth_headers()
    publish_with_eur(client, headers, eur=False)
    assert _patch(client, headers, local_currency="EUR").status_code == 200
    fencer = auth_headers(email="f9@example.com", name="F9")

    listed = client.get("/api/tournaments/open", headers=fencer).json()
    entry = next(t for t in listed if t["slug"] == "na-duel-2026")
    assert entry["local_currency"] == "EUR"


# --- 8.7 incomplete EUR prices block registration -------------------------------


def test_incomplete_eur_prices_block_registration(client, auth_headers):
    headers = auth_headers()
    make_api_tournament(client, headers)
    patch = {
        "location": "Brno",
        "organizers": [{"name": "Org", "link": None}],
        "eur_payments_enabled": True,
    }
    assert client.patch(
        "/api/tournaments/na-duel-2026", json=patch, headers=headers
    ).status_code == 200
    # fee_eur left empty — completeness follows from the form (design Decision 2)
    client.post(
        "/api/tournaments/na-duel-2026/disciplines",
        json={"slug": "LS", "weapon": "LS", "capacity": 10, "fee": 1750},
        headers=headers,
    )
    fencer = auth_headers(email="fincomplete@example.com", name="F")

    response = client.post(
        "/api/tournaments/na-duel-2026/register",
        json={"disciplines": ["LS"]},
        headers=fencer,
    )
    assert response.status_code == 403
    assert response.json()["detail"] == {"reason": "not_published"}


# --- 8.14 a price change leaves existing registrations untouched ---------------


def test_price_change_leaves_existing_registration_untouched(client, auth_headers, mailbox):
    headers = auth_headers()
    publish_with_eur(client, headers, fee=1750, fee_eur=70)
    fencer, _ = enroll(client, auth_headers)
    initial = client.get(
        "/api/tournaments/na-duel-2026/my-registration", headers=fencer
    ).json()
    assert initial["total_amount"] == 1750
    assert initial["total_eur"] == 70

    assert client.patch(
        "/api/tournaments/na-duel-2026/disciplines/LS",
        json={"slug": "LS", "weapon": "LS", "capacity": 10, "fee": 2000, "fee_eur": 80},
        headers=headers,
    ).status_code == 200

    unchanged = client.get(
        "/api/tournaments/na-duel-2026/my-registration", headers=fencer
    ).json()
    assert unchanged["total_amount"] == 1750
    assert unchanged["total_eur"] == 70

    new_fencer = auth_headers(email="fnew@example.com", name="FNew")
    new_registration = client.post(
        "/api/tournaments/na-duel-2026/register",
        json={"disciplines": ["LS"]},
        headers=new_fencer,
    ).json()
    assert new_registration["total_amount"] == 2000
    assert new_registration["total_eur"] == 80
