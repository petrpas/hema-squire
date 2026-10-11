"""The public entrant rosters (spec public-entrants, public-browsing)."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.db import get_session
from app.main import app
from app.models import Discipline, ImportBatch, Registration, RegistrationsKeptBy, Tournament
from tests.conftest import credit_registration, enable_payments, publish


def db_session():
    return next(app.dependency_overrides[get_session]())


def setup_tournament(client, organizer, *, payments=True, sabre_capacity=1):
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    client.patch(
        "/api/tournaments/cup",
        json={"city": "Brno", "organizers": [{"name": "Cup Org", "link": None}]},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "LS", "weapon": "LS", "capacity": 10, "fee": 800},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "SB", "weapon": "SB", "capacity": sabre_capacity, "fee": 500},
        headers=organizer,
    )
    if payments:
        enable_payments(client, organizer, "cup")
        client.patch(
            "/api/tournaments/cup",
            json={"bank_account": "CZ6508000000192000145399"},
            headers=organizer,
        )
    publish(client, organizer, "cup")


def register(client, headers, disciplines=("LS",), **overrides):
    response = client.post(
        "/api/tournaments/cup/register",
        json={"disciplines": list(disciplines), **overrides},
        headers=headers,
    )
    assert response.status_code in (200, 201), response.text
    return response.json()


def pay(vs):
    session = db_session()
    registration = session.scalar(select(Registration).where(Registration.vs == vs))
    assert registration is not None
    credit_registration(session, registration, registration.total_amount * 100)


def tournament_row(session):
    tournament = session.scalar(select(Tournament).where(Tournament.slug == "cup"))
    assert tournament is not None
    return tournament


def rosters(client):
    response = client.get("/api/tournaments/cup/entrants")
    assert response.status_code == 200, response.text
    return {roster["slug"]: roster for roster in response.json()["rosters"]}


def seated(roster):
    return [(row["number"], row["name"], row["paid"], row["faded"]) for row in roster["seated"]]


# ------------------------------------------------------------- publication


def test_rosters_answer_without_a_credential(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    register(client, auth_headers(email="a@example.com", name="Adéla"))

    anonymous = client.get("/api/tournaments/cup/entrants").json()
    signed_in = client.get(
        "/api/tournaments/cup/entrants", headers=auth_headers(email="z@example.com", name="Z")
    ).json()

    assert anonymous == signed_in
    assert [r["slug"] for r in anonymous["rosters"]] == ["LS", "SB"]


def test_a_cancelled_tournament_names_nobody(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    register(client, auth_headers(email="a@example.com", name="Adéla"))
    session = db_session()
    tournament_row(session).cancelled_at = datetime.now(UTC)
    session.commit()

    response = client.get("/api/tournaments/cup/entrants")

    assert response.status_code == 404
    assert "Adéla" not in response.text


def test_a_draft_is_not_found(client, auth_headers):
    organizer = auth_headers()
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    assert client.get("/api/tournaments/cup/entrants").status_code == 404


def test_the_answer_carries_no_contact_or_money(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    vs = register(client, auth_headers(email="a@example.com", name="Adéla"))["vs"]

    text = client.get("/api/tournaments/cup/entrants").text

    assert "a@example.com" not in text
    assert str(vs) not in text
    assert "800" not in text


# ------------------------------------------------------------ the rows


def test_unpaid_entrants_are_shown_faded_after_the_paid(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    register(client, auth_headers(email="a@example.com", name="Adéla"))
    boris = register(client, auth_headers(email="b@example.com", name="Boris"))
    pay(boris["vs"])

    assert seated(rosters(client)["LS"]) == [
        (1, "Boris", "yes", False),
        (2, "Adéla", "no", True),
    ]


def test_the_organizers_correction_and_deletion_reach_the_roster(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    register(client, auth_headers(email="a@example.com", name="Jan Novak"))
    register(client, auth_headers(email="b@example.com", name="Duplicate"))
    rows = {
        row["name"]: row["id"]
        for row in client.get("/api/tournaments/cup/sheet", headers=organizer).json()["rows"]
    }
    for kind, target, payload in (
        ("field_edit", rows["Jan Novak"], {"field": "name", "value": "Jan Novák"}),
        ("row_delete", rows["Duplicate"], {}),
    ):
        response = client.post(
            "/api/tournaments/cup/rules",
            json={"phase": "parsing", "kind": kind, "target": target, "payload": payload},
            headers=organizer,
        )
        assert response.status_code == 201, response.text

    assert [row["name"] for row in rosters(client)["LS"]["seated"]] == ["Jan Novák"]


def test_an_expired_reservation_is_gone(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    vs = register(client, auth_headers(email="a@example.com", name="Adéla"))["vs"]
    session = db_session()
    registration = session.scalar(select(Registration).where(Registration.vs == vs))
    assert registration is not None
    registration.expires_at = datetime.now(UTC) - timedelta(hours=1)
    session.commit()

    assert rosters(client)["LS"]["seated"] == []


def test_a_hand_tick_is_the_only_mark_where_squire_does_not_collect(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer, payments=False)
    adela = register(client, auth_headers(email="a@example.com", name="Adéla"))
    register(client, auth_headers(email="b@example.com", name="Boris"))
    session = db_session()
    registration = session.scalar(select(Registration).where(Registration.vs == adela["vs"]))
    assert registration is not None
    response = client.post(
        f"/api/tournaments/cup/registrations/{registration.id}/settled?settled=true",
        headers=organizer,
    )
    assert response.status_code == 200, response.text

    assert sorted(seated(rosters(client)["LS"])) == [
        (1, "Adéla", "yes", False),
        (2, "Boris", None, False),
    ]


# ------------------------------------------------------------ the queue


def test_the_queue_follows_the_line_in_queue_order(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    register(client, auth_headers(email="a@example.com", name="Adéla"), disciplines=("SB",))
    register(client, auth_headers(email="b@example.com", name="Boris"), disciplines=("SB",))
    cyril = auth_headers(email="c@example.com", name="Cyril")
    register(client, cyril, disciplines=("SB",))

    sabre = rosters(client)["SB"]

    assert sabre["line"] is True
    assert [row["name"] for row in sabre["seated"]] == ["Adéla"]
    assert [(row["number"], row["name"]) for row in sabre["queued"]] == [(1, "Boris"), (2, "Cyril")]
    # the number the fencer reads on their own registration
    own = client.get("/api/tournaments/cup/my-registration", headers=cyril).json()
    (entry,) = own["entries"]
    assert entry["queue_position"] == 2


def test_a_queued_row_states_nothing_about_money(client, auth_headers):
    """The registration's settled state covers its seats: on a queued row it
    would claim payment for a placement that is not priced."""
    organizer = auth_headers()
    setup_tournament(client, organizer)
    register(client, auth_headers(email="a@example.com", name="Adéla"), disciplines=("SB",))
    mixed = register(
        client, auth_headers(email="b@example.com", name="Boris"), disciplines=("LS", "SB")
    )
    pay(mixed["vs"])
    register(client, auth_headers(email="c@example.com", name="Cyril"), disciplines=("SB",))

    by_slug = rosters(client)

    assert seated(by_slug["LS"]) == [(1, "Boris", "yes", False)]
    assert [(row["name"], row["paid"], row["faded"]) for row in by_slug["SB"]["queued"]] == [
        ("Boris", None, False),
        ("Cyril", None, False),
    ]


def test_a_conditional_placement_is_marked(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    register(client, auth_headers(email="a@example.com", name="Adéla"), disciplines=("SB",))
    register(
        client,
        auth_headers(email="b@example.com", name="Boris"),
        disciplines=("LS", "SB"),
        condition=["LS", "SB"],
    )

    by_slug = rosters(client)

    (boris,) = by_slug["SB"]["queued"]
    assert boris["conditional"] is True
    # waiting for all of them, he holds no seat in Longsword either
    assert [(row["name"], row["conditional"]) for row in by_slug["LS"]["queued"]] == [
        ("Boris", True)
    ]


def test_manual_mode_shows_no_queue_and_no_line(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer, payments=False)
    register(client, auth_headers(email="a@example.com", name="Adéla"))
    register(client, auth_headers(email="b@example.com", name="Boris"))
    session = db_session()
    tournament = tournament_row(session)
    tournament.registrations_kept_by = RegistrationsKeptBy.ORGANIZER
    # an imported roster may seat beyond capacity
    longsword = session.scalar(
        select(Discipline).where(Discipline.tournament_id == tournament.id, Discipline.slug == "LS")
    )
    assert longsword is not None
    longsword.capacity = 1
    session.commit()

    roster = rosters(client)["LS"]

    assert roster["line"] is False
    assert roster["queued"] == []
    assert [(row["number"], row["name"]) for row in roster["seated"]] == [
        (1, "Adéla"),
        (2, "Boris"),
    ]


def test_a_held_tournament_keeps_its_rosters_without_a_queue(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    register(client, auth_headers(email="a@example.com", name="Adéla"), disciplines=("SB",))
    register(client, auth_headers(email="b@example.com", name="Boris"), disciplines=("SB",))
    session = db_session()
    tournament_row(session).date = datetime.now(UTC).date() - timedelta(days=30)
    session.commit()

    sabre = rosters(client)["SB"]

    assert [row["name"] for row in sabre["seated"]] == ["Adéla"]
    assert sabre["queued"] == []
    assert sabre["line"] is False


def test_an_organizer_kept_list_states_when_the_roster_reached_squire(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer, payments=False)
    register(client, auth_headers(email="a@example.com", name="Adéla"))
    assert client.get("/api/tournaments/cup/entrants").json()["as_of"] is None

    session = db_session()
    tournament = tournament_row(session)
    tournament.registrations_kept_by = RegistrationsKeptBy.ORGANIZER
    session.add(
        ImportBatch(
            tournament_id=tournament.id,
            filename="roster.csv",
            uploaded_by=1,
            uploaded_at=datetime(2026, 8, 30, 9, 15, tzinfo=UTC),
            row_count=54,
        )
    )
    session.commit()

    assert client.get("/api/tournaments/cup/entrants").json()["as_of"].startswith("2026-08-30")


# ------------------------------------------------------------ teams


def setup_team_tournament(client, organizer):
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    client.patch(
        "/api/tournaments/cup",
        json={"city": "Brno", "organizers": [{"name": "Cup Org", "link": None}]},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/cup/disciplines",
        json={
            "slug": "TM",
            "weapon": "LS",
            "capacity": 1,
            "fee": 3000,
            "kind": "team",
            "team_min": 2,
            "team_max": 4,
        },
        headers=organizer,
    )
    publish(client, organizer, "cup")


def enter_team(client, headers, name):
    return register(client, headers, disciplines=(), teams=[{"slug": "TM", "name": name}])


def test_a_team_is_listed_with_its_members_and_the_waitlist_below(client, auth_headers):
    organizer = auth_headers()
    setup_team_tournament(client, organizer)
    captain = auth_headers(email="a@example.com", name="Adéla")
    team_id = enter_team(client, captain, "Draci")["teams"][0]["id"]
    response = client.put(
        f"/api/tournaments/cup/my-registration/teams/{team_id}/roster",
        json={"members": [{"name": "Eva", "club": "Klub X"}, {"name": "Filip"}]},
        headers=captain,
    )
    assert response.status_code == 200, response.text
    enter_team(client, auth_headers(email="b@example.com", name="Boris"), "Vlci")

    roster = rosters(client)["TM"]

    assert roster["kind"] == "team"
    (draci,) = roster["seated"]
    assert draci["name"] == "Draci"
    assert [(m["name"], m["club"]) for m in draci["members"]] == [
        ("Eva", "Klub X"),
        ("Filip", None),
    ]
    (vlci,) = roster["queued"]
    assert (vlci["number"], vlci["name"], vlci["members"], vlci["paid"]) == (1, "Vlci", [], None)


# ------------------------------------------------------------ the counts


def test_a_removed_row_is_not_counted_but_keeps_its_seat(client, auth_headers):
    """The count beside the capacity is who the public is shown; the seat the
    removed registration holds is a separate matter (spec public-entrants)."""
    organizer = auth_headers()
    setup_tournament(client, organizer)
    register(client, auth_headers(email="a@example.com", name="Adéla"))
    register(client, auth_headers(email="b@example.com", name="Boris"))
    rows = {
        row["name"]: row["id"]
        for row in client.get("/api/tournaments/cup/sheet", headers=organizer).json()["rows"]
    }
    response = client.post(
        "/api/tournaments/cup/rules",
        json={"phase": "parsing", "kind": "row_delete", "target": rows["Boris"], "payload": {}},
        headers=organizer,
    )
    assert response.status_code == 201, response.text

    (longsword,) = [
        a for a in client.get("/api/tournaments/cup/availability").json() if a["slug"] == "LS"
    ]
    assert (longsword["entered"], longsword["taken"]) == (1, 2)
    (card,) = client.get("/api/tournaments/open").json()
    assert {d["slug"]: d["entered"] for d in card["disciplines"]}["LS"] == 1

    restored = client.post(
        "/api/tournaments/cup/rules",
        json={"phase": "parsing", "kind": "row_restore", "target": rows["Boris"], "payload": {}},
        headers=organizer,
    )
    assert restored.status_code == 201, restored.text
    (longsword,) = [
        a for a in client.get("/api/tournaments/cup/availability").json() if a["slug"] == "LS"
    ]
    assert longsword["entered"] == 2


# ------------------------------------------------------------ side events


def add_item(client, organizer, name, category):
    response = client.post(
        "/api/tournaments/cup/extra-items",
        json={"name": name, "category": category, "price": 300},
        headers=organizer,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_seminars_and_other_events_have_rosters_the_afterparty_does_not(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    seminar = add_item(client, organizer, "Seminář Liechtenauer", "seminar")
    add_item(client, organizer, "Afterparty", "afterparty")
    walk = add_item(client, organizer, "Prohlídka hradu", "other_action")
    add_item(client, organizer, "Tričko", "merch")
    register(
        client,
        auth_headers(email="a@example.com", name="Adéla"),
        extras=[{"extra_item_id": seminar}],
    )
    paid = register(
        client,
        auth_headers(email="b@example.com", name="Boris"),
        extras=[{"extra_item_id": seminar}, {"extra_item_id": walk}],
    )
    pay(paid["vs"])

    by_slug = rosters(client)

    # the disciplines first, then the events in the order they were offered
    assert [(r["kind"], r["slug"]) for r in by_slug.values()] == [
        ("individual", "LS"),
        ("individual", "SB"),
        ("event", str(seminar)),
        ("event", str(walk)),
    ]
    assert by_slug[str(seminar)]["name"] == "Seminář Liechtenauer"
    assert seated(by_slug[str(seminar)]) == [(1, "Boris", "yes", False), (2, "Adéla", "no", True)]
    assert [row["name"] for row in by_slug[str(walk)]["seated"]] == ["Boris"]
    assert by_slug[str(seminar)]["line"] is False
