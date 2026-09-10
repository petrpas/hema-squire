"""An organizer's correction to the disciplines of a registration that exists
(spec `discipline-amendment`).

The disciplines cell on the fencer list used to open only for a row with no
registration behind it. Issuing became a step of payment intake, so every
imported row has one within seconds of arriving and the cell opened for nothing.
It opens for every row now, and where a registration stands behind the row the
edit amends the registration — the same operation the fencer's own amendment
performs, reached from the other side.

What these are watching for is the money. A correction that moved the table and
left the registration billing the old selection is the defect the change exists
to remove; one that repriced the whole registration at today's fees is the
defect `imported-registrations` forbids.
"""

import pytest
from conftest import enable_payments, publish, set_fio_token
from sqlalchemy import select

from app.importer import get_import_parser
from app.mail import get_mailer
from app.main import app
from app.models import PaymentEvent, Registration, RegistrationState
from tests.test_issuing import (
    CollectingMailer,
    RosterParser,
    import_roster,
    issue,
    row,
    sheet_rows,
)
from tests.test_matching import db_session


@pytest.fixture
def mailbox():
    """Every test here takes it: an organizer's correction that wrote to a
    fencer is a fact worth catching even where the test is about something
    else, and an uncollected mailer would post it into the outbox."""
    mailer = CollectingMailer()
    app.dependency_overrides[get_mailer] = lambda: mailer
    yield mailer
    app.dependency_overrides.pop(get_mailer, None)


IBAN = "CZ6508000000192000145399"


def setup(client, organizer, *, sb_capacity=20, early_fee=None, early_until=None):
    """A tournament offering two individual disciplines, SA at 800 and SB at
    500. `sb_capacity` is how the fullness tests make SB genuinely full."""
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    enable_payments(client, organizer, "cup")
    body = {"slug": "SA", "weapon": "SA", "capacity": 50, "fee": 800}
    if early_fee is not None:
        body["fee_early"] = early_fee
    client.post("/api/tournaments/cup/disciplines", json=body, headers=organizer)
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "SB", "weapon": "SB", "capacity": sb_capacity, "fee": 500},
        headers=organizer,
    )
    patch = {
        "location": "Brno",
        "organizers": [{"name": "Cup Org", "link": None}],
        "bank_account": IBAN,
    }
    if early_until is not None:
        patch["early_bird_until"] = early_until
    response = client.patch("/api/tournaments/cup", json=patch, headers=organizer)
    set_fio_token(client, organizer, "cup")
    assert response.status_code == 200, response.text
    publish(client, organizer, "cup")
    app.dependency_overrides[get_import_parser] = lambda: RosterParser()


def amend(client, organizer, row_id, slugs, kind="registration_amendment"):
    return client.post(
        "/api/tournaments/cup/rules",
        json={
            "phase": "fencers",
            "kind": kind,
            "target": row_id,
            "payload": {"field": "disciplines", "value": slugs},
        },
        headers=organizer,
    )


def registration_of(row_id):
    return db_session().scalar(select(Registration).where(Registration.source_row_id == row_id))


def selection(registration):
    """(seated, substitute) slugs, which is what placement means here."""
    seated = sorted(e.discipline.slug for e in registration.entries if not e.is_substitute)
    subs = sorted(e.discipline.slug for e in registration.entries if e.is_substitute)
    return seated, subs


def issued_row(client, organizer, rows=None):
    """One imported, issued row: the shape the organizer meets after an
    import, and the one the cell used to be closed on."""
    import_roster(client, organizer, rows or [row("Jan", "jan@example.com")])
    issue(client, organizer)
    return sheet_rows(client, organizer)[0]


# --- what the correction is worth ------------------------------------------


def test_early_bird_survives_the_correction(client, auth_headers, mailbox):
    """The load-bearing test of the whole change. Repricing at today's fees
    also "changes the total"; only an early-bird registration corrected after
    the deadline tells the two apart."""
    organizer = auth_headers()
    setup(client, organizer, early_fee=600, early_until="2026-05-01")
    listed = issued_row(client, organizer)
    assert registration_of(listed["id"]).total_amount == 600

    assert amend(client, organizer, listed["id"], ["SA", "SB"]).status_code == 201

    # 600 + 500, not 800 + 500: the correction prices at the registration's own
    # registration moment, which is April, not at today's full fee
    assert registration_of(listed["id"]).total_amount == 1100


