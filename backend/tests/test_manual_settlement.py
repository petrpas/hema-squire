"""Settled with nothing passing through Squire (spec payments, "An organizer
may mark a registration settled by hand").

One mark meaning one thing on every kind of tournament. Where Squire handles no
payments it is the organizer's word that they collected the money themselves,
and it is the only way a registration reaches the paid state there. Where
Squire handles the payments it is a **waiver** — a free place, a comped
entrant — and it asks for a reason, because a paid row holding nothing beside a
live ledger is otherwise read as a fault.

It used to be refused wherever Squire collected. What that refusal protected
against was a *silent* second writer to the paid state; this one is stored,
explained, audited, and a statement arriving afterwards is flagged rather than
credited (`add-manual-payment-entry` D4)."""

from sqlalchemy import select

from app.db import get_session
from app.main import app
from app.models import PaymentEvent, Registration, RegistrationState
from app.routers.registrations import MARK_SETTLED, UNMARK_SETTLED
from tests.conftest import enable_payments, publish

IBAN = "CZ6508000000192000145399"


def db_session():
    return next(app.dependency_overrides[get_session]())


def make_tournament(client, organizer, **patch):
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    base = {"location": "Brno", "organizers": [{"name": "Org", "link": None}]}
    assert (
        client.patch("/api/tournaments/cup", json=base | patch, headers=organizer).status_code
        == 200
    )
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "LS", "weapon": "LS", "capacity": 10, "fee": 1200},
        headers=organizer,
    )


def enroll(client, auth_headers, email):
    fencer = auth_headers(email=email, name=email.split("@")[0])
    response = client.post(
        "/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=fencer
    )
    assert response.status_code == 201, response.text
    return response.json()


def registration_row(vs):
    return db_session().scalar(select(Registration).where(Registration.vs == vs))


def registration_id(entry) -> int:
    """`RegistrationOut` states the variable symbol, not the row id — the VS is
    what the fencer and the bank both quote."""
    return registration_row(entry["vs"]).id


def settled(client, organizer, registration_id, value=True, reason=None):
    query = f"settled={value}" + (f"&reason={reason}" if reason else "")
    return client.post(
        f"/api/tournaments/cup/registrations/{registration_id}/settled?{query}",
        headers=organizer,
    )


def collecting_tournament(client, organizer):
    make_tournament(client, organizer, bank_account=IBAN)
    enable_payments(client, organizer, "cup")
    publish(client, organizer, "cup")


def self_collecting_tournament(client, organizer):
    """Squire prices everything and leaves the money alone."""
    make_tournament(client, organizer)
    publish(client, organizer, "cup")


# ----------------------------------------------------------------- the mark


def test_the_organizer_marks_a_registration_settled(client, auth_headers):
    organizer = auth_headers()
    self_collecting_tournament(client, organizer)
    entry = enroll(client, auth_headers, "a@example.com")

    response = settled(client, organizer, registration_id(entry))
    assert response.status_code == 200, response.text

    row = registration_row(entry["vs"])
    assert row.state == RegistrationState.PAID
    assert row.paid_at is not None


def test_the_mark_records_no_amount(client, auth_headers):
    """The load-bearing assertion (design D1). Writing the outstanding amount
    into the paid counter is the obvious wrong move and a state-only assertion
    would not catch it: those counters mean money that passed through Squire,
    and a figure invented here would afterwards be indistinguishable from one
    read off a statement."""
    organizer = auth_headers()
    self_collecting_tournament(client, organizer)
    entry = enroll(client, auth_headers, "a@example.com")
    before = registration_row(entry["vs"])
    owed, owed_eur = before.outstanding_cents, before.outstanding_eur_cents

    settled(client, organizer, registration_id(entry))

    row = registration_row(entry["vs"])
    assert row.amount_paid_cents == 0
    assert (row.amount_paid_eur_cents or 0) == 0
    # what it is owed is untouched: paid, and owing its whole total
    assert row.outstanding_cents == owed
    assert row.outstanding_eur_cents == owed_eur


def test_unmarking_returns_it(client, auth_headers):
    organizer = auth_headers()
    self_collecting_tournament(client, organizer)
    entry = enroll(client, auth_headers, "a@example.com")

    settled(client, organizer, registration_id(entry))
    assert settled(client, organizer, registration_id(entry), value=False).status_code == 200

    row = registration_row(entry["vs"])
    assert row.state == RegistrationState.RESERVED
    assert row.paid_at is None


