"""A seat changing hands (spec `fencer-substitution`).

What every one of these is really asserting is that nothing moved: the whole
design is that the number, the order, the symbol, the totals and the journal are
properties of the registration and of the row id rather than of the person, so
the substitute inherits them by nothing being done to them.
"""

import pytest
from sqlalchemy import select

from app.mail import get_mailer
from app.main import app
from app.models import Fencer, Registration
from tests.conftest import enable_payments, publish


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


def setup(client, organizer, *, payments=True):
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "LS", "weapon": "LS", "capacity": 10, "fee": 1000},
        headers=organizer,
    )
    if payments:
        enable_payments(client, organizer, "cup")
    publish(client, organizer, "cup")


def register(client, auth_headers, email="jan@example.com", name="Jan Novák"):
    fencer = auth_headers(email=email, name=name)
    response = client.post(
        "/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=fencer
    )
    assert response.status_code in (200, 201), response.text
    return fencer


def rows(client, organizer):
    return client.get("/api/tournaments/cup/sheet", headers=organizer).json()["rows"]


def substitute(client, organizer, target, **fields):
    payload = {"name": "Petr Náhradník", "email": "petr@example.com", **fields}
    return client.post(
        "/api/tournaments/cup/rules",
        json={"phase": "fencers", "kind": "row_substitute", "target": target, "payload": payload},
        headers=organizer,
    )


def db():
    from tests.test_matching import db_session

    return db_session()


def test_the_seat_keeps_its_place_its_symbol_and_its_money(client, auth_headers, mailbox):
    """2.7 — the substitute inherits the seat by nothing being done to it."""
    organizer = auth_headers()
    setup(client, organizer)
    register(client, auth_headers)

    before = rows(client, organizer)[0]
    response = substitute(client, organizer, before["id"])
    assert response.status_code == 201, response.text

    after = rows(client, organizer)[0]
    assert after["name"] == "Petr Náhradník"
    assert after["id"] == before["id"]
    assert after["number"] == before["number"]
    assert after["vs"] == before["vs"]
    assert after["registered_at"] == before["registered_at"]
    assert after["registration_id"] == before["registration_id"]
    assert after["state"] == before["state"]
    assert after["paid"] == before["paid"]


def test_the_registration_itself_is_untouched(client, auth_headers, mailbox):
    """2.7 — one foreign key moves and nothing else does."""
    organizer = auth_headers()
    setup(client, organizer)
    register(client, auth_headers)

    session = db()
    registration = session.scalars(select(Registration)).all()[-1]
    was = (
        registration.id,
        registration.vs,
        registration.total_amount,
        registration.registered_at,
        registration.expires_at,
        len(registration.credits),
    )
    held_by = registration.fencer_id

    substitute(client, organizer, rows(client, organizer)[0]["id"])

    session.expire_all()
    registration = session.get(Registration, was[0])
    assert (
        registration.id,
        registration.vs,
        registration.total_amount,
        registration.registered_at,
        registration.expires_at,
        len(registration.credits),
    ) == was
    assert registration.fencer_id != held_by


def test_a_queued_placement_is_inherited_queued(client, auth_headers, mailbox):
    """2.7 — the place below the line is the registration's, not the person's."""
    organizer = auth_headers()
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "LS", "weapon": "LS", "capacity": 1, "fee": 1000},
        headers=organizer,
    )
    enable_payments(client, organizer, "cup")
    publish(client, organizer, "cup")
    register(client, auth_headers, email="first@example.com", name="First Seated")
    register(client, auth_headers, email="queued@example.com", name="Queued Fencer")

    queued = [row for row in rows(client, organizer) if row["substitute_for"]][0]
    substitute(client, organizer, queued["id"], name="Petr Náhradník")

    after = [row for row in rows(client, organizer) if row["name"] == "Petr Náhradník"][0]
    assert after["substitute_for"] == ["LS"]
    assert after["disciplines"] == []


