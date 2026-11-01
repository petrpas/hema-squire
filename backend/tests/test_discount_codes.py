"""Discount codes (spec discount-codes): what a code does to a price, how uses
are counted, what a registration a code covered means, and who can see any of
it."""

from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import discount_codes, emails, pricing
from app.db import Base, get_session
from app.mail import get_mailer
from app.main import app
from app.models import (
    Discipline,
    DiscountCode,
    ExtraCategory,
    ExtraItem,
    Fencer,
    PaymentCredit,
    PaymentMode,
    RefundState,
    Registration,
    RegistrationDiscipline,
    RegistrationExtra,
    RegistrationState,
    Tournament,
)
from app.ratelimit import limiter
from tests.conftest import credit_registration, enable_payments, publish

CODES = "/api/tournaments/cup/discount-codes"


def percent(value: int) -> dict:
    return {"kind": "percent", "value": value}


def fixed(value: int) -> dict:
    return {"kind": "fixed", "value": value}


def db_session():
    return next(app.dependency_overrides[get_session]())


def setup_tournament(client, organizer, *, publish_it=True, capacity=5):
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    enable_payments(client, organizer, "cup")
    client.patch(
        "/api/tournaments/cup",
        json={"city": "Brno", "organizers": [{"name": "Cup Org", "link": None}]},
        headers=organizer,
    )
    for slug, fee in (("LS", 1000), ("SB", 500)):
        client.post(
            "/api/tournaments/cup/disciplines",
            json={"slug": slug, "weapon": slug, "capacity": capacity, "fee": fee},
            headers=organizer,
        )
    if publish_it:
        publish(client, organizer, "cup")


def define(client, organizer, code="trener", effect=None, **fields):
    response = client.post(
        CODES,
        json={"name": code.title(), "code": code, "effect": effect or fixed(200), **fields},
        headers=organizer,
    )
    assert response.status_code == 201, response.text
    return response.json()


def register(client, headers, code=None, disciplines=("LS",)):
    payload: dict = {"disciplines": list(disciplines)}
    if code is not None:
        payload["discount_code"] = code
    return client.post("/api/tournaments/cup/register", json=payload, headers=headers)


def amend(client, headers, code=None, disciplines=("LS",)):
    payload: dict = {"disciplines": list(disciplines)}
    if code is not None:
        payload["discount_code"] = code
    return client.post("/api/tournaments/cup/my-registration/amend", json=payload, headers=headers)


def uses(client, organizer, index=0) -> int:
    return client.get(CODES, headers=organizer).json()[index]["uses"]


def run_lifecycle(client, organizer):
    response = client.post("/api/tournaments/cup/payments/process", headers=organizer)
    assert response.status_code == 200, response.text


def stored(session, email="f@example.com") -> Registration:
    registration = session.scalar(select(Registration).join(Fencer).where(Fencer.email == email))
    assert registration is not None
    return registration


def lapse_window(email="f@example.com"):
    session = db_session()
    stored(session, email).expires_at = datetime.now(UTC) - timedelta(days=1)
    session.commit()


# ---- pricing, on models ----


def make_tournament(**kwargs) -> Tournament:
    defaults = dict(
        slug="t",
        display_name="T",
        date=date(2026, 10, 3),
        discounts=[],
        organizers=[],
        vs_year=2026,
        vs_series=1,
        timezone="Europe/Prague",
        weapon_rental_fee=0,
        afterparty_fee=0,
    )
    return Tournament(**{**defaults, **kwargs})


def make_registration(tournament, fees, extras=()) -> Registration:
    entries = [
        RegistrationDiscipline(
            discipline=Discipline(
                tournament=tournament,
                slug=f"D{i}",
                name=f"D{i}",
                weapon=f"D{i}",
                gender="",
                material="",
                capacity=10,
                fee=fee,
            ),
            is_substitute=False,
        )
        for i, fee in enumerate(fees)
    ]
    selections = [RegistrationExtra(item=item, qty=qty) for item, qty in extras]
    return Registration(
        tournament=tournament,
        registered_at=datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
        entries=entries,
        extra_selections=selections,
        weapon_rentals=[],
        afterparty=False,
    )