def test_both_directions_are_recorded_against_the_organizer(client, auth_headers):
    organizer = auth_headers(email="org@example.com", name="Organizátor")
    self_collecting_tournament(client, organizer)
    entry = enroll(client, auth_headers, "a@example.com")

    settled(client, organizer, registration_id(entry))
    settled(client, organizer, registration_id(entry), value=False)

    events = (
        db_session()
        .scalars(
            select(PaymentEvent)
            .where(PaymentEvent.registration_id == registration_id(entry))
            .order_by(PaymentEvent.id)
        )
        .all()
    )
    kinds = [event.kind for event in events]
    assert MARK_SETTLED in kinds and UNMARK_SETTLED in kinds
    # a roster saying someone paid can always say who said so
    assert all("org@example.com" in event.detail for event in events if event.kind in kinds)


# ------------------------------------------------------------- the refusals


def test_a_reason_is_required_where_squire_collects(client, auth_headers):
    """The reversal of `add-manual-paid-marking` D2, and its replacement: the
    mark is allowed here, but not unexplained."""
    organizer = auth_headers()
    collecting_tournament(client, organizer)
    entry = enroll(client, auth_headers, "a@example.com")

    response = settled(client, organizer, registration_id(entry))
    assert response.status_code == 422
    assert response.json()["detail"] == "reason_required"
    # and the registration is untouched, which is what the refusal is for
    assert registration_row(entry["vs"]).state == RegistrationState.RESERVED


def test_a_waiver_on_a_collecting_tournament(client, auth_headers):
    organizer = auth_headers()
    collecting_tournament(client, organizer)
    entry = enroll(client, auth_headers, "a@example.com")

    response = settled(client, organizer, registration_id(entry), reason="volná účast")
    assert response.status_code == 200, response.text

    row = registration_row(entry["vs"])
    assert row.state == RegistrationState.PAID
    assert row.settled_by_hand_at is not None
    assert row.settled_by_hand_reason == "volná účast"
    # nothing arrived, so no total of received money moves — the whole of the
    # second ask (design D5)
    assert row.amount_paid_cents == 0
    assert (row.amount_paid_eur_cents or 0) == 0


def test_the_reason_is_optional_where_squire_collects_nothing(client, auth_headers):
    organizer = auth_headers()
    self_collecting_tournament(client, organizer)
    entry = enroll(client, auth_headers, "a@example.com")

    assert settled(client, organizer, registration_id(entry)).status_code == 200
    row = registration_row(entry["vs"])
    assert row.settled_by_hand_at is not None
    assert row.settled_by_hand_reason is None


def test_the_mark_is_stored_and_cleared(client, auth_headers):
    """Stored rather than deduced from a paid state with empty counters, which
    a waived registration holding a recorded payment would defeat (design
    D4)."""
    organizer = auth_headers()
    collecting_tournament(client, organizer)
    entry = enroll(client, auth_headers, "a@example.com")

    settled(client, organizer, registration_id(entry), reason="sponzor")
    settled(client, organizer, registration_id(entry), value=False)

    row = registration_row(entry["vs"])
    assert row.state == RegistrationState.RESERVED
    assert row.settled_by_hand_at is None
    assert row.settled_by_hand_reason is None


def test_the_reason_is_carried_into_the_audit(client, auth_headers):
    organizer = auth_headers(email="org@example.com", name="Organizátor")
    collecting_tournament(client, organizer)
    entry = enroll(client, auth_headers, "a@example.com")

    settled(client, organizer, registration_id(entry), reason="volná účast")

    event = db_session().scalars(
        select(PaymentEvent).where(PaymentEvent.kind == MARK_SETTLED)
    ).one()
    assert "org@example.com" in event.detail
    assert "volná účast" in event.detail


def test_refused_without_console_access(client, auth_headers):
    organizer = auth_headers()
    self_collecting_tournament(client, organizer)
    entry = enroll(client, auth_headers, "a@example.com")

    outsider = auth_headers(email="nobody@example.com", name="Nobody")
    assert settled(client, outsider, registration_id(entry)).status_code == 403


def test_a_cancelled_registration_is_not_revived(client, auth_headers):
    organizer = auth_headers()
    self_collecting_tournament(client, organizer)
    fencer = auth_headers(email="a@example.com", name="A")
    entry = client.post(
        "/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=fencer
    ).json()
    assert client.post(
        "/api/tournaments/cup/my-registration/cancel", headers=fencer
    ).status_code == 200

    response = settled(client, organizer, registration_id(entry))
    assert response.status_code == 409
    assert response.json()["detail"] == "registration_not_live"


def test_an_unknown_registration_is_not_found(client, auth_headers):
    organizer = auth_headers()
    self_collecting_tournament(client, organizer)
    assert settled(client, organizer, 9999).status_code == 404


# -------------------------------------------------- what the public list says


def test_an_unmarked_list_makes_no_claim(client, auth_headers):
    organizer = auth_headers()
    self_collecting_tournament(client, organizer)
    enroll(client, auth_headers, "a@example.com")
    enroll(client, auth_headers, "b@example.com")

    body = client.get("/api/tournaments/cup/participants").json()
    assert body["payment_state_known"] is False
    assert [p["status"] for p in body["participants"]] == [None, None]