def test_withdrawal_returns_the_seat_to_the_fencer_it_was_taken_from(client, auth_headers, mailbox):
    """2.8 — the identity the rule carries is where the seat goes back to."""
    organizer = auth_headers()
    setup(client, organizer)
    register(client, auth_headers)
    row = rows(client, organizer)[0]

    rule = substitute(client, organizer, row["id"]).json()
    client.delete(f"/api/tournaments/cup/rules/{rule['id']}", headers=organizer)

    after = rows(client, organizer)[0]
    assert after["name"] == "Jan Novák"
    assert after["email"] == "jan@example.com"
    assert after["vs"] == row["vs"]
    assert after["number"] == row["number"]


def test_a_seat_substituted_twice_goes_back_one_step(client, auth_headers, mailbox):
    """2.8 — each rule returns the seat to whoever held it when it was made."""
    organizer = auth_headers()
    setup(client, organizer)
    register(client, auth_headers)
    target = rows(client, organizer)[0]["id"]

    substitute(client, organizer, target, name="First Substitute", email="one@example.com")
    second = substitute(
        client, organizer, target, name="Second Substitute", email="two@example.com"
    ).json()

    client.delete(f"/api/tournaments/cup/rules/{second['id']}", headers=organizer)

    assert rows(client, organizer)[0]["name"] == "First Substitute"


def test_a_row_with_no_registration_is_substituted_in_the_projection(client, auth_headers, mailbox):
    """2.9 — a hand-entered row that has been issued nothing."""
    organizer = auth_headers()
    setup(client, organizer, payments=False)
    client.post(
        "/api/tournaments/cup/manual-rows",
        json={"name": "Hand Entered", "disciplines": ["LS"], "nationality": "CZ"},
        headers=organizer,
    )
    target = rows(client, organizer)[0]["id"]

    response = substitute(client, organizer, target, hr_id=4321)
    assert response.status_code == 201, response.text

    row = rows(client, organizer)[0]
    assert row["id"] == target
    assert row["name"] == "Petr Náhradník"
    assert row["hr_id"] == 4321
    assert row["match_verdict"] == "confirmed"


def test_a_substitute_without_a_profile_goes_to_matching(client, auth_headers, mailbox):
    """2.9 — a name HEMA Ratings does not carry is accepted as typed."""
    organizer = auth_headers()
    setup(client, organizer)
    register(client, auth_headers)

    substitute(client, organizer, rows(client, organizer)[0]["id"])

    row = rows(client, organizer)[0]
    assert row["hr_id"] is None
    assert row["match_verdict"] == "unknown"


def test_a_deleted_row_cannot_be_handed_on(client, auth_headers, mailbox):
    """2.5 — a deleted row offers to come back, not to change hands."""
    organizer = auth_headers()
    setup(client, organizer)
    register(client, auth_headers)
    target = rows(client, organizer)[0]["id"]
    client.post(
        "/api/tournaments/cup/rules",
        json={"phase": "fencers", "kind": "row_delete", "target": target, "payload": {}},
        headers=organizer,
    )

    response = substitute(client, organizer, target)

    assert response.status_code == 409
    assert "row_is_deleted" in response.text


def test_the_substitute_cannot_be_the_fencer_already_on_the_row(client, auth_headers, mailbox):
    """2.5 — naming the holder is not a substitution."""
    organizer = auth_headers()
    setup(client, organizer)
    register(client, auth_headers)

    response = substitute(client, organizer, rows(client, organizer)[0]["id"], name="Jan Novák")

    assert response.status_code == 409
    assert "substitute_is_the_fencer_on_the_row" in response.text


def test_an_address_of_the_same_name_takes_the_seat_to_that_account(client, auth_headers, mailbox):
    """2.3 — the substitute sees the seat among their own registrations."""
    organizer = auth_headers()
    setup(client, organizer)
    register(client, auth_headers)
    auth_headers(email="petr@example.com", name="Petr Náhradník")

    substitute(client, organizer, rows(client, organizer)[0]["id"])

    session = db()
    account = session.scalar(select(Fencer).where(Fencer.email == "petr@example.com"))
    registration = session.scalars(select(Registration)).all()[-1]
    assert registration.fencer_id == account.id
    assert registration.contact_email is None


