"""An organizer's correction to what a registration borrows (spec
`discipline-amendment`, An organizer may change what a registration borrows).

The second priced field the console can correct, and the reason the rule kind
stopped being about disciplines. What these watch for is the same thing the
discipline amendment's tests watch for — that the money moves with the table —
plus two properties that only appear once a registration has more than one
amendable field: that an amendment of one field does not disturb another, and
that correcting the rentals does not quietly drop the fencer's afterparty.
"""

import pytest
from conftest import enable_payments, publish, set_fio_token
from sqlalchemy import select

from app.importer import get_import_parser
from app.mail import get_mailer
from app.main import app
from app.models import Registration
from tests.test_discipline_amendment import registration_of, rules_for
from tests.test_issuing import (
    CollectingMailer,
    RosterParser,
    import_roster,
    issue,
    row,
    sheet_rows,
)
from tests.test_matching import db_session

IBAN = "CZ6508000000192000145399"


@pytest.fixture
def mailbox():
    mailer = CollectingMailer()
    app.dependency_overrides[get_mailer] = lambda: mailer
    yield mailer
    app.dependency_overrides.pop(get_mailer, None)


def setup(client, organizer):
    """A tournament priced by items: SA at 800, SB at 500, two rental items at
    50 each and an afterparty at 250."""
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    enable_payments(client, organizer, "cup")
    for slug, weapon, fee in (("SA", "SA", 800), ("SB", "SB", 500)):
        client.post(
            "/api/tournaments/cup/disciplines",
            json={"slug": slug, "weapon": weapon, "capacity": 50, "fee": fee},
            headers=organizer,
        )
    for name, category, price in (
        ("Sabre", "rental", 50),
        ("Buckler", "rental", 50),
        ("Afterparty", "afterparty", 250),
    ):
        response = client.post(
            "/api/tournaments/cup/extra-items",
            json={"name": name, "category": category, "price": price, "max_qty": 1},
            headers=organizer,
        )
        assert response.status_code == 201, response.text
    assert client.patch(
        "/api/tournaments/cup",
        json={
            "location": "Brno",
            "organizers": [{"name": "Cup Org", "link": None}],
            "bank_account": IBAN,
        },
        headers=organizer,
    ).status_code == 200
    set_fio_token(client, organizer, "cup")
    publish(client, organizer, "cup")
    app.dependency_overrides[get_import_parser] = lambda: RosterParser()


def amend(client, organizer, row_id, value, field="weapon_rentals", kind=None):
    return client.post(
        "/api/tournaments/cup/rules",
        json={
            "phase": "fencers",
            "kind": kind or "registration_amendment",
            "target": row_id,
            "payload": {"field": field, "value": value},
        },
        headers=organizer,
    )


def issued_row(client, organizer, rows=None):
    import_roster(client, organizer, rows or [row("Jan", "jan@example.com")])
    issue(client, organizer)
    return sheet_rows(client, organizer)[0]


def rentals_of(registration: Registration) -> list[str]:
    return sorted(
        s.item.name for s in registration.extra_selections if s.item.category.value == "rental"
    )


def extras_of(registration: Registration) -> list[str]:
    return sorted(s.item.name for s in registration.extra_selections)


# --- the money -------------------------------------------------------------


