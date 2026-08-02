"""Publication: the one-time, irreversible act that makes a tournament
public, and the guard that keeps a published tournament complete forever
after (design add-explicit-publishing)."""

from datetime import date, timedelta

from tests.conftest import publish

TODAY = date.today()


def make_tournament(client, organizer, slug="cup", **patch):
    client.post(
        "/api/tournaments",
        json={"slug": slug, "display_name": "Cup", "date": str(TODAY + timedelta(days=30))},
        headers=organizer,
    )
    base = {"location": "Brno", "organizers": [{"name": "Cup Org", "link": None}]}
    client.patch(f"/api/tournaments/{slug}", json=base | patch, headers=organizer)
    return slug


def add_priced_discipline(client, organizer, slug="cup", code="LS", fee=800):
    response = client.post(
        f"/api/tournaments/{slug}/disciplines",
        json={"code": code, "capacity": 10, "fee": fee},
        headers=organizer,
    )
    assert response.status_code == 201, response.text
    return response.json()


def register(client, headers, slug="cup"):
    return client.post(
        f"/api/tournaments/{slug}/register", json={"disciplines": ["LS"]}, headers=headers
    )


# --- publication as a one-time, guarded act ---------------------------------


def test_setup_complete_draft_absent_and_rejects_registration(client, auth_headers):
    organizer = auth_headers()
    slug = make_tournament(client, organizer)
    add_priced_discipline(client, organizer, slug)
    fencer = auth_headers(email="f1@example.com", name="F1")

    listed = client.get("/api/tournaments/open", headers=fencer).json()
    assert slug not in [t["slug"] for t in listed]

    response = register(client, fencer, slug)
    assert response.status_code == 403
    assert response.json()["detail"] == {"reason": "not_published"}


def test_publishing_makes_it_appear_and_accept(client, auth_headers):
    organizer = auth_headers()
    slug = make_tournament(client, organizer)
    add_priced_discipline(client, organizer, slug)

    published = publish(client, organizer, slug)
    assert published["published_at"] is not None

    fencer = auth_headers(email="f1@example.com", name="F1")
    listed = client.get("/api/tournaments/open", headers=fencer).json()
    assert slug in [t["slug"] for t in listed]

    response = register(client, fencer, slug)
    assert response.status_code == 201


def test_publishing_incomplete_tournament_names_missing_items(client, auth_headers):
    organizer = auth_headers()
    # location present, organizers cleared, no discipline added
    slug = make_tournament(client, organizer, organizers=[])

    response = client.post(f"/api/tournaments/{slug}/publish", headers=organizer)
    assert response.status_code == 422
    assert set(response.json()["detail"]["missing"]) == {"organizers", "disciplines"}


def test_republishing_refused_and_timestamp_unchanged(client, auth_headers):
    organizer = auth_headers()
    slug = make_tournament(client, organizer)
    add_priced_discipline(client, organizer, slug)
    first = publish(client, organizer, slug)

    again = client.post(f"/api/tournaments/{slug}/publish", headers=organizer)
    assert again.status_code == 409
    assert again.json()["detail"] == "already_published"

    detail = client.get(f"/api/tournaments/{slug}", headers=organizer).json()
    assert detail["published_at"] == first["published_at"]


def test_publishing_a_cancelled_tournament_refused(client, auth_headers):
    organizer = auth_headers()
    slug = make_tournament(client, organizer)
    add_priced_discipline(client, organizer, slug)
    client.post(f"/api/tournaments/{slug}/cancel", headers=organizer)

    response = client.post(f"/api/tournaments/{slug}/publish", headers=organizer)
    assert response.status_code == 409
    assert response.json()["detail"] == "cancelled"


def test_non_console_account_refused(client, auth_headers):
    organizer = auth_headers()
    slug = make_tournament(client, organizer)
    add_priced_discipline(client, organizer, slug)
    stranger = auth_headers(email="stranger@example.com", name="Stranger")

    response = client.post(f"/api/tournaments/{slug}/publish", headers=stranger)
    assert response.status_code == 403


def test_non_owner_team_member_may_publish_and_is_recorded(client, auth_headers, engine):
    organizer = auth_headers()
    slug = make_tournament(client, organizer)
    add_priced_discipline(client, organizer, slug)
    auth_headers(email="helper@example.com", name="Helper")
    added = client.post(
        f"/api/tournaments/{slug}/team", json={"email": "helper@example.com"}, headers=organizer
    )
    assert added.status_code == 201, added.text
    helper_login = client.post(
        "/api/auth/login", json={"email": "helper@example.com", "password": "correct-horse"}
    )
    helper = {"Authorization": f"Bearer {helper_login.json()['token']}"}

    response = client.post(f"/api/tournaments/{slug}/publish", headers=helper)
    assert response.status_code == 200, response.text

    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from app.models import Fencer, Tournament

    with Session(engine) as session:
        tournament = session.scalar(select(Tournament).where(Tournament.slug == slug))
        helper_fencer = session.scalar(select(Fencer).where(Fencer.email == "helper@example.com"))
        assert tournament.published_by_id == helper_fencer.id


