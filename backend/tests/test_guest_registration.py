"""Registering without an account, and the manage link that stands in for one
(spec `guest-registration`)."""

import re

import pytest
from sqlalchemy import select

from app import emails, managekey
from app.mail import get_mailer
from app.main import app
from app.models import Fencer, Registration
from tests.conftest import deadline_passed, enable_payments, publish, verification_key
from tests.test_matching import db_session


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


def setup(client, organizer, slug="cup", *, capacity=10):
    client.post(
        "/api/tournaments",
        json={"slug": slug, "display_name": slug.title(), "date": "2026-12-05"},
        headers=organizer,
    )
    client.patch(
        f"/api/tournaments/{slug}",
        json={"bank_account": "CZ6508000000192000145399"},
        headers=organizer,
    )
    for discipline, cap in (("LS", capacity), ("SA", 1)):
        client.post(
            f"/api/tournaments/{slug}/disciplines",
            json={"slug": discipline, "weapon": discipline, "capacity": cap, "fee": 1000},
            headers=organizer,
        )
    enable_payments(client, organizer, slug)
    publish(client, organizer, slug)


def guest_register(client, name="Jana Malá", email="jana@example.com", slug="cup", **selection):
    return client.post(
        f"/api/tournaments/{slug}/guest-register",
        json={"disciplines": ["LS"], **selection}
        | {"guest": {"email": email, "display_name": name, "language": "cs"}},
    )


def rid(out: dict) -> int:
    """The id of the registration a guest submission answered with."""
    vs = out["registration"]["vs"]
    return db_session().scalar(select(Registration.id).where(Registration.vs == vs))


def managed(key: str) -> dict:
    return {"X-Manage-Key": key}


def opens(client, key: str) -> int:
    """The status a manage key's read of its registration answers with."""
    return client.get("/api/tournaments/cup/my-registration", headers=managed(key)).status_code


def body(message) -> str:
    return message.get_body(("plain",)).get_content()


def link_in(message) -> str | None:
    found = re.search(r"/t/[\w-]+/manage#(\S+)", body(message))
    return found.group(1) if found else None


def test_a_guest_registration_is_an_ordinary_registration(client, auth_headers, mailbox):
    setup(client, auth_headers())
    client.post(
        "/api/tournaments/cup/register",
        json={"disciplines": ["SA"]},
        headers=auth_headers(email="a@example.com", name="Adam Plný"),
    )
    mailbox.sent.clear()

    response = guest_register(client, disciplines=["LS", "SA"])
    assert response.status_code == 201, response.text
    out = response.json()
    registration = out["registration"]
    assert registration["vs"]
    assert registration["expires_at"] is not None
    queued = {e["slug"]: e["is_substitute"] for e in registration["entries"]}
    assert queued == {"LS": False, "SA": True}

    # the confirmation goes to the address given, carrying the key returned
    assert [m["To"] for m in mailbox.sent] == ["jana@example.com"]
    assert link_in(mailbox.sent[0]) == out["manage_key"]
    record = db_session().scalar(select(Fencer).where(Fencer.email == "jana@example.com"))
    assert record.password_hash is None
    assert record.display_name == "Jana Malá"


def test_a_guest_and_an_account_are_priced_alike(client, auth_headers, mailbox):
    setup(client, auth_headers())
    guest = guest_register(client).json()["registration"]
    account = client.post(
        "/api/tournaments/cup/register",
        json={"disciplines": ["LS"]},
        headers=auth_headers(email="b@example.com", name="Bára Účtová"),
    ).json()
    assert guest["total_amount"] == account["total_amount"]
    assert bool(guest["expires_at"]) == bool(account["expires_at"])


def test_a_parent_enters_two_children_from_one_address(client, auth_headers, mailbox):
    setup(client, auth_headers())
    anna = guest_register(client, name="Anna Nová", email="rodic@example.com").json()
    petr = guest_register(client, name="Petr Nový", email="rodic@example.com").json()

    session = db_session()
    anna_reg = session.get(Registration, rid(anna))
    petr_reg = session.get(Registration, rid(petr))
    assert anna_reg.fencer.email == "rodic@example.com"
    assert anna_reg.contact_email is None
    assert petr_reg.fencer.email is None
    assert petr_reg.contact_email == "rodic@example.com"
    assert [m["To"] for m in mailbox.sent] == ["rodic@example.com", "rodic@example.com"]
    assert [link_in(m) for m in mailbox.sent] == [anna["manage_key"], petr["manage_key"]]


