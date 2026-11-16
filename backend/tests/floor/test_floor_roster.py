"""The floor roster against the public roster (spec floor-roster).

Each scenario builds a tournament through the API and asks both the floor's
office adapter and `entrants.rosters()` who is seated, per discipline. The
public roster carries no keys, so entrants are compared by what both state:
name, club, nationality and HEMA Ratings id for a fencer, and name and
membership count for a team.
"""

from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import entrants, hr_match, list_counts
from app.db import get_session
from app.floor.adapters import office
from app.floor.roster import Roster
from app.importer import store_decision
from app.main import app
from app.models import (
    Fencer,
    Registration,
    RegistrationsKeptBy,
    Rule,
    SheetRowNumber,
    Tournament,
)
from tests import contract_seed
from tests.conftest import credit_registration
from tests.test_entrants import enter_team, register, setup_team_tournament, setup_tournament


def db_session() -> Session:
    return next(app.dependency_overrides[get_session]())


def tournament(session: Session, slug: str = "cup") -> Tournament:
    return session.scalars(select(Tournament).where(Tournament.slug == slug)).one()


def assert_floor_matches_public(slug: str = "cup") -> Roster:
    """Per discipline, the floor's entrants are the public roster's seated."""
    session = db_session()
    found = tournament(session, slug)
    floor = office.roster(session, found)
    persons = {person.key: person for person in floor.persons}
    public = {roster.slug: roster for roster in entrants.rosters(session, found)}
    assert [d.slug for d in floor.disciplines] == [d.slug for d in found.disciplines]
    for discipline in floor.disciplines:
        seated = public[discipline.slug].seated
        if discipline.kind == "individual":
            expected = Counter(
                (row.name, row.club, row.nationality, row.hr_id)
                for row in seated
                if isinstance(row, entrants.EntrantRow)
            )
            actual = Counter(
                (p.name, p.club, p.nationality, p.hr_id)
                for entry in floor.individuals
                if entry.discipline == discipline.slug
                for p in [persons[entry.person]]
            )
        else:
            expected = Counter(
                (row.name, len(row.members)) for row in seated if isinstance(row, entrants.TeamRow)
            )
            actual = Counter(
                (team.name, len(team.members))
                for team in floor.teams
                if team.discipline == discipline.slug
            )
        assert actual == expected, discipline.slug
        assert len(seated) == sum(expected.values())
    return floor


def registration_of(email: str) -> Registration:
    return (
        db_session().scalars(select(Registration).join(Fencer).where(Fencer.email == email)).one()
    )


def pay(email: str) -> None:
    session = db_session()
    registration = session.scalars(
        select(Registration).join(Fencer).where(Fencer.email == email)
    ).one()
    credit_registration(session, registration, registration.total_amount * 100)


def set_hr_id(email: str, hr_id: int) -> None:
    session = db_session()
    session.scalars(select(Fencer).where(Fencer.email == email)).one().hr_id = hr_id
    session.commit()


def save_roster(client, headers, team_id: int, members: list[dict]) -> None:
    response = client.put(
        f"/api/tournaments/cup/my-registration/teams/{team_id}/roster",
        json={"members": members},
        headers=headers,
    )
    assert response.status_code == 200, response.text


# ------------------------------------------------------------ the seated set


def test_the_seeded_tournament(client, auth_headers, engine):
    contract_seed.build(client, auth_headers, engine)
    floor = assert_floor_matches_public(contract_seed.SLUG)
    assert {d.kind for d in floor.disciplines} == {"individual", "team"}