def test_an_account_already_entered_refuses_the_substitution(client, auth_headers, mailbox):
    """2.3 — one fencer holds one registration per tournament."""
    organizer = auth_headers()
    setup(client, organizer)
    register(client, auth_headers)
    register(client, auth_headers, email="petr@example.com", name="Petr Náhradník")

    row = [r for r in rows(client, organizer) if r["name"] == "Jan Novák"][0]
    response = substitute(client, organizer, row["id"])

    assert response.status_code == 409
    assert "substitute_already_registered" in response.text


def test_a_kept_address_becomes_the_seats_contact(client, auth_headers, mailbox):
    """2.3 / 1.3 — keeping an address does not hand the seat to its account."""
    organizer = auth_headers()
    setup(client, organizer)
    register(client, auth_headers)

    substitute(client, organizer, rows(client, organizer)[0]["id"], email="jan@example.com")

    session = db()
    registration = session.scalars(select(Registration)).all()[-1]
    jan = session.scalar(select(Fencer).where(Fencer.email == "jan@example.com"))
    assert registration.fencer_id != jan.id
    assert registration.fencer.email is None
    assert registration.contact_email == "jan@example.com"


def test_an_address_under_another_name_is_a_contact_not_an_identity(client, auth_headers, mailbox):
    """2.3 — the club address on a roster names the payer, not the entrant."""
    organizer = auth_headers()
    setup(client, organizer)
    register(client, auth_headers)
    auth_headers(email="klub@example.com", name="Klub Zástupce")

    substitute(client, organizer, rows(client, organizer)[0]["id"], email="klub@example.com")

    session = db()
    registration = session.scalars(select(Registration)).all()[-1]
    klub = session.scalar(select(Fencer).where(Fencer.email == "klub@example.com"))
    assert registration.fencer_id != klub.id
    assert registration.contact_email == "klub@example.com"


def body(message):
    return message.get_body(("plain",)).get_content()


def test_both_parties_are_told_where_the_address_is_new(client, auth_headers, mailbox):
    """4.4 — the arrival and the departure, one each."""
    organizer = auth_headers()
    setup(client, organizer)
    register(client, auth_headers)
    mailbox.sent.clear()

    substitute(client, organizer, rows(client, organizer)[0]["id"])

    assert [message["To"] for message in mailbox.sent] == ["petr@example.com", "jan@example.com"]
    assert "Petr Náhradník" in body(mailbox.sent[0])
    assert "Jan Novák" in body(mailbox.sent[0])
    assert "Petr Náhradník" in body(mailbox.sent[1])


def test_a_kept_address_gets_one_message(client, auth_headers, mailbox):
    """4.4 — one address is one reader, and it is the arrival they need."""
    organizer = auth_headers()
    setup(client, organizer)
    register(client, auth_headers)
    mailbox.sent.clear()

    substitute(client, organizer, rows(client, organizer)[0]["id"], email="jan@example.com")

    assert [message["To"] for message in mailbox.sent] == ["jan@example.com"]
    assert "Petr Náhradník" in body(mailbox.sent[0])


def test_the_arrival_states_what_is_outstanding_not_the_total(client, auth_headers, mailbox):
    """4.4 — a seat already paid for is inherited paid for."""
    organizer = auth_headers()
    setup(client, organizer)
    register(client, auth_headers)

    session = db()
    registration = session.scalars(select(Registration)).all()[-1]
    vs = registration.vs
    mailbox.sent.clear()

    substitute(client, organizer, rows(client, organizer)[0]["id"])

    arrival = body(mailbox.sent[0])
    assert str(vs) in arrival
    assert "1000" in arrival or "1 000" in arrival