def test_the_same_child_twice_is_refused(client, auth_headers, mailbox):
    setup(client, auth_headers())
    guest_register(client, name="Anna Nová", email="rodic@example.com")
    guest_register(client, name="Petr Nový", email="rodic@example.com")

    for name in ("Petr Nový", "Nový Petr", "Anna Nová"):
        again = guest_register(client, name=name, email="rodic@example.com")
        assert again.status_code == 409
        assert again.json()["detail"] == "already_registered"
    assert len(db_session().scalars(select(Registration)).all()) == 2


def test_a_returning_guest_is_recognized(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    setup(client, organizer, slug="open")
    first = guest_register(client).json()
    session = db_session()
    record = session.get(Registration, rid(first)).fencer
    record.hr_id = 10234
    session.commit()
    record_id = record.id

    second = guest_register(client, name="Malá Jana", slug="open").json()
    session = db_session()
    again = session.get(Registration, rid(second)).fencer
    assert again.id == record_id
    assert again.display_name == "Jana Malá"
    assert again.hr_id == 10234


def test_an_accounts_address_is_refused_at_check_and_at_submit(client, auth_headers, mailbox):
    setup(client, auth_headers())
    auth_headers(email="eva@example.com", name="Eva Účtová")

    checked = client.post("/api/auth/guest-check", json={"email": "eva@example.com"})
    assert checked.status_code == 409
    assert checked.json()["detail"] == "email_has_account"
    assert client.post("/api/auth/guest-check", json={"email": "x@example.com"}).status_code == 204

    mailbox.sent.clear()
    submitted = guest_register(client, name="Eva Účtová", email="eva@example.com")
    assert submitted.status_code == 409
    assert submitted.json()["detail"] == "email_has_account"
    assert db_session().scalars(select(Registration)).all() == []
    assert mailbox.sent == []


def test_a_key_opens_its_registration_and_nothing_else(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    setup(client, organizer, slug="open")
    jana = guest_register(client).json()
    other = guest_register(client, name="Karel Jiný", email="karel@example.com").json()
    guest_register(client, slug="open")
    key = jana["manage_key"]

    mine = client.get("/api/tournaments/cup/my-registration", headers=managed(key))
    assert mine.status_code == 200
    assert mine.json()["vs"] == jana["registration"]["vs"]
    assert (
        client.get("/api/tournaments/cup/my-registration/payment", headers=managed(key)).status_code
        == 200
    )

    # one registration's key on another tournament, a forged one, an older one
    refusals = [
        client.get("/api/tournaments/open/my-registration", headers=managed(key)),
        client.get(
            "/api/tournaments/cup/my-registration",
            headers=managed(f"{rid(other)}.{key.partition('.')[2]}"),
        ),
        client.get("/api/tournaments/cup/my-registration", headers=managed("999999." + "A" * 32)),
    ]
    for refused in refusals:
        assert refused.status_code == 404
        assert refused.json()["detail"] == "manage_key_invalid"

    # no account screen opens to it
    assert client.get("/api/account", headers=managed(key)).status_code == 401
    assert client.get("/api/tournaments?tab=mine", headers=managed(key)).status_code in (401, 403)


def test_a_guest_amends_and_cancels_through_the_link(client, auth_headers, mailbox):
    setup(client, auth_headers())
    key = guest_register(client).json()["manage_key"]
    mailbox.sent.clear()

    amended = client.post(
        "/api/tournaments/cup/my-registration/amend",
        json={"disciplines": ["LS", "SA"]},
        headers=managed(key),
    )
    assert amended.status_code == 200, amended.text
    assert link_in(mailbox.sent[-1]) == key

    cancelled = client.post("/api/tournaments/cup/my-registration/cancel", headers=managed(key))
    assert cancelled.status_code == 200
    # a cancelled registration keeps its key and is read through it
    read = client.get("/api/tournaments/cup/my-registration", headers=managed(key))
    assert read.status_code == 200
    assert read.json()["state"] == "cancelled"


def test_the_amendment_window_binds_through_the_link(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    key = guest_register(client).json()["manage_key"]
    client.patch(
        "/api/tournaments/cup",
        json={"amendments_close": deadline_passed().isoformat()},
        headers=organizer,
    )
    refused = client.post(
        "/api/tournaments/cup/my-registration/amend",
        json={"disciplines": ["LS", "SA"]},
        headers=managed(key),
    )
    assert refused.status_code == 403
    assert opens(client, key) == 200


# what a sender takes beyond the registration: a reinstatement states the
# payment that caused it, in its lane
EXTRA: dict[str, tuple[str, int]] = {"send_reservation_reinstated": ("local", 100000)}


SENDERS = [
    "send_registration_confirmation",
    "send_payment_reminder",
    "send_reservation_expired",
    "send_payment_received",
    "send_amendment_confirmation",
    "send_reservation_reinstated",
    "send_payment_after_expiry",
]


@pytest.mark.parametrize("name", SENDERS)
def test_every_guest_send_carries_the_link_and_no_account_send_does(
    client, auth_headers, mailbox, name
):
    setup(client, auth_headers())
    key = guest_register(client).json()["manage_key"]
    client.post(
        "/api/tournaments/cup/register",
        json={"disciplines": ["LS"]},
        headers=auth_headers(email="b@example.com", name="Bára Účtová"),
    )
    session = db_session()
    guest, account = sorted(session.scalars(select(Registration)).all(), key=lambda r: r.id)
    mailbox.sent.clear()

    for registration in (guest, account):
        getattr(emails, name)(
            mailbox,
            registration.tournament,
            registration.fencer,
            registration,
            *EXTRA.get(name, ()),
        )

    assert [m["To"] for m in mailbox.sent] == ["jana@example.com", "b@example.com"]
    assert link_in(mailbox.sent[0]) == key
    assert link_in(mailbox.sent[1]) is None


def test_an_organizers_cancellation_carries_the_link(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    out = guest_register(client).json()
    mailbox.sent.clear()
    client.post(
        f"/api/tournaments/cup/registrations/{rid(out)}/cancel",
        json={},
        headers=organizer,
    )
    assert link_in(mailbox.sent[-1]) == out["manage_key"]


def substitute(client, organizer, **payload):
    target = client.get("/api/tournaments/cup/sheet", headers=organizer).json()["rows"][0]["id"]
    return client.post(
        "/api/tournaments/cup/rules",
        json={"phase": "fencers", "kind": "row_substitute", "target": target, "payload": payload},
        headers=organizer,
    )


def test_substitution_to_a_new_address_kills_the_old_key(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    old = guest_register(client).json()["manage_key"]
    mailbox.sent.clear()

    response = substitute(client, organizer, name="Petr Náhradník", email="petr@example.com")
    assert response.status_code == 201, response.text

    arrival = next(m for m in mailbox.sent if m["To"] == "petr@example.com")
    new = link_in(arrival)
    assert new is not None and new != old
    assert opens(client, old) == 404
    assert opens(client, new) == 200
    # the departing holder is told, and handed no link to a seat no longer theirs
    departure = next(m for m in mailbox.sent if m["To"] == "jana@example.com")
    assert link_in(departure) is None


def test_substitution_keeping_the_address_keeps_the_key(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    key = guest_register(client).json()["manage_key"]
    mailbox.sent.clear()

    substitute(client, organizer, name="Petr Náhradník", email="jana@example.com")

    assert link_in(mailbox.sent[-1]) == key
    assert opens(client, key) == 200


def test_substitution_onto_an_account_ends_the_link(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    key = guest_register(client).json()["manage_key"]
    auth_headers(email="petr@example.com", name="Petr Náhradník")
    mailbox.sent.clear()

    substitute(client, organizer, name="Petr Náhradník", email="petr@example.com")

    assert all(link_in(m) is None for m in mailbox.sent)
    assert opens(client, key) == 404


def test_verified_signup_on_the_records_address_kills_the_key(client, auth_headers, mailbox):
    setup(client, auth_headers())
    out = guest_register(client).json()
    client.post(
        "/api/auth/signup",
        json={
            "email": "jana@example.com",
            "password": "correct-horse",
            "display_name": "Jana Malá",
        },
    )
    token = client.post(
        "/api/auth/verify", json={"key": verification_key(mailbox.sent[-1])}
    ).json()["token"]

    refused = client.get("/api/tournaments/cup/my-registration", headers=managed(out["manage_key"]))
    assert refused.status_code == 404
    mine = client.get(
        "/api/tournaments/cup/my-registration", headers={"Authorization": f"Bearer {token}"}
    )
    assert mine.json()["vs"] == out["registration"]["vs"]


def test_a_signup_on_a_contact_address_takes_nothing_over(client, auth_headers, mailbox):
    """fencer-accounts: a contact address is not an identity."""
    setup(client, auth_headers())
    guest_register(client, name="Anna Nová", email="rodic@example.com")
    petr = guest_register(client, name="Petr Nový", email="rodic@example.com").json()
    # Anna's record holds the address; the parent signs up on it under their own
    # name, which takes Anna's record over and leaves Petr's registration a guest's
    client.post(
        "/api/auth/signup",
        json={
            "email": "rodic@example.com",
            "password": "correct-horse",
            "display_name": "Anna Nová",
        },
    )
    client.post("/api/auth/verify", json={"key": verification_key(mailbox.sent[-1])})

    session = db_session()
    petr_reg = session.get(Registration, rid(petr))
    assert petr_reg.fencer.password_hash is None
    assert petr_reg.contact_email == "rodic@example.com"
    assert managekey.key_for(petr_reg) == petr["manage_key"]


def test_a_dead_key_and_a_missing_one_are_refused_alike(client, auth_headers, mailbox):
    setup(client, auth_headers())
    out = guest_register(client).json()
    session = db_session()
    registration = session.get(Registration, rid(out))
    managekey.rotate(registration)
    session.commit()

    stale = client.get("/api/tournaments/cup/my-registration", headers=managed(out["manage_key"]))
    missing = client.get(
        "/api/tournaments/cup/my-registration", headers=managed("424242." + "A" * 32)
    )
    assert stale.status_code == missing.status_code == 404
    assert stale.json() == missing.json()


def test_the_manage_screen_is_told_the_guests_language(client, auth_headers, mailbox):
    setup(client, auth_headers())
    key = guest_register(client).json()["manage_key"]  # the form chose "cs"

    through_link = client.get("/api/tournaments/cup/my-registration", headers=managed(key))
    assert through_link.json()["language"] == "cs"

    account = auth_headers(email="b@example.com", name="Bára Účtová")
    client.post("/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=account)
    own = client.get("/api/tournaments/cup/my-registration", headers=account)
    assert own.json()["language"] is None


def resend(client, organizer, registration_id):
    return client.post(
        f"/api/tournaments/cup/registrations/{registration_id}/manage-link", headers=organizer
    )


def test_the_organizer_sends_a_guest_their_link_again(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    petr = guest_register(client, name="Petr Nový", email="rodic@example.com").json()
    mailbox.sent.clear()

    assert resend(client, organizer, rid(petr)).status_code == 204

    # the current key, so the link mailed at registration keeps working too
    assert [m["To"] for m in mailbox.sent] == ["rodic@example.com"]
    assert link_in(mailbox.sent[0]) == petr["manage_key"]
    assert opens(client, petr["manage_key"]) == 200
    rows = client.get("/api/tournaments/cup/sheet", headers=organizer).json()["rows"]
    assert [row["guest"] for row in rows] == [True]


def test_only_a_guest_registration_has_a_link_to_send(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    client.post(
        "/api/tournaments/cup/register",
        json={"disciplines": ["LS"]},
        headers=auth_headers(email="b@example.com", name="Bára Účtová"),
    )
    registration_id = db_session().scalars(select(Registration.id)).one()
    mailbox.sent.clear()

    refused = resend(client, organizer, registration_id)
    assert refused.status_code == 409
    assert refused.json()["detail"] == "not_a_guest_registration"
    assert mailbox.sent == []


def test_a_fencer_cannot_send_links(client, auth_headers, mailbox):
    setup(client, auth_headers())
    out = guest_register(client).json()
    stranger = auth_headers(email="x@example.com", name="Xaver Cizí")
    assert resend(client, stranger, rid(out)).status_code in (403, 404)