def code_of(effect, scope=(), **kwargs) -> DiscountCode:
    return DiscountCode(code="c", name="C", effect=effect, scope=list(scope), **kwargs)


def test_a_fixed_code_goes_before_an_automatic_percentage():
    early = {
        "name": "Early",
        "condition": {"kind": "discipline_count", "count": 1},
        "effect": percent(15),
        "scope": ["discipline"],
    }
    tournament = make_tournament(discounts=[early])
    registration = make_registration(tournament, [2000])
    registration.discount_code = code_of(fixed(500))

    assert pricing.registration_total(registration, tournament).local == 1275


def test_a_percentage_reaches_only_its_categories():
    tournament = make_tournament()
    shirt = ExtraItem(name="Shirt", category=ExtraCategory.MERCH, price=500)
    tournament.extra_items.append(shirt)
    registration = make_registration(tournament, [1000], [(shirt, 1)])
    registration.discount_code = code_of(percent(20), ["discipline"])

    assert pricing.registration_total(registration, tournament).local == 800 + 500


def test_a_whole_total_percentage_reaches_every_category():
    tournament = make_tournament()
    shirt = ExtraItem(name="Shirt", category=ExtraCategory.MERCH, price=500)
    tournament.extra_items.append(shirt)
    registration = make_registration(tournament, [1000], [(shirt, 1)])
    registration.discount_code = code_of(percent(10))

    assert pricing.registration_total(registration, tournament).local == 1350


def test_a_code_never_moves_a_tournament_off_the_legacy_path():
    tournament = make_tournament(weapon_rental_fee=200)
    tournament.discount_codes.append(code_of(fixed(100)))
    registration = make_registration(tournament, [1000])
    registration.weapon_rentals = ["LS"]
    assert pricing.registration_total(registration, tournament).local == 1200

    registration.discount_code = tournament.discount_codes[0]
    assert not pricing.uses_itemized_pricing(tournament)
    assert pricing.registration_total(registration, tournament).local == 1100


def test_a_legacy_breakdown_accounts_for_its_total():
    tournament = make_tournament(weapon_rental_fee=200)
    registration = make_registration(tournament, [1000])
    registration.weapon_rentals = ["LS"]
    code = code_of(percent(25))
    code.id = 7
    registration.discount_code = code

    breakdown = pricing.registration_breakdown(registration, tournament)

    gross = sum(piece.unit_price * piece.qty for piece in breakdown.pieces)
    taken = sum(deduction.deducted for deduction in breakdown.deductions)
    assert gross - taken == pricing.registration_total(registration, tournament).local == 900
    assert {deduction.code_id for deduction in breakdown.deductions} == {7}


def test_each_currency_takes_its_own_fixed_amount():
    tournament = make_tournament(eur_payments_enabled=True, local_currency="CZK")
    registration = make_registration(tournament, [1000])
    registration.entries[0].discipline.fee_eur = 40
    registration.discount_code = code_of({"kind": "fixed", "value": 500, "value_eur": 20})

    totals = pricing.registration_total(registration, tournament)

    assert (totals.local, totals.eur) == (500, 20)


def test_a_fixed_code_floors_at_zero():
    tournament = make_tournament()
    registration = make_registration(tournament, [1500])
    registration.discount_code = code_of(fixed(2000))

    assert pricing.registration_total(registration, tournament).local == 0


def test_a_code_on_a_free_selection_covers_nothing():
    tournament = make_tournament()
    registration = make_registration(tournament, [0])
    registration.discount_code = code_of(percent(100))

    pricing.reprice(registration, tournament)

    assert registration.total_amount == 0
    assert registration.code_covered is False


@pytest.mark.parametrize(
    ("typed", "stored_as"),
    [(" ŠKOLA", "skola"), ("Trenéři HEMA", "treneri-hema"), ("trener", "trener")],
)
def test_a_code_matches_loosely(typed, stored_as):
    assert discount_codes.normalize(typed) == stored_as


# ---- defining ----