# --- the published-completeness guard ---------------------------------------


def test_clearing_a_discipline_price_on_published_tournament_rejected(client, auth_headers):
    organizer = auth_headers()
    slug = make_tournament(client, organizer)
    add_priced_discipline(client, organizer, slug)
    publish(client, organizer, slug)

    response = client.patch(
        f"/api/tournaments/{slug}/disciplines/LS",
        json={"code": "LS", "capacity": 10, "fee": None},
        headers=organizer,
    )
    assert response.status_code == 422
    assert response.json()["detail"] == {
        "reason": "setup_incomplete",
        "missing": ["discipline_prices"],
    }

    detail = client.get(f"/api/tournaments/{slug}", headers=organizer).json()
    assert detail["disciplines"][0]["fee"] == 800


def test_deleting_the_only_discipline_on_published_tournament_rejected(client, auth_headers):
    organizer = auth_headers()
    slug = make_tournament(client, organizer)
    add_priced_discipline(client, organizer, slug)
    publish(client, organizer, slug)

    response = client.delete(f"/api/tournaments/{slug}/disciplines/LS", headers=organizer)
    assert response.status_code == 422
    assert response.json()["detail"] == {"reason": "setup_incomplete", "missing": ["disciplines"]}

    detail = client.get(f"/api/tournaments/{slug}", headers=organizer).json()
    assert len(detail["disciplines"]) == 1


def test_emptying_the_location_on_published_tournament_rejected(client, auth_headers):
    organizer = auth_headers()
    slug = make_tournament(client, organizer)
    add_priced_discipline(client, organizer, slug)
    publish(client, organizer, slug)

    response = client.patch(
        f"/api/tournaments/{slug}", json={"location": ""}, headers=organizer
    )
    assert response.status_code == 422
    assert response.json()["detail"] == {"reason": "setup_incomplete", "missing": ["location"]}

    detail = client.get(f"/api/tournaments/{slug}", headers=organizer).json()
    assert detail["location"] == "Brno"


def test_removing_the_last_organizer_on_published_tournament_rejected(client, auth_headers):
    organizer = auth_headers()
    slug = make_tournament(client, organizer)
    add_priced_discipline(client, organizer, slug)
    publish(client, organizer, slug)

    response = client.patch(
        f"/api/tournaments/{slug}", json={"organizers": []}, headers=organizer
    )
    assert response.status_code == 422
    assert response.json()["detail"] == {"reason": "setup_incomplete", "missing": ["organizers"]}

    detail = client.get(f"/api/tournaments/{slug}", headers=organizer).json()
    assert detail["organizers"] == [{"name": "Cup Org", "link": None}]


def test_enabling_eur_with_unpriced_extra_item_on_published_tournament_rejected(
    client, auth_headers
):
    organizer = auth_headers()
    slug = make_tournament(client, organizer)
    add_priced_discipline(client, organizer, slug, fee=800)
    client.patch(
        f"/api/tournaments/{slug}/disciplines/LS",
        json={"code": "LS", "capacity": 10, "fee": 800, "fee_eur": 32},
        headers=organizer,
    )
    item = client.post(
        f"/api/tournaments/{slug}/extra-items",
        json={"name": "t-shirt", "category": "merch", "price": 300, "max_qty": 5},
        headers=organizer,
    ).json()
    publish(client, organizer, slug)

    response = client.patch(
        f"/api/tournaments/{slug}", json={"eur_payments_enabled": True}, headers=organizer
    )
    assert response.status_code == 422
    assert response.json()["detail"] == {
        "reason": "setup_incomplete",
        "missing": ["extra_item_prices"],
    }

    detail = client.get(f"/api/tournaments/{slug}", headers=organizer).json()
    assert detail["eur_payments_enabled"] is False
    assert detail["extra_items"][0]["id"] == item["id"]


def test_same_operations_succeed_on_a_draft(client, auth_headers):
    """The guard is a no-op while the tournament is a draft (design D3): any
    mandatory item may be emptied or removed freely."""
    organizer = auth_headers()
    slug = make_tournament(client, organizer)
    add_priced_discipline(client, organizer, slug)

    deleted = client.delete(f"/api/tournaments/{slug}/disciplines/LS", headers=organizer)
    assert deleted.status_code == 204

    cleared = client.patch(
        f"/api/tournaments/{slug}", json={"organizers": [], "location": ""}, headers=organizer
    )
    assert cleared.status_code == 200
    assert cleared.json()["organizers"] == []
    assert cleared.json()["location"] == ""