def test_the_money_follows_the_table(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    listed = issued_row(client, organizer)

    assert amend(client, organizer, listed["id"], ["SB"]).status_code == 201

    registration = registration_of(listed["id"])
    assert selection(registration) == (["SB"], [])
    assert registration.total_amount == 500
    # and the table states the same disciplines, since it reads them off the
    # registration it just amended
    assert sheet_rows(client, organizer)[0]["disciplines"] == ["SB"]


# --- where the correction is placed ----------------------------------------


def test_an_issued_correction_is_seated_and_billed(client, auth_headers, mailbox):
    """Capacity does not apply to an issued registration. A substitute
    placement is not billed, so queueing this would make the fencer free."""
    organizer = auth_headers()
    setup(client, organizer, sb_capacity=1)
    listed = issued_row(
        client,
        organizer,
        [row("Jan", "jan@example.com"), row("Eva", "eva@example.com", disciplines="SB")],
    )
    # Eva holds SB's only seat
    assert amend(client, organizer, listed["id"], ["SA", "SB"]).status_code == 201

    registration = registration_of(listed["id"])
    assert selection(registration) == (["SA", "SB"], [])
    assert registration.total_amount == 1300  # seated *and* billed


def test_an_in_app_correction_queues(client, auth_headers, mailbox):
    """A registration the fencer made themselves follows the amendment rule:
    a full discipline joins as a substitute placement in place."""
    organizer = auth_headers()
    setup(client, organizer, sb_capacity=1)
    issued_row(client, organizer, [row("Eva", "eva@example.com", disciplines="SB")])
    fencer = auth_headers("jan@example.com")
    assert (
        client.post(
            "/api/tournaments/cup/register", json={"disciplines": ["SA"]}, headers=fencer
        ).status_code
        == 201
    )

    listed = [r for r in sheet_rows(client, organizer) if r["name"].startswith("jan")]
    listed = (
        listed[0]
        if listed
        else [r for r in sheet_rows(client, organizer) if r["id"].startswith("reg:")][0]
    )
    assert amend(client, organizer, listed["id"], ["SA", "SB"]).status_code == 201

    registration = db_session().scalar(
        select(Registration).where(Registration.id == int(listed["id"][len("reg:") :]))
    )
    # SB queued, and SA — the placement the fencer already held — untouched
    assert selection(registration) == (["SA"], ["SB"])


# --- withdrawal ------------------------------------------------------------


def rules_for(client, organizer):
    return client.get("/api/tournaments/cup/rules?phase=fencers", headers=organizer).json()


def test_undoing_a_correction_restores_the_price(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    listed = issued_row(client, organizer)
    created = amend(client, organizer, listed["id"], ["SA", "SB"]).json()
    assert registration_of(listed["id"]).total_amount == 1300

    assert (
        client.delete(f"/api/tournaments/cup/rules/{created['id']}", headers=organizer).status_code
        == 204
    )

    registration = registration_of(listed["id"])
    assert selection(registration) == (["SA"], [])
    assert registration.total_amount == 800


def test_withdrawing_the_first_of_two_amendments(client, auth_headers, mailbox):
    """Withdrawal is a replay of what remains, not an undo of what went. An
    implementation that reversed the last operation passes the test above and
    fails this one."""
    organizer = auth_headers()
    setup(client, organizer)
    listed = issued_row(client, organizer)
    first = amend(client, organizer, listed["id"], ["SA", "SB"]).json()
    amend(client, organizer, listed["id"], ["SB"])

    assert (
        client.delete(f"/api/tournaments/cup/rules/{first['id']}", headers=organizer).status_code
        == 204
    )

    registration = registration_of(listed["id"])
    assert selection(registration) == (["SB"], [])  # what the second alone produces
    assert registration.total_amount == 500


# --- who is told -----------------------------------------------------------


def subjects(mailbox):
    return [message.subject for message in mailbox.sent]


def test_a_dearer_correction_mails_once_and_a_cheaper_one_mails_nobody(
    client, auth_headers, mailbox
):
    organizer = auth_headers()
    setup(client, organizer)
    listed = issued_row(client, organizer)
    assert mailbox.sent == []  # issuing itself mails nobody

    amend(client, organizer, listed["id"], ["SA", "SB"])
    assert len(mailbox.sent) == 1

    amend(client, organizer, listed["id"], ["SB"])
    assert len(mailbox.sent) == 1  # the cheaper correction adds nothing


def test_correcting_a_whole_imported_roster_sends_no_post(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer, sb_capacity=50)
    import_roster(
        client,
        organizer,
        [row(f"F{n}", f"f{n}@example.com", disciplines="SA|SB") for n in range(40)],
    )
    issue(client, organizer)

    for listed in sheet_rows(client, organizer):
        assert amend(client, organizer, listed["id"], ["SA"]).status_code == 201

    assert mailbox.sent == []


def test_an_overpaid_registration_is_marked_for_refund(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    listed = issued_row(client, organizer, [row("Jan", "jan@example.com", disciplines="SA|SB")])
    registration = registration_of(listed["id"])
    response = client.post(
        "/api/tournaments/cup/payments/manual",
        json={
            "registration_id": registration.id,
            "amount": "1300.00",
            "currency": "CZK",
            "received_on": "2026-08-01",
            "method": "cash",
        },
        headers=organizer,
    )
    assert response.status_code in (200, 201), response.text
    assert registration_of(listed["id"]).state is RegistrationState.RESERVED

    amend(client, organizer, listed["id"], ["SB"])

    registration = registration_of(listed["id"])
    assert registration.total_amount == 500
    assert registration.refund_state is not None
    assert registration.refund_state.value == "pending"


# --- what the correction is not bound by -----------------------------------


def test_corrected_after_the_amendment_deadline(client, auth_headers, mailbox):
    """The window governs the fencer. The days before the export, once the
    entries have settled, are exactly when the organizer needs the cell."""
    organizer = auth_headers()
    setup(client, organizer)
    listed = issued_row(client, organizer)
    client.patch("/api/tournaments/cup", json={"amendments_close": "2026-05-01"}, headers=organizer)

    assert amend(client, organizer, listed["id"], ["SB"]).status_code == 201
    assert registration_of(listed["id"]).total_amount == 500


def test_a_dormant_registration_is_still_correctable(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    listed = issued_row(client, organizer)
    assert registration_of(listed["id"]).clocks_dormant is True

    assert amend(client, organizer, listed["id"], ["SA", "SB"]).status_code == 201
    assert registration_of(listed["id"]).total_amount == 1300


def test_an_expired_registration_is_not_corrected_in_the_table(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    listed = issued_row(client, organizer)
    session = db_session()
    registration = session.scalar(
        select(Registration).where(Registration.source_row_id == listed["id"])
    )
    registration.state = RegistrationState.EXPIRED
    session.commit()

    response = amend(client, organizer, listed["id"], ["SB"])
    assert response.status_code == 409
    assert response.json()["detail"] == "registration_not_live"


# --- the shape of the rule -------------------------------------------------


def test_a_disciplines_field_edit_is_refused_where_a_registration_stands(
    client, auth_headers, mailbox
):
    organizer = auth_headers()
    setup(client, organizer)
    listed = issued_row(client, organizer)

    response = amend(client, organizer, listed["id"], ["SB"], kind="field_edit")

    assert response.status_code == 409
    assert response.json()["detail"] == "row_has_registration"
    assert registration_of(listed["id"]).total_amount == 800


def test_a_field_edit_still_corrects_a_row_that_has_no_registration(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    import_roster(client, organizer, [row("Jan", "jan@example.com")])
    listed = sheet_rows(client, organizer)[0]

    assert amend(client, organizer, listed["id"], ["SB"], kind="field_edit").status_code == 201
    assert sheet_rows(client, organizer)[0]["disciplines"] == ["SB"]


def test_an_unknown_slug_is_refused_at_the_console(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    listed = issued_row(client, organizer)

    response = amend(client, organizer, listed["id"], ["nope"])

    assert response.status_code == 422
    assert response.json()["detail"]["slugs"] == ["nope"]


def test_the_correction_reads_in_the_manual_edits_log(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    listed = issued_row(client, organizer)

    amend(client, organizer, listed["id"], ["SA", "SB"])

    body = client.get("/api/tournaments/cup/sheet", headers=organizer).json()
    entry = [e for e in body["edits"] if e["field"] == "disciplines"]
    assert len(entry) == 1
    assert entry[0]["before"] == ["SA"]
    assert entry[0]["after"] == ["SA", "SB"]
    assert entry[0]["target"] == listed["id"]


def test_an_amendment_records_a_payment_event(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    listed = issued_row(client, organizer)

    amend(client, organizer, listed["id"], ["SA", "SB"])

    session = db_session()
    kinds = [event.kind for event in session.scalars(select(PaymentEvent))]
    assert "registration_amended" in kinds


def test_the_console_is_told_what_changed_about_the_money(client, auth_headers, mailbox):
    """The half of the edit the organizer cannot see in the cell."""
    organizer = auth_headers()
    setup(client, organizer)
    listed = issued_row(client, organizer)

    reported = amend(client, organizer, listed["id"], ["SA", "SB"]).json()["amendment"]

    assert reported["previous_total"] == "800"
    assert reported["total"] == "1300"
    assert reported["notified"] is True


def test_a_cheaper_correction_reports_no_letter(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    listed = issued_row(client, organizer, [row("Jan", "jan@example.com", disciplines="SA|SB")])

    reported = amend(client, organizer, listed["id"], ["SA"]).json()["amendment"]

    assert reported["previous_total"] == "1300"
    assert reported["total"] == "800"
    assert reported["notified"] is False