def test_the_money_follows_the_borrowed_item(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    listed = issued_row(client, organizer)
    assert registration_of(listed["id"]).total_amount == 800

    assert amend(client, organizer, listed["id"], ["Sabre"]).status_code == 201

    registration = registration_of(listed["id"])
    assert rentals_of(registration) == ["Sabre"]
    assert registration.weapon_rentals == ["Sabre"]
    assert registration.total_amount == 850


def test_removing_a_rental_lowers_the_total(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    listed = issued_row(
        client, organizer, [row("Jan", "jan@example.com", borrow="Sabre|Buckler")]
    )
    assert registration_of(listed["id"]).total_amount == 900

    amend(client, organizer, listed["id"], [])

    registration = registration_of(listed["id"])
    assert rentals_of(registration) == []
    assert registration.weapon_rentals == []
    assert registration.total_amount == 800


def test_a_rentals_correction_leaves_the_afterparty_alone(client, auth_headers, mailbox):
    """`apply_amendment` replaces the extras it is given in full, so a
    correction that passed only the rentals would drop the fencer's evening —
    a change nobody asked for, made by an edit about sabres."""
    organizer = auth_headers()
    setup(client, organizer)
    listed = issued_row(
        client, organizer, [row("Jan", "jan@example.com", afterparty="y")]
    )
    assert registration_of(listed["id"]).total_amount == 1050

    amend(client, organizer, listed["id"], ["Sabre"])

    registration = registration_of(listed["id"])
    assert extras_of(registration) == ["Afterparty", "Sabre"]
    assert registration.total_amount == 1100


def test_an_item_the_tournament_does_not_lend_is_kept_and_not_billed(
    client, auth_headers, mailbox
):
    """The organizer is correcting a record of what a fencer asked for, and
    refusing the correction would leave the worse record standing (owner
    decision, 2026-09-06). The row says which item nothing prices."""
    organizer = auth_headers()
    setup(client, organizer)
    listed = issued_row(client, organizer)

    assert amend(client, organizer, listed["id"], ["Sabre", "Sword"]).status_code == 201

    registration = registration_of(listed["id"])
    assert rentals_of(registration) == ["Sabre"]
    assert registration.weapon_rentals == ["Sabre", "Sword"]
    assert registration.total_amount == 850
    assert sheet_rows(client, organizer)[0]["unpriced_rentals"] == ["Sword"]


# --- two fields on one row -------------------------------------------------


def test_two_fields_corrected_on_one_row(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    listed = issued_row(client, organizer)

    amend(client, organizer, listed["id"], ["SA", "SB"], field="disciplines")
    amend(client, organizer, listed["id"], ["Sabre"])

    registration = registration_of(listed["id"])
    assert sorted(e.discipline.slug for e in registration.entries) == ["SA", "SB"]
    assert rentals_of(registration) == ["Sabre"]
    assert registration.total_amount == 1350


def test_withdrawing_one_field_leaves_the_other(client, auth_headers, mailbox):
    """The test a per-row replay fails. Rebuilding the row from the amendments
    that remain, without asking which field each of them is about, restores the
    issued disciplines and the issued rentals together — silently undoing a
    correction nobody withdrew."""
    organizer = auth_headers()
    setup(client, organizer)
    listed = issued_row(client, organizer)
    disciplines = amend(
        client, organizer, listed["id"], ["SA", "SB"], field="disciplines"
    ).json()
    amend(client, organizer, listed["id"], ["Sabre"])

    assert client.delete(
        f"/api/tournaments/cup/rules/{disciplines['id']}", headers=organizer
    ).status_code == 204

    registration = registration_of(listed["id"])
    assert sorted(e.discipline.slug for e in registration.entries) == ["SA"]
    assert rentals_of(registration) == ["Sabre"]
    assert registration.total_amount == 850


def test_undoing_a_rentals_correction_restores_the_price(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    listed = issued_row(
        client, organizer, [row("Jan", "jan@example.com", borrow="Sabre")]
    )
    created = amend(client, organizer, listed["id"], ["Sabre", "Buckler"]).json()
    assert registration_of(listed["id"]).total_amount == 900

    assert client.delete(
        f"/api/tournaments/cup/rules/{created['id']}", headers=organizer
    ).status_code == 204

    registration = registration_of(listed["id"])
    assert rentals_of(registration) == ["Sabre"]
    assert registration.weapon_rentals == ["Sabre"]
    assert registration.total_amount == 850


# --- who is told -----------------------------------------------------------


def test_a_dearer_correction_mails_once_and_a_cheaper_one_mails_nobody(
    client, auth_headers, mailbox
):
    organizer = auth_headers()
    setup(client, organizer)
    listed = issued_row(client, organizer)

    amend(client, organizer, listed["id"], ["Sabre"])
    assert len(mailbox.sent) == 1

    amend(client, organizer, listed["id"], [])
    assert len(mailbox.sent) == 1


# --- the shape of the rule -------------------------------------------------


def test_a_rentals_field_edit_is_refused_where_a_registration_stands(
    client, auth_headers, mailbox
):
    organizer = auth_headers()
    setup(client, organizer)
    listed = issued_row(client, organizer)

    response = amend(client, organizer, listed["id"], ["Sabre"], kind="field_edit")

    assert response.status_code == 409
    assert response.json()["detail"] == "row_has_registration"
    assert registration_of(listed["id"]).total_amount == 800


def test_a_field_edit_still_corrects_a_row_that_has_no_registration(
    client, auth_headers, mailbox
):
    organizer = auth_headers()
    setup(client, organizer)
    import_roster(client, organizer, [row("Jan", "jan@example.com")])
    listed = sheet_rows(client, organizer)[0]

    assert amend(
        client, organizer, listed["id"], ["Sabre"], kind="field_edit"
    ).status_code == 201
    assert sheet_rows(client, organizer)[0]["weapon_rentals"] == ["Sabre"]


def test_a_field_that_is_not_amendable_is_refused(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    listed = issued_row(client, organizer)

    response = amend(client, organizer, listed["id"], "Novák", field="name")

    assert response.status_code == 422
    assert response.json()["detail"] == "field_is_not_amendable"


def test_rentals_must_be_a_list_of_names(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    listed = issued_row(client, organizer)

    response = amend(client, organizer, listed["id"], "Sabre")

    assert response.status_code == 422
    assert response.json()["detail"] == "rentals_must_be_a_list"


def test_the_correction_reads_in_the_manual_edits_log(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    listed = issued_row(client, organizer)

    amend(client, organizer, listed["id"], ["Sabre"])

    body = client.get("/api/tournaments/cup/sheet", headers=organizer).json()
    [entry] = [e for e in body["edits"] if e["field"] == "weapon_rentals"]
    assert entry["before"] == []
    assert entry["after"] == ["Sabre"]
    assert entry["target"] == listed["id"]
    assert len(rules_for(client, organizer)) == 1


def test_an_unissued_row_has_no_registration_to_amend(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    import_roster(client, organizer, [row("Jan", "jan@example.com")])
    listed = sheet_rows(client, organizer)[0]

    response = amend(client, organizer, listed["id"], ["Sabre"])

    assert response.status_code == 409
    assert response.json()["detail"] == "no_registration_for_row"


def test_the_registration_is_priced_at_its_own_moment(client, auth_headers, mailbox):
    """A rental correction prices through the same call a discipline
    correction does, so a later fee change must not reach the rest of the
    registration."""
    organizer = auth_headers()
    setup(client, organizer)
    listed = issued_row(client, organizer)
    client.patch(
        "/api/tournaments/cup/disciplines/SA", json={"fee": 2000}, headers=organizer
    )

    amend(client, organizer, listed["id"], ["Sabre"])

    assert registration_of(listed["id"]).total_amount == 850


def test_the_registration_row_and_the_table_agree(client, auth_headers, mailbox):
    organizer = auth_headers()
    setup(client, organizer)
    listed = issued_row(client, organizer)

    amend(client, organizer, listed["id"], ["Buckler"])

    listed = sheet_rows(client, organizer)[0]
    assert listed["weapon_rentals"] == ["Buckler"]
    assert listed["total_amount"] == 850
    assert db_session().scalar(select(Registration)).total_amount == 850
