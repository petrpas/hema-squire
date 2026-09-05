"""The organizer who collected the money says so (spec payments, "An organizer
may mark a registration settled by hand").

Nothing else in Squire lets a person assert that a registration is paid: the
state is reached only from a credited transaction, even on a tournament Squire
collects for. That is right where it collects and useless where it does not, and
this is the one place a human verdict is allowed."""

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


def settled(client, organizer, registration_id, value=True):
    return client.post(
        f"/api/tournaments/cup/registrations/{registration_id}/settled?settled={value}",
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


def test_refused_where_squire_handles_the_payments(client, auth_headers):
    organizer = auth_headers()
    collecting_tournament(client, organizer)
    entry = enroll(client, auth_headers, "a@example.com")

    response = settled(client, organizer, registration_id(entry))
    assert response.status_code == 409
    assert response.json()["detail"] == "payments_handled_by_squire"
    # and the registration is untouched, which is what the refusal is for
    assert registration_row(entry["vs"]).state == RegistrationState.RESERVED


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