def test_a_marked_entrant_is_shown_confirmed(client, auth_headers):
    organizer = auth_headers()
    self_collecting_tournament(client, organizer)
    marked = enroll(client, auth_headers, "a@example.com")
    enroll(client, auth_headers, "b@example.com")

    settled(client, organizer, registration_id(marked))

    body = client.get("/api/tournaments/cup/participants").json()
    by_name = {p["name"]: p["status"] for p in body["participants"]}
    assert by_name["a"] == "confirmed"
    # and the other carries no mark whatever — an absent tick is an organizer
    # who has not reached that row, not a claim that anyone failed to pay
    assert by_name["b"] is None


def test_the_unpaid_setting_still_does_not_apply(client, auth_headers):
    organizer = auth_headers()
    self_collecting_tournament(client, organizer)
    client.patch(
        "/api/tournaments/cup",
        json={"unpaid_list_treatment": "hidden"},
        headers=organizer,
    )
    marked = enroll(client, auth_headers, "a@example.com")
    enroll(client, auth_headers, "b@example.com")
    settled(client, organizer, registration_id(marked))

    names = [
        p["name"] for p in client.get("/api/tournaments/cup/participants").json()["participants"]
    ]
    assert names == ["a", "b"], "hidden would have dropped the unmarked one"


def test_a_collecting_tournaments_list_is_unchanged(client, auth_headers):
    organizer = auth_headers()
    collecting_tournament(client, organizer)
    entry = enroll(client, auth_headers, "a@example.com")

    session = db_session()
    row = session.scalar(select(Registration).where(Registration.vs == entry["vs"]))
    row.state = RegistrationState.PAID
    session.commit()

    body = client.get("/api/tournaments/cup/participants").json()
    assert body["payment_state_known"] is True
    assert [p["status"] for p in body["participants"]] == ["confirmed"]


# ------------------------------------------- switching afterwards is not handled


def test_switching_to_squire_handled_payments_leaves_the_marks(client, auth_headers):
    """Deliberately unhandled (design, Risks). The marks are neither cleared nor
    counted; the organizer who switches owns the consequence."""
    organizer = auth_headers()
    self_collecting_tournament(client, organizer)
    entry = enroll(client, auth_headers, "a@example.com")
    settled(client, organizer, registration_id(entry))

    client.patch(
        "/api/tournaments/cup", json={"bank_account": IBAN}, headers=organizer
    )
    enable_payments(client, organizer, "cup")

    row = registration_row(entry["vs"])
    assert row.state == RegistrationState.PAID
    assert row.amount_paid_cents == 0


def test_unmarking_a_registration_the_money_settled_is_refused(client, auth_headers):
    """Unmarking is this mark's to reverse and nothing else's. Clearing a mark
    a registration never had would return it to reserved with its credit
    stranded (design add-manual-payment-entry D4)."""
    organizer = auth_headers()
    collecting_tournament(client, organizer)
    entry = enroll(client, auth_headers, "a@example.com")
    reg_id = registration_id(entry)

    # paid by money, not by anybody's word
    assert client.post(
        "/api/tournaments/cup/payments/manual",
        json={
            "registration_id": reg_id,
            "amount": "1200.00",
            "currency": "CZK",
            "received_on": "2026-08-01",
            "method": "cash",
        },
        headers=organizer,
    ).status_code == 201
    assert registration_row(entry["vs"]).state == RegistrationState.PAID

    response = settled(client, organizer, reg_id, value=False)
    assert response.status_code == 409
    assert response.json()["detail"] == "not_settled_by_hand"
    row = registration_row(entry["vs"])
    assert row.state == RegistrationState.PAID
    assert row.amount_paid_cents == 120000


def test_a_registration_with_no_variable_symbol_is_marked(client, auth_headers):
    """The 500 this test exists for. A tournament whose organizer keeps the
    roster mints no variable symbols — Squire never told any payer a number to
    quote (`issuing.py`) — and `RegistrationOut.vs` was declared `int`, so the
    response could not be serialised.

    The write had already committed by then, so the mark *took* and only
    appeared on the next reload: the failure read as a refresh problem rather
    than as an error, which is how it survived being noticed."""
    organizer = auth_headers()
    collecting_tournament(client, organizer)
    entry = enroll(client, auth_headers, "a@example.com")

    session = db_session()
    registration = session.scalar(
        select(Registration).where(Registration.vs == entry["vs"])
    )
    reg_id = registration.id
    registration.vs = None
    session.commit()

    response = settled(client, organizer, reg_id, reason="kupon")
    assert response.status_code == 200, response.text
    assert response.json()["vs"] is None
    assert registration_row_by_id(reg_id).settled_by_hand_reason == "kupon"


def registration_row_by_id(registration_id: int) -> Registration:
    return db_session().get(Registration, registration_id)