def test_a_settled_seat_is_inherited_without_a_bill(client, auth_headers, mailbox):
    """4.4 — nothing owed is said in words, not printed as a zero."""
    organizer = auth_headers()
    setup(client, organizer, payments=False)
    register(client, auth_headers)
    mailbox.sent.clear()

    substitute(client, organizer, rows(client, organizer)[0]["id"])

    arrival = body(mailbox.sent[0])
    assert "Variabilní symbol" not in arrival
    assert list(mailbox.sent[0].iter_attachments()) == []


def test_a_manual_tournament_sends_nothing(client, auth_headers, mailbox):
    """4.4 — Squire runs nothing against a tournament it does not keep."""
    from tests.test_registrations_kept_by import set_kept_by

    organizer = auth_headers()
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    client.patch(
        "/api/tournaments/cup",
        json={
            "city": "Brno",
            "organizers": [{"name": "Org", "link": None}],
            "external_registration_url": "https://elsewhere.example/e",
        },
        headers=organizer,
    )
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "LS", "weapon": "LS", "capacity": 10, "fee": 1000},
        headers=organizer,
    )
    set_kept_by(client, organizer, "organizer")
    publish(client, organizer, "cup")
    client.post(
        "/api/tournaments/cup/manual-rows",
        json={"name": "Hand Entered", "disciplines": ["LS"], "email": "hand@example.com"},
        headers=organizer,
    )
    mailbox.sent.clear()

    response = substitute(client, organizer, rows(client, organizer)[0]["id"])

    assert response.status_code == 201, response.text
    assert mailbox.sent == []


def test_a_manual_tournament_needs_no_address(client, auth_headers, mailbox):
    """5.2 — the address is required only where Squire writes to people."""
    from tests.test_registrations_kept_by import set_kept_by

    organizer = auth_headers()
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    client.patch(
        "/api/tournaments/cup",
        json={
            "city": "Brno",
            "organizers": [{"name": "Org", "link": None}],
            "external_registration_url": "https://elsewhere.example/e",
        },
        headers=organizer,
    )
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "LS", "weapon": "LS", "capacity": 10, "fee": 1000},
        headers=organizer,
    )
    set_kept_by(client, organizer, "organizer")
    publish(client, organizer, "cup")
    client.post(
        "/api/tournaments/cup/manual-rows",
        json={"name": "Hand Entered", "disciplines": ["LS"]},
        headers=organizer,
    )

    response = substitute(client, organizer, rows(client, organizer)[0]["id"], email=None)

    assert response.status_code == 201, response.text


@pytest.mark.parametrize(
    ("fields", "reason"),
    [
        ({"name": "  "}, "substitute_name_required"),
        ({"email": "not-an-address"}, "substitute_email_malformed"),
        ({"email": None}, "substitute_email_required"),
        ({"hr_id": "1234"}, "hr_id_must_be_a_whole_number"),
    ],
)
def test_the_endpoint_names_what_it_refuses(client, auth_headers, mailbox, fields, reason):
    """5.2 — each refusal has its own reason, and none of them is generic."""
    organizer = auth_headers()
    setup(client, organizer)
    register(client, auth_headers)
    mailbox.sent.clear()

    response = substitute(client, organizer, rows(client, organizer)[0]["id"], **fields)

    assert response.status_code == 422, response.text
    assert reason in response.text
    assert mailbox.sent == []


def test_the_log_names_both_fencers(client, auth_headers, mailbox):
    """3.4 — the substitution reads as a sentence about two people."""
    organizer = auth_headers()
    setup(client, organizer)
    register(client, auth_headers)

    substitute(client, organizer, rows(client, organizer)[0]["id"])

    sheet = client.get("/api/tournaments/cup/sheet", headers=organizer).json()
    entry = [edit for edit in sheet["edits"] if edit["field"] == "_substituted"][0]
    assert entry["before"] == "Jan Novák"
    assert entry["after"] == "Petr Náhradník"
    assert sheet["rows"][0]["_substituted_for"] == "Jan Novák"
