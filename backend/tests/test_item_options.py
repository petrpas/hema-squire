"""Extra-item options: an item may declare one option (a label plus optional
preset choices) that the fencer answers when selecting it. Options are inert for
pricing and required once declared."""

import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import pricing
from app.db import Base
from app.mail import get_mailer
from app.main import app
from app.models import Discipline, ExtraCategory, ExtraItem, Tournament
from tests.test_tournaments import make_tournament as make_api_tournament

SLUG = "na-duel-2026"


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


def publish(client, headers):
    make_api_tournament(client, headers)
    client.patch(
        f"/api/tournaments/{SLUG}",
        json={"location": "Brno", "organizers": [{"name": "Org", "link": None}]},
        headers=headers,
    )
    client.post(
        f"/api/tournaments/{SLUG}/disciplines",
        json={"code": "LS", "capacity": 10, "fee": 800},
        headers=headers,
    )


def add_item(client, headers, **fields):
    payload = {"name": "t-shirt", "category": "merch", "price": 300, "max_qty": 5, **fields}
    response = client.post(f"/api/tournaments/{SLUG}/extra-items", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def register(client, headers, extras):
    return client.post(
        f"/api/tournaments/{SLUG}/register",
        json={"disciplines": ["LS"], "extras": extras},
        headers=headers,
    )


# --- 3.1 option definition ------------------------------------------------------


def test_option_with_choices_round_trip(client, auth_headers):
    headers = auth_headers()
    publish(client, headers)

    item = add_item(
        client, headers, option_label="size", option_choices=["S", "M", "L", "XL"]
    )
    assert item["option_label"] == "size"
    assert item["option_choices"] == ["S", "M", "L", "XL"]


def test_free_text_option_round_trip(client, auth_headers):
    headers = auth_headers()
    publish(client, headers)

    item = add_item(client, headers, option_label="engraving")
    assert item["option_label"] == "engraving"
    assert item["option_choices"] == []


def test_choices_are_trimmed_and_deduplicated(client, auth_headers):
    headers = auth_headers()
    publish(client, headers)

    item = add_item(
        client, headers, option_label="size", option_choices=[" S ", "M", "M", "", "  "]
    )
    assert item["option_choices"] == ["S", "M"]


def test_choices_without_a_label_rejected(client, auth_headers):
    headers = auth_headers()
    publish(client, headers)

    response = client.post(
        f"/api/tournaments/{SLUG}/extra-items",
        json={
            "name": "t-shirt",
            "category": "merch",
            "price": 300,
            "option_choices": ["S", "M"],
        },
        headers=headers,
    )
    assert response.status_code == 422


def test_option_fields_editable(client, auth_headers):
    headers = auth_headers()
    publish(client, headers)
    item = add_item(client, headers)

    response = client.patch(
        f"/api/tournaments/{SLUG}/extra-items/{item['id']}",
        json={
            "name": "t-shirt",
            "category": "merch",
            "price": 300,
            "max_qty": 5,
            "option_label": "size",
            "option_choices": ["S", "M"],
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["option_label"] == "size"
    assert response.json()["option_choices"] == ["S", "M"]


# --- 3.3/3.4 answering the option at registration -------------------------------


def test_preset_choice_recorded_and_itemized(client, auth_headers):
    headers = auth_headers()
    publish(client, headers)
    item = add_item(client, headers, option_label="size", option_choices=["S", "M", "L"])
    fencer = auth_headers(email="f1@example.com", name="F1")

    response = register(
        client, fencer, [{"extra_item_id": item["id"], "qty": 2, "option_value": "M"}]
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["extras"] == [
        {
            "extra_item_id": item["id"],
            "name": "t-shirt",
            "category": "merch",
            "qty": 2,
            "option_label": "size",
            "option_value": "M",
        }
    ]
    assert body["total_amount"] == 800 + 2 * 300


def test_free_text_option_recorded(client, auth_headers):
    headers = auth_headers()
    publish(client, headers)
    item = add_item(client, headers, option_label="engraving")
    fencer = auth_headers(email="f1@example.com", name="F1")

    response = register(
        client, fencer, [{"extra_item_id": item["id"], "option_value": " Pro memoria "}]
    )
    assert response.status_code == 201, response.text
    assert response.json()["extras"][0]["option_value"] == "Pro memoria"


def test_missing_required_option_rejected(client, auth_headers):
    headers = auth_headers()
    publish(client, headers)
    item = add_item(client, headers, option_label="size", option_choices=["S", "M"])
    fencer = auth_headers(email="f1@example.com", name="F1")

    response = register(client, fencer, [{"extra_item_id": item["id"], "qty": 1}])
    assert response.status_code == 422
    assert response.json()["detail"] == {"option_required": [item["id"]]}


@pytest.mark.parametrize("value", ["XXL", "m", " "])
def test_value_outside_choices_rejected(client, auth_headers, value):
    headers = auth_headers()
    publish(client, headers)
    item = add_item(client, headers, option_label="size", option_choices=["S", "M"])
    fencer = auth_headers(email="f1@example.com", name="F1")

    response = register(
        client, fencer, [{"extra_item_id": item["id"], "option_value": value}]
    )
    assert response.status_code == 422


def test_option_for_option_less_item_rejected(client, auth_headers):
    headers = auth_headers()
    publish(client, headers)
    item = add_item(client, headers)
    fencer = auth_headers(email="f1@example.com", name="F1")

    response = register(
        client, fencer, [{"extra_item_id": item["id"], "option_value": "M"}]
    )
    assert response.status_code == 422
    assert response.json()["detail"] == {"option_not_accepted": [item["id"]]}


def test_option_value_reaches_the_confirmation_email(client, auth_headers, mailbox):
    headers = auth_headers()
    publish(client, headers)
    item = add_item(client, headers, option_label="size", option_choices=["S", "M"])
    fencer = auth_headers(email="f1@example.com", name="F1")

    register(client, fencer, [{"extra_item_id": item["id"], "qty": 2, "option_value": "M"}])

    body = mailbox.sent[-1].get_body(preferencelist=("plain",)).get_content()
    assert "t-shirt ×2 (size: M)" in body


# --- 3.5/3.6 pricing is untouched, old rows stay valid --------------------------


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_option_value_does_not_change_the_total(session):
    """The same selection totals identically with and without an answer."""
    tournament = Tournament(
        slug="t", display_name="T", date=datetime.date(2026, 10, 3)
    )
    longsword = Discipline(
        tournament=tournament, code="LS", name="LS", capacity=32, fee=800
    )
    shirt = ExtraItem(
        tournament=tournament,
        name="t-shirt",
        category=ExtraCategory.MERCH,
        price=300,
        max_qty=5,
        option_label="size",
        option_choices=["S", "M"],
    )
    plain = ExtraItem(
        tournament=tournament,
        name="mug",
        category=ExtraCategory.MERCH,
        price=300,
        max_qty=5,
    )
    session.add(tournament)
    session.commit()

    with_option = pricing.selection_total(
        tournament,
        disciplines=[longsword],
        extras=[(shirt, 2)],
        weapon_rentals=[],
        afterparty=False,
        at=datetime.date(2026, 9, 1),
    )
    without_option = pricing.selection_total(
        tournament,
        disciplines=[longsword],
        extras=[(plain, 2)],
        weapon_rentals=[],
        afterparty=False,
        at=datetime.date(2026, 9, 1),
    )
    assert with_option == without_option == 800 + 2 * 300


def test_selection_predating_the_option_stays_valid(client, auth_headers):
    """An organizer adding an option label later must not invalidate rows that
    were stored without one."""
    headers = auth_headers()
    publish(client, headers)
    item = add_item(client, headers)
    fencer = auth_headers(email="f1@example.com", name="F1")
    register(client, fencer, [{"extra_item_id": item["id"], "qty": 1}])

    # the organizer introduces the option after the fact
    client.patch(
        f"/api/tournaments/{SLUG}/extra-items/{item['id']}",
        json={
            "name": "t-shirt",
            "category": "merch",
            "price": 300,
            "max_qty": 5,
            "option_label": "size",
            "option_choices": ["S", "M"],
        },
        headers=headers,
    )

    existing = client.get(f"/api/tournaments/{SLUG}/my-registration", headers=fencer)
    assert existing.status_code == 200, existing.text
    extra = existing.json()["extras"][0]
    assert extra["option_label"] == "size"
    assert extra["option_value"] is None
