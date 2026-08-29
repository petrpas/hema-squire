"""The fixed number a row carries in a tournament's table (spec etl-console,
Fixed fencer number)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import rownumbers
from app.models import SheetRowNumber, Tournament
from tests.conftest import publish


def setup(client, organizer):
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    client.patch(
        "/api/tournaments/cup",
        json={"location": "Brno", "organizers": [{"name": "Cup Org", "link": None}]},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "LS", "weapon": "LS", "capacity": 10, "fee": 1000},
        headers=organizer,
    )
    publish(client, organizer, "cup")


def tournament_of(session) -> Tournament:
    return session.scalar(select(Tournament).where(Tournament.slug == "cup"))


def test_allocation_is_stable_and_never_reissued(client, auth_headers, engine):
    setup(client, auth_headers())
    with Session(engine) as session:
        cup = tournament_of(session)
        first = rownumbers.allocate(session, cup, ["reg:1", "reg:2", "imp:aa"])
        session.commit()
        assert list(first.values()) == [1, 2, 3]

        # asking again returns what was allocated, mints nothing
        again = rownumbers.allocate(session, cup, ["imp:aa", "reg:1"])
        session.commit()
        assert again == {"imp:aa": 3, "reg:1": 1}

        # a row leaving the table is a rule, never a freed allocation: its
        # allocation stands, so the next row minted takes the next free number
        assert rownumbers.allocate(session, cup, ["reg:9"]) == {"reg:9": 4}

        # only a clear deletes an allocation, and what it releases is available
        # again — otherwise its release would mean nothing (spec table-import,
        # Clearing releases the cleared numbers)
        session.delete(session.scalar(select(SheetRowNumber).where(SheetRowNumber.number == 2)))
        session.commit()
        assert rownumbers.allocate(session, cup, ["reg:10"]) == {"reg:10": 2}


def test_numbers_are_per_tournament(client, auth_headers, engine):
    organizer = auth_headers()
    setup(client, organizer)
    client.post(
        "/api/tournaments",
        json={"slug": "other", "display_name": "Other", "date": "2026-12-06"},
        headers=organizer,
    )
    with Session(engine) as session:
        cup = tournament_of(session)
        other = session.scalar(select(Tournament).where(Tournament.slug == "other"))
        rownumbers.allocate(session, cup, ["reg:1", "reg:2"])
        session.commit()
        assert rownumbers.allocate(session, other, ["reg:7"]) == {"reg:7": 1}


def register(client, auth_headers, email, name):
    fencer = auth_headers(email=email, name=name)
    response = client.post(
        "/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=fencer
    )
    assert response.status_code == 201, response.text


def registration_row_ids(session) -> list[str]:
    """Sheet row ids of the tournament's registrations, in registration order."""
    from app.models import Registration

    rows = session.scalars(
        select(Registration)
        .where(Registration.tournament_id == tournament_of(session).id)
        .order_by(Registration.registered_at, Registration.id)
    ).all()
    return [f"reg:{r.id}" for r in rows]


def test_registration_takes_a_number_and_keeps_it(client, auth_headers, engine):
    organizer = auth_headers()
    setup(client, organizer)
    register(client, auth_headers, "one@example.com", "One")
    register(client, auth_headers, "two@example.com", "Two")
    register(client, auth_headers, "three@example.com", "Three")

    with Session(engine) as session:
        ids = registration_row_ids(session)
        numbers = rownumbers.numbers_for(session, tournament_of(session))
    assert [numbers[row_id] for row_id in ids] == [1, 2, 3]

    # deleting an earlier row is a rule; it frees no number and moves none
    response = client.post(
        "/api/tournaments/cup/rules",
        json={"phase": "fencers", "kind": "row_delete", "target": ids[0], "payload": {}},
        headers=organizer,
    )
    assert response.status_code == 201, response.text
    with Session(engine) as session:
        assert rownumbers.numbers_for(session, tournament_of(session)) == numbers


def test_import_numbers_new_fingerprints_only(client, auth_headers, engine):
    """A re-upload allocates nothing for rows the file did not change; a
    changed row is a new fingerprint and takes a new number."""
    import io

    from app.importer import get_import_parser
    from app.main import app
    from tests.test_import import CSV, FakeParser, override_parser

    organizer = auth_headers()
    setup(client, organizer)
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "SA", "weapon": "SA", "capacity": 20, "fee": 800},
        headers=organizer,
    )
    override_parser(FakeParser())
    try:

        def upload(content):
            return client.post(
                "/api/tournaments/cup/import",
                files={"file": ("regs.csv", io.BytesIO(content.encode()), "text/csv")},
                headers=organizer,
            )

        assert upload(CSV).status_code == 202
        with Session(engine) as session:
            first = rownumbers.numbers_for(session, tournament_of(session))
        assert sorted(first.values()) == [1, 2]

        # identical file: same fingerprints, so nothing new is minted
        assert upload(CSV).status_code == 202
        with Session(engine) as session:
            assert rownumbers.numbers_for(session, tournament_of(session)) == first

        # one row corrected: a new fingerprint, and a number that counts on
        corrected = CSV.replace("Twerchhau", "Twerchhaw")
        assert upload(corrected).status_code == 202
        with Session(engine) as session:
            after = rownumbers.numbers_for(session, tournament_of(session))
        assert len(after) == 3
        assert sorted(after.values()) == [1, 2, 3]
        assert {k: v for k, v in after.items() if k in first} == first
    finally:
        app.dependency_overrides.pop(get_import_parser, None)


def test_row_without_an_allocation_carries_null(client, auth_headers, engine):
    """A visible gap beats a number that lies: nothing falls back to the row's
    position in the list."""
    organizer = auth_headers()
    setup(client, organizer)
    register(client, auth_headers, "one@example.com", "One")
    with Session(engine) as session:
        session.delete(session.scalar(select(SheetRowNumber)))
        session.commit()
    rows = client.get("/api/tournaments/cup/sheet", headers=organizer).json()["rows"]
    assert [row["number"] for row in rows] == [None]