def test_queued_fencers_are_not_listed_and_unpaid_ones_are(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    register(client, auth_headers(email="a@example.com", name="Adéla"), disciplines=("LS", "SB"))
    register(client, auth_headers(email="b@example.com", name="Boris"), disciplines=("SB",))
    pay("a@example.com")

    floor = assert_floor_matches_public()

    by_discipline = Counter(entry.discipline for entry in floor.individuals)
    assert by_discipline == {"LS": 1, "SB": 1}
    paid = {(entry.discipline, entry.paid) for entry in floor.individuals}
    assert paid == {("LS", True), ("SB", True)}
    # one human in two disciplines is one person
    (adela,) = floor.persons
    assert adela.name == "Adéla"


def test_an_unpaid_seated_fencer_is_listed_unpaid(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    register(client, auth_headers(email="a@example.com", name="Adéla"))

    floor = assert_floor_matches_public()

    (entry,) = floor.individuals
    assert entry.paid is False


def test_organizer_kept_registrations(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer, payments=False)
    register(client, auth_headers(email="a@example.com", name="Adéla"))
    register(client, auth_headers(email="b@example.com", name="Boris"))
    session = db_session()
    tournament(session).registrations_kept_by = RegistrationsKeptBy.ORGANIZER
    session.commit()

    floor = assert_floor_matches_public()

    assert len(floor.individuals) == 2


def test_a_console_correction_stands_on_the_floor(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    register(client, auth_headers(email="a@example.com", name="Jan Novak"))
    (row,) = client.get("/api/tournaments/cup/sheet", headers=organizer).json()["rows"]
    response = client.post(
        "/api/tournaments/cup/rules",
        json={
            "phase": "parsing",
            "kind": "field_edit",
            "target": row["id"],
            "payload": {"field": "club", "value": "Klub Y"},
        },
        headers=organizer,
    )
    assert response.status_code == 201, response.text

    floor = assert_floor_matches_public()

    (person,) = floor.persons
    assert person.club == "Klub Y"


def test_a_waitlisted_team_and_a_removed_registrations_team_are_not_listed(client, auth_headers):
    organizer = auth_headers()
    setup_team_tournament(client, organizer)
    captain = auth_headers(email="a@example.com", name="Adéla")
    draci = enter_team(client, captain, "Draci")["teams"][0]["id"]
    save_roster(client, captain, draci, [{"name": "Eva"}, {"name": "Filip"}])
    enter_team(client, auth_headers(email="b@example.com", name="Boris"), "Vlci")

    floor = assert_floor_matches_public()
    (team,) = floor.teams
    assert (team.key, team.name, len(team.members)) == (f"team:{draci}", "Draci", 2)
    assert {person.name for person in floor.persons} == {"Eva", "Filip"}

    # a deletion of a live registration's row can no longer be made; the rule
    # is written as one made before `organizer-cancels-registration` stood
    session = db_session()
    session.add(
        Rule(
            tournament_id=tournament(session).id,
            phase="fencers",
            kind="row_delete",
            target=f"reg:{registration_of('a@example.com').id}",
            payload={},
            created_by=1,
        )
    )
    session.commit()

    floor = assert_floor_matches_public()
    assert floor.teams == ()
    assert floor.persons == ()


# ------------------------------------------------------------ who is one person


def individual_and_team(client, auth_headers, member: dict, other: dict | None = None):
    """Adéla fences Longsword Open and is a member of her own team."""
    organizer = auth_headers()
    setup_tournament(client, organizer, payments=False)
    client.post(
        "/api/tournaments/cup/disciplines",
        json={
            "slug": "TM",
            "weapon": "LS",
            "capacity": 4,
            "fee": 3000,
            "kind": "team",
            "team_min": 2,
            "team_max": 4,
        },
        headers=organizer,
    )
    captain = auth_headers(email="a@example.com", name="Adéla")
    team_id = register(client, captain, teams=[{"slug": "TM", "name": "Draci"}])["teams"][0]["id"]
    save_roster(client, captain, team_id, [member, other or {"name": "Filip"}])
    return assert_floor_matches_public()


def test_an_individual_on_a_team_with_one_identifier_is_one_person(client, auth_headers):
    floor = individual_and_team(client, auth_headers, {"name": "Adéla Nováková", "hr_id": 123})
    # the member states 123, the fencer nothing, and their names differ: two persons
    assert len(floor.persons) == 3
    set_hr_id("a@example.com", 123)

    floor = assert_floor_matches_public()

    (individual,) = floor.individuals
    (team,) = floor.teams
    assert individual.person.startswith("reg:")
    assert team.members[0] == individual.person
    assert len(floor.persons) == 2
    adela = next(p for p in floor.persons if p.key == individual.person)
    # the anchor's name, not the roster's spelling
    assert (adela.name, adela.hr_id) == ("Adéla", 123)


def test_a_member_without_an_identifier_joins_by_folded_name(client, auth_headers):
    individual_and_team(client, auth_headers, {"name": "  adela ", "club": None})
    set_hr_id("a@example.com", 123)

    floor = assert_floor_matches_public()

    (individual,) = floor.individuals
    (team,) = floor.teams
    assert team.members[0] == individual.person
    assert len(floor.persons) == 2


def test_a_proposed_identifier_is_no_identifier(client, auth_headers):
    """A matcher's proposal is not stored on the member, so the member still
    joins by name — as the public count joins it."""
    individual_and_team(client, auth_headers, {"name": "Adéla", "club": None})
    session = db_session()
    found = tournament(session)
    store_decision(session, found, "hr_match", hr_match.identity_key("Adéla", None), {"hr_id": 456})
    session.commit()
    set_hr_id("a@example.com", 123)

    floor = assert_floor_matches_public()

    assert len(floor.persons) == 2


def test_two_identifiers_are_two_people(client, auth_headers):
    individual_and_team(client, auth_headers, {"name": "Adéla", "hr_id": 456})
    set_hr_id("a@example.com", 123)

    floor = assert_floor_matches_public()

    assert len(floor.persons) == 3
    (team,) = floor.teams
    assert team.members[0].startswith("mem:")


def test_two_registrations_sharing_an_identifier_stay_two(client, auth_headers):
    individual_and_team(client, auth_headers, {"name": "Adéla", "hr_id": 123})
    register(client, auth_headers(email="b@example.com", name="Adéla Dvojnice"))
    set_hr_id("a@example.com", 123)
    set_hr_id("b@example.com", 123)

    floor = assert_floor_matches_public()

    assert len(floor.persons) == 3
    assert all(entry.person.startswith("reg:") for entry in floor.individuals)
    (team,) = floor.teams
    # the member joins the first of them
    assert team.members[0] == f"reg:{registration_of('a@example.com').id}"


def test_namesakes_on_one_team_stay_two(client, auth_headers):
    floor = individual_and_team(
        client, auth_headers, {"name": "Petr Svoboda"}, {"name": "petr  svoboda"}
    )

    (team,) = floor.teams
    assert len(set(team.members)) == 2


def test_the_floor_counts_the_people_the_public_list_counts(client, auth_headers):
    individual_and_team(client, auth_headers, {"name": "adéla", "club": None})
    register(client, auth_headers(email="b@example.com", name="Filip"))
    session = db_session()
    found = tournament(session)

    floor = office.roster(session, found)
    seated = list_counts.seated_entrants(session, [found], {})
    ((fencers, _),) = list_counts.entrant_counts(seated).values()

    # Adéla alone and on her team, Filip alone and Filip on the team
    assert len(floor.persons) == fencers == 2


# ------------------------------------------------------------ day facts


def test_disciplines_carry_their_id_and_the_day_is_stated(client, auth_headers):
    setup_tournament(client, auth_headers())
    session = db_session()
    found = tournament(session)

    floor = office.roster(session, found)

    assert [d.id for d in floor.disciplines] == [d.id for d in found.disciplines]
    assert floor.date == found.date
    assert floor.timezone == (found.timezone or "Europe/Prague")


# ------------------------------------------------------------ it reads only


def test_building_the_roster_writes_nothing(client, auth_headers):
    organizer = auth_headers()
    setup_tournament(client, organizer)
    register(client, auth_headers(email="a@example.com", name="Adéla"))
    session = db_session()

    def counts() -> tuple[int | None, ...]:
        return tuple(
            session.scalar(select(func.count()).select_from(model))
            for model in (Rule, Registration, SheetRowNumber)
        )

    before = counts()
    office.roster(session, tournament(session))
    assert not session.new and not session.dirty and not session.deleted
    assert counts() == before