def test_a_duplicate_code_is_a_field_error(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    define(client, organizer)

    response = client.post(
        CODES,
        json={"name": "Other", "code": "trener", "effect": fixed(100)},
        headers=organizer,
    )

    assert response.status_code == 422
    error = response.json()["detail"]["errors"][0]
    assert (error["field"], error["code"]) == ("code", "code_taken")


def test_a_code_is_a_slug_at_the_boundary(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    for bad in ("Velká", "a b", "-x", "x"):
        response = client.post(
            CODES, json={"name": "N", "code": bad, "effect": fixed(1)}, headers=organizer
        )
        assert response.status_code == 422, bad


def test_codes_are_for_console_access_alone(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    define(client, organizer)
    stranger = auth_headers(email="f@example.com", name="F")

    assert client.get(CODES, headers=stranger).status_code == 403
    assert client.get(f"{CODES}/redemptions", headers=stranger).status_code == 403
    assert (
        client.post(
            CODES, json={"name": "N", "code": "nn", "effect": fixed(1)}, headers=stranger
        ).status_code
        == 403
    )


def test_a_used_code_keeps_its_meaning(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    code = define(client, organizer, effect=percent(10), max_uses=10)
    register(client, auth_headers(email="f@example.com", name="F"), "trener")
    assert client.get(CODES, headers=organizer).json()[0]["locked"] is True
    body = {"name": "Trenér", "code": "trener", "effect": percent(10), "max_uses": 10}

    changed = client.put(
        f"{CODES}/{code['id']}", json={**body, "effect": percent(20)}, headers=organizer
    )
    renamed_code = client.put(
        f"{CODES}/{code['id']}", json={**body, "code": "jiny"}, headers=organizer
    )
    renamed = client.put(f"{CODES}/{code['id']}", json=body, headers=organizer)

    assert changed.status_code == renamed_code.status_code == 422
    assert renamed.status_code == 200
    assert client.delete(f"{CODES}/{code['id']}", headers=organizer).status_code == 409


def test_a_limit_retires_a_code_but_cannot_go_below_its_uses(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    code = define(client, organizer, max_uses=5)
    register(client, auth_headers(email="f@example.com", name="F"), "trener")
    body = {"name": "T", "code": "trener", "effect": fixed(200)}

    assert (
        client.put(
            f"{CODES}/{code['id']}", json={**body, "max_uses": 1}, headers=organizer
        ).status_code
        == 200
    )
    late = auth_headers(email="g@example.com", name="G")
    assert register(client, late, "trener").json()["detail"] == "code_unavailable"
    assert client.get(CODES, headers=organizer).json()[0]["uses"] == 1


def test_a_limit_below_the_uses_is_refused(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    code = define(client, organizer, max_uses=5)
    register(client, auth_headers(email="f@example.com", name="F"), "trener")
    register(client, auth_headers(email="g@example.com", name="G"), "trener")

    response = client.put(
        f"{CODES}/{code['id']}",
        json={"name": "T", "code": "trener", "effect": fixed(200), "max_uses": 1},
        headers=organizer,
    )

    assert response.status_code == 422
    assert response.json()["detail"]["errors"][0]["field"] == "max_uses"


def test_an_unused_code_can_be_deleted(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    code = define(client, organizer)

    assert client.delete(f"{CODES}/{code['id']}", headers=organizer).status_code == 204
    assert client.get(CODES, headers=organizer).json() == []


def test_a_cancelled_row_still_blocks_deletion(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    code = define(client, organizer)
    fencer = auth_headers(email="f@example.com", name="F")
    register(client, fencer, "trener")
    client.post("/api/tournaments/cup/my-registration/cancel", headers=fencer)

    assert client.delete(f"{CODES}/{code['id']}", headers=organizer).status_code == 409


def test_a_fixed_code_without_its_euro_amount_is_a_missing_price(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer, publish_it=False)
    client.patch("/api/tournaments/cup", json={"eur_payments_enabled": True}, headers=organizer)
    define(client, organizer)

    detail = client.get("/api/tournaments/cup", headers=organizer).json()

    assert "discount_prices" in detail["setup_missing"]


def test_a_manual_tournament_takes_no_codes(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer, publish_it=False)
    assert (
        client.patch(
            "/api/tournaments/cup/registrations-kept-by",
            json={"registrations_kept_by": "organizer"},
            headers=organizer,
        ).status_code
        == 200
    )

    response = client.post(
        CODES, json={"name": "T", "code": "trener", "effect": fixed(1)}, headers=organizer
    )

    assert response.status_code == 409


# ---- redeeming ----


def test_every_unusable_code_answers_the_same(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    define(client, organizer, max_uses=1)
    register(client, auth_headers(email="a@example.com", name="A"), "trener")

    exhausted = register(client, auth_headers(email="b@example.com", name="B"), "trener")
    invented = register(client, auth_headers(email="c@example.com", name="C"), "nikdy")
    malformed = register(client, auth_headers(email="d@example.com", name="D"), "!!! ?")

    assert exhausted.status_code == invented.status_code == malformed.status_code == 422
    assert exhausted.json() == invented.json() == malformed.json()
    session = db_session()
    assert len(session.scalars(select(Registration)).all()) == 1


def test_another_tournaments_code_is_no_code(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    client.post(
        "/api/tournaments",
        json={"slug": "other", "display_name": "Other", "date": "2026-12-05"},
        headers=organizer,
    )
    response = client.post(
        "/api/tournaments/other/discount-codes",
        json={"name": "Elsewhere", "code": "elsewhere", "effect": percent(50)},
        headers=organizer,
    )
    assert response.status_code == 201

    refused = register(client, auth_headers(email="f@example.com", name="F"), "elsewhere")

    assert refused.json()["detail"] == "code_unavailable"


def test_preview_equals_registration(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    define(client, organizer, effect=percent(10))

    preview = client.post(
        "/api/tournaments/cup/price-preview/code",
        json={"disciplines": ["LS", "SB"], "discount_code": "TRENER"},
    ).json()
    registered = register(
        client, auth_headers(email="f@example.com", name="F"), "TRENER", ("LS", "SB")
    ).json()

    assert preview["total"] == registered["total_amount"] == 1350
    assert preview["discounts"] == []
    assert preview["applied_code"]["deducted"] == 150
    assert registered["applied_code"] == preview["applied_code"]


def test_the_plain_preview_ignores_a_code(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    define(client, organizer)

    plain = client.post(
        "/api/tournaments/cup/price-preview",
        json={"disciplines": ["LS"], "discount_code": "trener"},
    ).json()

    assert plain["total"] == 1000
    assert plain["applied_code"] is None


def test_the_preview_is_throttled_only_with_a_code():
    limited = limiter._route_limits
    assert "app.routers.registrations.price_preview_with_code" in limited
    assert "app.routers.registrations.price_preview_for_amendment" in limited
    assert "app.routers.registrations.price_preview" not in limited


def test_a_cancellation_gives_the_use_back(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    define(client, organizer, max_uses=1)
    first = auth_headers(email="f@example.com", name="F")
    register(client, first, "trener")
    assert uses(client, organizer) == 1

    client.post("/api/tournaments/cup/my-registration/cancel", headers=first)

    assert uses(client, organizer) == 0
    next_up = register(client, auth_headers(email="g@example.com", name="G"), "trener")
    assert next_up.status_code == 201


def test_an_expiry_gives_the_use_back(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    define(client, organizer, max_uses=1)
    register(client, auth_headers(email="f@example.com", name="F"), "trener")
    lapse_window()

    run_lifecycle(client, organizer)

    assert uses(client, organizer) == 0


def test_the_last_use_cannot_be_taken_twice(client, auth_headers):
    """The race's second arrival: it passed the early check, then finds the use
    gone at the claim, and leaves nothing behind."""
    organizer = auth_headers()
    setup_tournament(client, organizer)
    code_id = define(client, organizer, max_uses=1)["id"]
    register(client, auth_headers(email="f@example.com", name="F"), "trener")
    auth_headers(email="late@example.com", name="Late")

    session = db_session()
    code = session.get(DiscountCode, code_id)
    late = session.scalar(select(Fencer).where(Fencer.email == "late@example.com"))
    assert code is not None
    assert late is not None
    session.add(
        Registration(tournament_id=code.tournament_id, fencer_id=late.id, discount_code=code)
    )
    session.flush()

    with pytest.raises(HTTPException) as refused:
        discount_codes.claim(session, code)

    assert refused.value.detail == "code_unavailable"
    assert len(db_session().scalars(select(Registration)).all()) == 1


def test_a_revival_keeps_the_discount_past_the_limit(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    define(client, organizer, max_uses=1)
    register(client, auth_headers(email="f@example.com", name="F"), "trener")
    lapse_window()
    run_lifecycle(client, organizer)
    register(client, auth_headers(email="g@example.com", name="G"), "trener")

    session = db_session()
    revived = stored(session)
    revived.state = RegistrationState.RESERVED
    pricing.reprice(revived, revived.tournament)
    session.commit()

    assert uses(client, organizer) == 2
    session = db_session()
    assert stored(session).total_amount == 800
    assert (
        register(client, auth_headers(email="h@example.com", name="H"), "trener").json()["detail"]
        == "code_unavailable"
    )


def test_re_registering_carries_only_what_it_submits(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    define(client, organizer)
    fencer = auth_headers(email="f@example.com", name="F")
    register(client, fencer, "trener")
    client.post("/api/tournaments/cup/my-registration/cancel", headers=fencer)

    again = register(client, fencer).json()

    assert again["total_amount"] == 1000
    assert again["applied_code"] is None
    assert uses(client, organizer) == 0


def test_a_failed_claim_on_a_re_registration_leaves_it_cancelled(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    define(client, organizer, max_uses=1)
    fencer = auth_headers(email="f@example.com", name="F")
    register(client, fencer)
    client.post("/api/tournaments/cup/my-registration/cancel", headers=fencer)
    register(client, auth_headers(email="g@example.com", name="G"), "trener")

    refused = register(client, fencer, "trener")

    assert refused.status_code == 422
    assert stored(db_session()).state == RegistrationState.CANCELLED


def test_a_held_code_keeps_pricing_after_it_runs_out(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    define(client, organizer, max_uses=1)
    holder = auth_headers(email="f@example.com", name="F")
    register(client, holder, "trener")

    preview = client.post(
        "/api/tournaments/cup/my-registration/price-preview",
        json={"disciplines": ["LS", "SB"]},
        headers=holder,
    )
    amended = amend(client, holder, disciplines=("LS", "SB"))

    assert preview.status_code == 200
    assert preview.json()["total"] == amended.json()["total_amount"] == 1300


# ---- amending ----


def test_a_forgotten_code_can_be_added_by_amending(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    define(client, organizer)
    fencer = auth_headers(email="f@example.com", name="F")
    register(client, fencer)

    amended = amend(client, fencer, "trener").json()

    assert amended["total_amount"] == 800
    assert amended["applied_code"]["name"] == "Trener"
    assert uses(client, organizer) == 1


def test_adding_a_code_after_paying_leaves_an_overpayment(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    define(client, organizer)
    fencer = auth_headers(email="f@example.com", name="F")
    register(client, fencer)
    session = db_session()
    credit_registration(session, stored(session), 100000)

    amended = amend(client, fencer, "trener").json()

    assert amended["state"] == "paid"
    assert amended["total_amount"] == 800
    assert stored(db_session()).balance_cents(stored(db_session()).tournament)[0] == -20000


def test_a_code_cannot_be_swapped_or_removed(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    define(client, organizer)
    define(client, organizer, code="jiny", effect=fixed(300))
    fencer = auth_headers(email="f@example.com", name="F")
    register(client, fencer, "trener")

    swapped = amend(client, fencer, "jiny")
    without = amend(client, fencer).json()
    repeated = amend(client, fencer, "Trener")

    assert swapped.status_code == 409
    assert without["total_amount"] == 800
    assert repeated.status_code == 200


def test_an_exhausted_code_cannot_be_added(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    define(client, organizer, max_uses=1)
    fencer = auth_headers(email="f@example.com", name="F")
    register(client, fencer)
    register(client, auth_headers(email="g@example.com", name="G"), "trener")

    assert amend(client, fencer, "trener").json()["detail"] == "code_unavailable"


# ---- a code that covers the price ----


def test_a_covered_registration_reads_paid_and_is_left_alone(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    define(client, organizer, effect=percent(100))

    body = register(client, auth_headers(email="f@example.com", name="F"), "trener").json()

    assert body["total_amount"] == 0
    assert body["state"] == "paid"
    lapse_window()
    run_lifecycle(client, organizer)
    session = db_session()
    registration = stored(session)
    assert registration.state == RegistrationState.RESERVED
    assert registration.reminded_at is None
    assert session.scalars(select(PaymentCredit)).all() == []
    assert registration.active_waiver is None


class CollectingMailer:
    def __init__(self):
        self.sent = []

    def send(self, message):
        self.sent.append(message)


def test_a_covered_confirmation_asks_for_nothing(client, auth_headers):
    mailer = CollectingMailer()
    app.dependency_overrides[get_mailer] = lambda: mailer
    organizer = auth_headers()
    setup_tournament(client, organizer)
    define(client, organizer, effect=percent(100))

    register(client, auth_headers(email="f@example.com", name="F"), "trener")

    app.dependency_overrides.pop(get_mailer, None)
    letter = next(m for m in mailer.sent if "f@example.com" in m["To"])
    assert "nic neplatíš" in letter.get_body(("plain",)).get_content()
    assert not list(letter.iter_attachments())


def test_nothing_covered_means_no_payment_instructions(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    define(client, organizer, effect=fixed(2000))
    fencer = auth_headers(email="f@example.com", name="F")
    register(client, fencer, "trener")

    response = client.get("/api/tournaments/cup/my-registration/payment", headers=fencer)

    assert response.status_code == 409
    assert response.json()["detail"] == "not_unpaid"


def test_an_amendment_leaving_money_owed_opens_a_window(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    define(client, organizer, effect=fixed(1000))
    fencer = auth_headers(email="f@example.com", name="F")
    register(client, fencer, "trener")
    lapse_window()

    amended = amend(client, fencer, disciplines=("LS", "SB")).json()

    assert amended["total_amount"] == 500
    assert amended["state"] == "reserved"
    assert datetime.fromisoformat(amended["expires_at"]) > datetime.now(UTC)


def test_cancelling_a_covered_registration_records_no_refund(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    client.patch("/api/tournaments/cup", json={"refundable_until": "2099-01-01"}, headers=organizer)
    define(client, organizer, effect=percent(100))
    fencer = auth_headers(email="f@example.com", name="F")
    register(client, fencer, "trener")

    client.post("/api/tournaments/cup/my-registration/cancel", headers=fencer)

    registration = stored(db_session())
    assert registration.refund_state == RefundState.NOT_APPLICABLE
    assert registration.refundable is None


def test_a_covered_registration_in_the_queue_is_not_paid_until_admitted(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer, capacity=1)
    define(client, organizer, effect=percent(100))
    register(client, auth_headers(email="a@example.com", name="A"))

    queued = register(client, auth_headers(email="f@example.com", name="F"), "trener").json()

    assert all(entry["is_substitute"] for entry in queued["entries"])
    assert queued["state"] == "reserved"


def test_a_code_covering_the_claim_leaves_no_offer_to_pay(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer, capacity=1)
    client.patch("/api/tournaments/cup", json={"queue_payment_seats": True}, headers=organizer)
    define(client, organizer, effect=percent(100))
    define(client, organizer, code="polovina", effect=percent(50))
    register(client, auth_headers(email="a@example.com", name="A"))
    covered = auth_headers(email="f@example.com", name="F")
    register(client, covered, "trener")
    paying = auth_headers(email="g@example.com", name="G")
    register(client, paying, "polovina")

    session = db_session()
    assert stored(session).claim_total is None
    assert stored(session, "g@example.com").claim_total == 500
    response = client.get("/api/tournaments/cup/my-registration/payment", headers=covered)
    assert (response.status_code, response.json()["detail"]) == (409, "no_payment_due")


def test_a_total_below_the_deposit_asks_for_the_total():
    tournament = make_tournament(
        payment_mode=PaymentMode.DEPOSIT, deposit_amount=500, language="en"
    )
    registration = make_registration(tournament, [300])
    registration.expires_at = datetime(2026, 9, 1, tzinfo=UTC)
    registration.total_amount = 300

    lines, _consequence, _qrs = emails._payment_block(tournament, registration, "en")

    assert "500" not in lines


# ---- privacy ----


def test_the_public_learns_only_that_codes_are_accepted(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    define(client, organizer, code="tajny-kod", effect=percent(37), max_uses=1)
    fencer = auth_headers(email="f@example.com", name="F")
    register(client, fencer, "tajny-kod")

    for path in ("/public", "/entrants", "/availability"):
        text = client.get(f"/api/tournaments/cup{path}").text
        assert "tajny" not in text.lower()
        assert "Tajny-Kod" not in text
        assert 'discount_code"' not in text


def test_the_field_is_withdrawn_when_nothing_is_usable(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    assert client.get("/api/tournaments/cup/public").json()["accepts_discount_codes"] is False
    define(client, organizer, max_uses=1)
    assert client.get("/api/tournaments/cup/public").json()["accepts_discount_codes"] is True

    register(client, auth_headers(email="f@example.com", name="F"), "trener")

    assert client.get("/api/tournaments/cup/public").json()["accepts_discount_codes"] is False


# ---- who holds what, and the document ----


def test_redemptions_list_live_holders_and_agree_with_uses(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    define(client, organizer, max_uses=10)
    define(client, organizer, code="nikdo")
    first = auth_headers(email="f@example.com", name="F")
    second = auth_headers(email="g@example.com", name="G")
    register(client, first, "trener")
    register(client, second, "trener")
    client.post("/api/tournaments/cup/my-registration/cancel", headers=second)

    body = client.get(f"{CODES}/redemptions", headers=organizer).json()

    assert [(c["uses"], c["max_uses"]) for c in body["codes"]] == [(1, 10), (0, None)]
    assert [(r["code"], r["deducted"], r["paid"]) for r in body["rows"]] == [("trener", 200, False)]


def test_codes_survive_the_document(client, auth_headers, engine):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    define(client, organizer, effect=percent(100), max_uses=4)
    register(client, auth_headers(email="f@example.com", name="F"), "trener")

    document = client.get("/api/tournaments/cup/export/json", headers=organizer).json()

    assert document["discount_codes"][0]["code"] == "trener"
    entry = document["registrations"][0]
    assert (entry["discount_code"], entry["code_covered"]) == ("trener", True)

    new_organizer = fresh_deployment(client, auth_headers)
    assert (
        client.post("/api/tournaments/restore", json=document, headers=new_organizer).status_code
        == 201
    )
    assert client.get(CODES, headers=new_organizer).json()[0]["uses"] == 1
    assert stored(db_session()).settled


def test_an_older_document_has_no_codes(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    register(client, auth_headers(email="f@example.com", name="F"))
    document = client.get("/api/tournaments/cup/export/json", headers=organizer).json()
    document["schema_version"] = 19
    del document["discount_codes"]
    for entry in document["registrations"]:
        del entry["discount_code"]
        del entry["code_covered"]

    new_organizer = fresh_deployment(client, auth_headers)
    assert (
        client.post("/api/tournaments/restore", json=document, headers=new_organizer).status_code
        == 201
    )
    assert client.get(CODES, headers=new_organizer).json() == []


def fresh_deployment(client, auth_headers):
    """An empty database behind the app: VS is unique across the deployment, so
    a document restores only beside nothing."""
    fresh = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(fresh)

    def fresh_session():
        with Session(fresh) as session:
            yield session

    app.dependency_overrides[get_session] = fresh_session
    return auth_headers()
