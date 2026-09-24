"""The participation condition (spec registration, Participation condition;
seating-queue, A conditional registration moves as one): a set of a
registration's individual disciplines attended only together, wholly seated or
wholly queued at every moment, whatever placed it or moved it."""

import pytest
from sqlalchemy import select

from app.mail import get_mailer
from app.main import app
from app.models import Registration
from tests.conftest import credit_registration
from tests.test_demotion import CollectingMailer, db_session, make_cup, settle


@pytest.fixture
def mailbox():
    mailer = CollectingMailer()
    app.dependency_overrides[get_mailer] = lambda: mailer
    yield mailer
    app.dependency_overrides.pop(get_mailer, None)


def register(client, auth_headers, name, disciplines, condition=(), expect=201):
    fencer = auth_headers(email=f"{name.lower()}@example.com", name=name)
    response = client.post(
        "/api/tournaments/cup/register",
        json={"disciplines": list(disciplines), "condition": list(condition)},
        headers=fencer,
    )
    assert response.status_code == expect, response.text
    return fencer, response.json()


def fill(client, auth_headers, slug, count=1):
    """Take every place of a discipline with one-discipline registrations."""
    return [register(client, auth_headers, f"Filler{slug}{n}", [slug])[0] for n in range(count)]


def placed(vs) -> dict[str, bool]:
    registration = db_session().scalar(select(Registration).where(Registration.vs == vs))
    assert registration is not None
    return {e.discipline.slug: e.is_substitute for e in registration.entries}


def assert_invariant():
    """Every registration's condition is wholly seated or wholly queued."""
    for registration in db_session().scalars(select(Registration)):
        condition = [e.is_substitute for e in registration.entries if e.conditional]
        assert all(condition) or not any(condition), registration.vs


CAPS = {"LS": 1, "SA": 1, "RA": 3}


