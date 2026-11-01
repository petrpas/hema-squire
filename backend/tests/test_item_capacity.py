"""Item capacity (spec item-capacity): what counts against an item's limit,
what a full item refuses, and what a fencer who holds one keeps."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app import matching
from app.db import get_session
from app.main import app
from app.models import ExtraItem, Fencer, Registration, RegistrationState
from app.routers import registrations
from tests.conftest import enable_payments, publish, set_features

ITEMS = "/api/tournaments/cup/extra-items"


def db_session():
    return next(app.dependency_overrides[get_session]())


def setup_tournament(client, organizer, capacity=5):
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2030-12-05"},
        headers=organizer,
    )
    enable_payments(client, organizer, "cup")
    set_features(client, organizer, "cup", feature_extras=True, feature_payments=True)
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "LS", "weapon": "LS", "capacity": capacity, "fee": 1000},
        headers=organizer,
    )


def add_item(client, organizer, capacity, category="seminar", max_qty=1, name="Seminar"):
    response = client.post(
        ITEMS,
        json={
            "name": name,
            "category": category,
            "price": 100,
            "max_qty": max_qty,
            "capacity": capacity,
        },
        headers=organizer,
    )
    assert response.status_code == 201, response.text
    return response.json()


def register(client, headers, item, qty=1):
    return client.post(
        "/api/tournaments/cup/register",
        json={"disciplines": ["LS"], "extras": [{"extra_item_id": item["id"], "qty": qty}]},
        headers=headers,
    )


def amend(client, headers, extras):
    return client.post(
        "/api/tournaments/cup/my-registration/amend",
        json={"disciplines": ["LS"], "extras": extras},
        headers=headers,
    )


def places(client) -> list[dict]:
    return client.get("/api/tournaments/cup/item-availability").json()


def stored(session, email) -> Registration:
    registration = session.scalar(select(Registration).join(Fencer).where(Fencer.email == email))
    assert registration is not None
    return registration


def lapse(email):
    session = db_session()
    stored(session, email).expires_at = datetime.now(UTC) - timedelta(days=1)
    session.commit()


def test_every_category_is_limited_on_the_same_terms(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    other = add_item(client, organizer, 1, category="other_action", name="Sparring")
    publish(client, organizer, "cup")

    assert register(client, auth_headers(email="f@example.com", name="F"), other).status_code == 201
    refused = register(client, auth_headers(email="g@example.com", name="G"), other)

    assert refused.status_code == 422
    assert refused.json()["detail"] == {"item_sold_out": [other["id"]]}


def test_an_item_without_a_capacity_is_never_refused_and_not_listed(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    item = add_item(client, organizer, None)
    publish(client, organizer, "cup")

    assert register(client, auth_headers(email="f@example.com", name="F"), item).status_code == 201
    assert places(client) == []


def test_pieces_are_counted(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    item = add_item(client, organizer, 5, category="merch", max_qty=4, name="Shirt")
    publish(client, organizer, "cup")

    register(client, auth_headers(email="f@example.com", name="F"), item, qty=3)

    assert places(client) == [{"id": item["id"], "capacity": 5, "taken": 3, "free": 2}]
    late = auth_headers(email="g@example.com", name="G")
    assert register(client, late, item, qty=3).status_code == 422
    assert register(client, late, item, qty=2).status_code == 201


def test_a_refused_submission_creates_nothing(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    item = add_item(client, organizer, 1)
    publish(client, organizer, "cup")
    register(client, auth_headers(email="f@example.com", name="F"), item)

    register(client, auth_headers(email="g@example.com", name="G"), item)

    assert db_session().scalar(select(func.count()).select_from(Registration)) == 1


def test_the_second_of_two_racing_submissions_is_refused(client, auth_headers, monkeypatch):
    """Both pass the check made before writing; the claim after it decides."""
    organizer = auth_headers()
    setup_tournament(client, organizer)
    item = add_item(client, organizer, 1)
    publish(client, organizer, "cup")
    register(client, auth_headers(email="f@example.com", name="F"), item)
    monkeypatch.setattr(registrations, "sold_out_items", lambda *_args: [])

    refused = register(client, auth_headers(email="g@example.com", name="G"), item)

    assert refused.json()["detail"] == {"item_sold_out": [item["id"]]}
    assert db_session().scalar(select(func.count()).select_from(Registration)) == 1


def test_a_fencer_waiting_in_the_queue_holds_their_item(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer, capacity=1)
    filler = add_item(client, organizer, None, name="Dinner")
    seminar = add_item(client, organizer, 1)
    publish(client, organizer, "cup")
    register(client, auth_headers(email="f@example.com", name="F"), filler)

    assert (
        register(client, auth_headers(email="g@example.com", name="G"), seminar).status_code == 201
    )
    session = db_session()
    assert stored(session, "g@example.com").fully_queued

    assert (
        register(client, auth_headers(email="h@example.com", name="H"), seminar).status_code == 422
    )


def test_an_expired_reservation_gives_its_place_back(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    item = add_item(client, organizer, 1)
    publish(client, organizer, "cup")
    register(client, auth_headers(email="f@example.com", name="F"), item)

    lapse("f@example.com")

    assert places(client)[0]["free"] == 1
    assert register(client, auth_headers(email="g@example.com", name="G"), item).status_code == 201


def test_re_registering_into_the_last_place_counts_once(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    item = add_item(client, organizer, 1)
    publish(client, organizer, "cup")
    fencer = auth_headers(email="f@example.com", name="F")
    register(client, fencer, item)
    lapse("f@example.com")
    client.post("/api/tournaments/cup/payments/process", headers=organizer)

    assert register(client, fencer, item).status_code == 201
    assert places(client)[0]["taken"] == 1


def test_lowering_a_capacity_takes_nothing_from_anyone(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    item = add_item(client, organizer, 3)
    publish(client, organizer, "cup")
    fencer = auth_headers(email="f@example.com", name="F")
    register(client, fencer, item)
    register(client, auth_headers(email="g@example.com", name="G"), item)

    response = client.patch(
        f"{ITEMS}/{item['id']}", json={**item, "capacity": 1}, headers=organizer
    )

    assert response.status_code == 200
    assert places(client)[0] == {"id": item["id"], "capacity": 1, "taken": 2, "free": 0}
    selection = {"extra_item_id": item["id"], "qty": 1}
    assert amend(client, fencer, [selection]).status_code == 200


def test_an_amendment_keeps_a_held_item_and_needs_room_to_raise_it(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    item = add_item(client, organizer, 1, category="merch", max_qty=2, name="Shirt")
    publish(client, organizer, "cup")
    fencer = auth_headers(email="f@example.com", name="F")
    register(client, fencer, item)

    kept = amend(client, fencer, [{"extra_item_id": item["id"], "qty": 1}])
    raised = amend(client, fencer, [{"extra_item_id": item["id"], "qty": 2}])

    assert kept.status_code == 200
    assert raised.json()["detail"] == {"item_sold_out": [item["id"]]}
    assert places(client)[0]["taken"] == 1


def test_removing_an_item_frees_it_at_once(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    item = add_item(client, organizer, 1)
    publish(client, organizer, "cup")
    fencer = auth_headers(email="f@example.com", name="F")
    register(client, fencer, item)

    assert amend(client, fencer, []).status_code == 200

    assert places(client)[0]["free"] == 1


def test_a_late_payment_does_not_reinstate_into_a_filled_item(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    item = add_item(client, organizer, 1)
    publish(client, organizer, "cup")
    register(client, auth_headers(email="f@example.com", name="F"), item)
    lapse("f@example.com")
    client.post("/api/tournaments/cup/payments/process", headers=organizer)

    session = db_session()
    expired = stored(session, "f@example.com")
    assert expired.state == RegistrationState.EXPIRED
    assert matching.seats_free(session, expired)

    register(client, auth_headers(email="g@example.com", name="G"), item)

    session = db_session()
    assert not matching.seats_free(session, stored(session, "f@example.com"))


def test_hand_entry_counts_and_may_overrun(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    item = add_item(client, organizer, 1, category="rental", name="longsword")
    publish(client, organizer, "cup")
    register(client, auth_headers(email="f@example.com", name="F"), item)

    response = client.post(
        "/api/tournaments/cup/manual-rows",
        json={"name": "Door Fencer", "disciplines": ["LS"], "weapon_rentals": ["longsword"]},
        headers=organizer,
    )

    assert response.status_code == 201, response.text
    assert places(client)[0]["taken"] == 2


def restored_capacities(client, organizer, document) -> list:
    client.delete("/api/tournaments/cup", headers=organizer)
    response = client.post("/api/tournaments/restore", json=document, headers=organizer)
    assert response.status_code == 201, response.text
    session = db_session()
    return [item.capacity for item in session.scalars(select(ExtraItem))]


def test_capacity_round_trips_through_the_export(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    add_item(client, organizer, 7)
    publish(client, organizer, "cup")

    document = client.get("/api/tournaments/cup/export/json", headers=organizer).json()

    assert restored_capacities(client, organizer, document) == [7]


def test_an_older_document_restores_items_unlimited(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    add_item(client, organizer, 7)
    publish(client, organizer, "cup")

    document = client.get("/api/tournaments/cup/export/json", headers=organizer).json()
    document["schema_version"] = 20
    del document["extra_items"][0]["capacity"]

    assert restored_capacities(client, organizer, document) == [None]