def test_a_met_condition_is_seated_together(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_cup(client, organizer, capacities=CAPS)

    _, body = register(client, auth_headers, "Both", ["LS", "SA"], ["LS", "SA"])

    assert placed(body["vs"]) == {"LS": False, "SA": False}
    assert body["total_amount"] == 2000
    assert [e["conditional"] for e in body["entries"]] == [True, True]
    assert body["condition_waits_for"] == []


def test_an_unmet_condition_waits_whole_and_says_for_what(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_cup(client, organizer, capacities=CAPS)
    fill(client, auth_headers, "SA")
    mailbox.sent.clear()

    _, body = register(client, auth_headers, "Both", ["LS", "SA"], ["LS", "SA"])

    assert placed(body["vs"]) == {"LS": True, "SA": True}
    assert body["total_amount"] == 0
    assert body["condition_waits_for"] == ["SA"]
    (confirmation,) = mailbox.sent
    text = confirmation.get_body(("plain",)).get_content()
    assert "Pojedu jen, pokud dostanu místo ve všech" in text
    assert "Zatím je plno v:" in text


def test_without_the_tick_each_discipline_stands_alone(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_cup(client, organizer, capacities=CAPS)
    fill(client, auth_headers, "SA")

    _, body = register(client, auth_headers, "Plain", ["LS", "SA"])

    assert placed(body["vs"]) == {"LS": False, "SA": True}


def test_a_condition_over_one_discipline_is_refused(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_cup(client, organizer, capacities=CAPS)
    register(client, auth_headers, "One", ["LS", "SA"], ["LS"], expect=422)
    register(client, auth_headers, "Outside", ["LS"], ["LS", "SA"], expect=422)


def test_a_subset_condition_seats_the_outside_discipline_on_its_own(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_cup(client, organizer, capacities=CAPS)

    _, met = register(client, auth_headers, "Met", ["LS", "SA", "RA"], ["LS", "SA"])
    assert placed(met["vs"]) == {"LS": False, "SA": False, "RA": False}

    _, unmet = register(client, auth_headers, "Unmet", ["LS", "SA", "RA"], ["LS", "SA"])
    # both condition disciplines are full now: the outside one waits too
    assert placed(unmet["vs"]) == {"LS": True, "SA": True, "RA": True}
    assert_invariant()


def test_after_settlement_everything_is_queued(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_cup(client, organizer, capacities=CAPS)
    settle(client, organizer)

    _, body = register(client, auth_headers, "Late", ["LS", "SA"], ["LS", "SA"])

    assert placed(body["vs"]) == {"LS": True, "SA": True}


def amend(client, fencer, disciplines, condition=(), expect=200):
    response = client.post(
        "/api/tournaments/cup/my-registration/amend",
        json={"disciplines": list(disciplines), "condition": list(condition)},
        headers=fencer,
    )
    assert response.status_code == expect, response.text
    return response.json()


def preview(client, fencer, disciplines, condition=()):
    response = client.post(
        "/api/tournaments/cup/my-registration/amend/preview",
        json={"disciplines": list(disciplines), "condition": list(condition)},
        headers=fencer,
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_ticking_on_amendment_warns_then_queues_the_whole(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_cup(client, organizer, capacities=CAPS)
    fill(client, auth_headers, "SA")
    fencer, body = register(client, auth_headers, "Mixed", ["LS", "SA"])
    assert placed(body["vs"]) == {"LS": False, "SA": True}

    stated = preview(client, fencer, ["LS", "SA"], ["LS", "SA"])
    assert stated == {"queued": ["LS", "SA"], "moves_to_queue": True, "refusal": None}

    amend(client, fencer, ["LS", "SA"], ["LS", "SA"])
    assert placed(body["vs"]) == {"LS": True, "SA": True}

    # unticking places what is free again
    assert preview(client, fencer, ["LS", "SA"])["queued"] == ["SA"]
    amend(client, fencer, ["LS", "SA"])
    assert placed(body["vs"]) == {"LS": False, "SA": True}


def test_an_amendment_that_would_queue_money_is_refused(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_cup(client, organizer, capacities=CAPS)
    fill(client, auth_headers, "SA")
    fencer, body = register(client, auth_headers, "Paid", ["LS", "SA"])
    session = db_session()
    registration = session.scalar(select(Registration).where(Registration.vs == body["vs"]))
    credit_registration(session, registration, 100000)

    assert preview(client, fencer, ["LS", "SA"], ["LS", "SA"])["refusal"] == (
        "amendment_would_queue_paid"
    )
    response = amend(client, fencer, ["LS", "SA"], ["LS", "SA"], expect=409)
    assert response["detail"] == "amendment_would_queue_paid"
    assert placed(body["vs"]) == {"LS": False, "SA": True}


def test_existing_registrations_carry_no_condition(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_cup(client, organizer, capacities=CAPS)
    _, body = register(client, auth_headers, "Plain", ["LS", "SA"])
    registration = db_session().scalar(select(Registration).where(Registration.vs == body["vs"]))
    assert not any(e.conditional for e in registration.entries)


def admit(client, organizer, vs, slug, expect=200):
    registration = db_session().scalar(select(Registration).where(Registration.vs == vs))
    response = client.post(
        f"/api/tournaments/cup/registrations/{registration.id}/admit/{slug}", headers=organizer
    )
    assert response.status_code == expect, response.text
    return response.json()


def give_back(client, organizer, vs, slug):
    registration = db_session().scalar(select(Registration).where(Registration.vs == vs))
    response = client.post(
        f"/api/tournaments/cup/registrations/{registration.id}/return-to-queue/{slug}",
        headers=organizer,
    )
    assert response.status_code == 200, response.text


def test_promotion_seats_the_condition_together_or_not_at_all(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_cup(client, organizer, capacities=CAPS)
    (sa_holder,) = fill(client, auth_headers, "SA")
    (ls_holder,) = fill(client, auth_headers, "LS")
    _, body = register(client, auth_headers, "Both", ["LS", "SA"], ["LS", "SA"])
    _, later = register(client, auth_headers, "Later", ["LS"])

    # Longsword frees, Sabre is still full: refused, naming Sabre
    client.post("/api/tournaments/cup/my-registration/cancel", headers=ls_holder)
    refused = admit(client, organizer, body["vs"], "LS", expect=409)
    assert refused["detail"] == {"condition_discipline_full": "SA"}
    assert_invariant()
    # a later fencer in that queue may be seated past it
    admit(client, organizer, later["vs"], "LS")
    give_back(client, organizer, later["vs"], "LS")

    client.post("/api/tournaments/cup/my-registration/cancel", headers=sa_holder)
    mailbox.sent.clear()
    admitted = admit(client, organizer, body["vs"], "LS")

    assert placed(body["vs"]) == {"LS": False, "SA": False}
    assert admitted["total_amount"] == 2000
    (notice,) = mailbox.sent
    text = notice.get_body(("plain",)).get_content()
    assert "Longsword" in text and "Sabre" in text
    assert_invariant()


def test_returning_one_placement_of_a_condition_returns_the_registration(
    client, auth_headers, mailbox
):
    organizer = auth_headers()
    make_cup(client, organizer, capacities=CAPS)
    _, body = register(client, auth_headers, "Three", ["LS", "SA", "RA"], ["LS", "SA"])
    assert placed(body["vs"]) == {"LS": False, "SA": False, "RA": False}

    give_back(client, organizer, body["vs"], "RA")
    assert placed(body["vs"]) == {"LS": False, "SA": False, "RA": True}

    give_back(client, organizer, body["vs"], "SA")
    assert placed(body["vs"]) == {"LS": True, "SA": True, "RA": True}
    registration = db_session().scalar(select(Registration).where(Registration.vs == body["vs"]))
    assert registration.total_amount == 0
    assert_invariant()


def test_the_sheet_row_carries_the_condition(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_cup(client, organizer, capacities=CAPS)
    register(client, auth_headers, "Both", ["LS", "SA"], ["LS", "SA"])

    rows = client.get("/api/tournaments/cup/sheet", headers=organizer).json()["rows"]
    (row,) = [r for r in rows if r["name"] == "Both"]
    assert row["conditional"] == ["LS", "SA"]


def test_a_hand_entry_carries_the_tick(client, auth_headers, mailbox):
    organizer = auth_headers()
    make_cup(client, organizer, capacities=CAPS)
    fill(client, auth_headers, "SA")

    response = client.post(
        "/api/tournaments/cup/manual-rows",
        json={"name": "Door", "disciplines": ["LS", "SA"], "condition": ["LS", "SA"]},
        headers=organizer,
    )

    assert response.status_code == 201, response.text
    registration = db_session().get(Registration, response.json()["registration_id"])
    assert {e.discipline.slug: e.is_substitute for e in registration.entries} == {
        "LS": True,
        "SA": True,
    }
