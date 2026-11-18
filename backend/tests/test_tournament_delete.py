"""The tournament cascade leaves nothing behind (spec tournament-admin,
Tournament deletion and cancellation: an Admin's delete removes everything
recorded under the tournament, and no account).

The test is driven by the model metadata rather than by a list of its own: it
first asserts that every table reachable from `tournaments` by foreign key
holds a row for the doomed tournament, then that none does afterwards. A table
added later fails the first assertion until the fixture populates it, and the
second until `app.tournament_delete` removes it."""

import datetime

from sqlalchemy import Table, func, select

from app.db import get_session
from app.floor.models import (
    FloorArrival,
    FloorAssignment,
    FloorBout,
    FloorBracket,
    FloorBracketSlot,
    FloorDay,
    FloorDisciplineDay,
    FloorDraw,
    FloorFormat,
    FloorLineup,
    FloorLocalPerson,
    FloorOfficial,
    FloorOfficialDay,
    FloorOfficialDiscipline,
    FloorPin,
    FloorPiste,
    FloorPisteDiscipline,
    FloorPlan,
    FloorPlanActivity,
    FloorPool,
    FloorPoolMember,
    FloorPoolRanking,
    FloorPublishedResult,
    FloorRingKey,
    FloorSettings,
    FloorSheetEdit,
    FloorSheetEntry,
    FloorSheetFetch,
    FloorSheetRating,
    FloorSheetTeam,
    FloorSnapshot,
    FloorSnapshotEntrant,
    FloorWithdrawal,
)
from app.main import app
from app.models import (
    BankTransaction,
    Base,
    CreditOrigin,
    CreditSource,
    Currency,
    Discipline,
    DiscountCode,
    ExtraCategory,
    ExtraItem,
    Fencer,
    HRRatingSnapshot,
    HRSnapshotRating,
    ImportBatch,
    ImportDecision,
    ImportedRow,
    ManualPayment,
    ManualRow,
    Operation,
    OperationKind,
    PaymentCredit,
    PaymentEvent,
    PaymentMethod,
    PaymentWaiver,
    Registration,
    RegistrationExtra,
    RosterChange,
    RosterChangeKind,
    Rule,
    RuleJournalEntry,
    SheetRowNumber,
    Team,
    TeamMember,
    Tournament,
)
from app.tournament_delete import delete_tournament
from tests.conftest import enable_payments, publish


def db_session():
    return next(app.dependency_overrides[get_session]())


def tables_under_tournaments() -> list[Table]:
    """Every table that refers to `tournaments` by foreign key, directly or
    through another such table. `fencers` is outside: accounts survive."""
    reached = {"tournaments"}
    grew = True
    while grew:
        grew = False
        for table in Base.metadata.sorted_tables:
            if table.name in reached or table.name == "fencers":
                continue
            if any(fk.column.table.name in reached for fk in table.foreign_keys):
                reached.add(table.name)
                grew = True
    return [Base.metadata.tables[name] for name in sorted(reached)]


def make_published_cup(client, organizer, slug: str) -> None:
    client.post(
        "/api/tournaments",
        json={"slug": slug, "display_name": slug.title(), "date": "2099-12-05"},
        headers=organizer,
    )
    client.patch(
        f"/api/tournaments/{slug}",
        json={"city": "Brno", "organizers": [{"name": "Org", "link": None}]},
        headers=organizer,
    )
    client.post(
        f"/api/tournaments/{slug}/disciplines",
        json={"slug": "LS", "weapon": "LS", "capacity": 10, "fee": 1000},
        headers=organizer,
    )
    enable_payments(client, organizer, slug)
    client.patch(
        f"/api/tournaments/{slug}",
        json={"bank_account": "CZ6508000000192000145399"},
        headers=organizer,
    )
    publish(client, organizer, slug)


def populate(session, tournament: Tournament, registration: Registration, actor: Fencer) -> None:
    """One row in every table under the tournament the API flow did not reach."""
    tid = tournament.id
    now = datetime.datetime.now(datetime.UTC)
    today = now.date()

    # a team needs a discipline to stand in; which one is beside the point here
    discipline = session.scalar(select(Discipline).where(Discipline.tournament_id == tid))
    assert discipline is not None
    item = ExtraItem(tournament_id=tid, name="Rental", category=ExtraCategory.RENTAL, price=100)
    session.add(item)
    code = DiscountCode(
        tournament_id=tid, code="c", name="C", effect={"kind": "percent", "value": 10}, scope=[]
    )
    session.add(code)
    session.flush()
    registration.discount_code = code

    team = Team(
        tournament_id=tid,
        discipline_id=discipline.id,
        registration_id=registration.id,
        name="Team",
        waitlisted_since=now,
    )
    session.add(team)
    session.flush()
    member = TeamMember(team_id=team.id, ordinal=1, name="Member")
    session.add(member)
    session.flush()
    session.add(
        RosterChange(
            team_id=team.id,
            member_id=member.id,
            member_name=member.name,
            kind=RosterChangeKind.ADDED,
            actor_fencer_id=actor.id,
        )
    )
    session.add(RegistrationExtra(registration_id=registration.id, extra_item_id=item.id))

    transaction = BankTransaction(
        tournament_id=tid,
        external_id="tx-1",
        source="csv",
        date=today,
        amount_cents=100000,
        currency="CZK",
        matched_registration_id=registration.id,
    )
    session.add(transaction)
    session.flush()
    session.add(
        PaymentEvent(
            tournament_id=tid,
            kind="matched",
            transaction_id=transaction.id,
            registration_id=registration.id,
        )
    )

    rule = Rule(
        tournament_id=tid,
        phase="match",
        kind="payment_link",
        target="tx-1",
        payload={},
        created_by=actor.id,
    )
    session.add(rule)
    session.flush()
    session.add(
        RuleJournalEntry(
            tournament_id=tid, rule_id=rule.id, action="created", actor_id=actor.id, content={}
        )
    )
    session.add(
        PaymentCredit(
            tournament_id=tid,
            registration_id=registration.id,
            amount_cents=100000,
            currency=Currency.CZK,
            value_date=today,
            source_kind=CreditSource.BANK_TRANSACTION,
            source_id=transaction.id,
            origin=CreditOrigin.PAYMENT_LINK,
            rule_id=rule.id,
        )
    )
    session.add(PaymentWaiver(tournament_id=tid, registration_id=registration.id, granted_by="a"))
    session.add(
        ManualPayment(
            tournament_id=tid,
            registration_id=registration.id,
            amount_cents=500,
            currency=Currency.CZK,
            received_on=today,
            method=PaymentMethod.CASH,
            recorded_by="a",
        )
    )

    snapshot = HRRatingSnapshot(tournament_id=tid, fencer_count=1)
    batch = ImportBatch(tournament_id=tid, filename="f.csv", uploaded_by=actor.id, row_count=1)
    session.add_all([snapshot, batch])
    session.flush()
    session.add(HRSnapshotRating(snapshot_id=snapshot.id, hr_id=1, discipline_code="LS"))
    session.add(ImportedRow(batch_id=batch.id, tournament_id=tid, row_number=1, key="r1", raw={}))
    session.add(ImportDecision(tournament_id=tid, kind="parse", key="k", payload={}))
    session.add(ManualRow(tournament_id=tid, name="Hand", registered_at=now, created_by=actor.id))
    session.add(SheetRowNumber(tournament_id=tid, row_id="r1", number=999))
    session.add(Operation(tournament_id=tid, kind=OperationKind.PARSE, started_by=actor.id))

    # the floor's tables, deleted by their prefix rather than by name
    day = FloorDay(
        tournament_id=tid, date=today, start=datetime.time(9), end=datetime.time(19), breaks=[]
    )
    piste = FloorPiste(tournament_id=tid, name="1", ordinal=1)
    official = FloorOfficial(tournament_id=tid, name="Ref", ordinal=1)
    session.add_all([day, piste, official])
    session.flush()
    session.add(FloorPisteDiscipline(piste_id=piste.id, discipline_id=discipline.id))
    session.add(FloorDisciplineDay(discipline_id=discipline.id, day_id=day.id))
    session.add(FloorOfficialDay(official_id=official.id, day_id=day.id))
    session.add(FloorOfficialDiscipline(official_id=official.id, discipline_id=discipline.id))
    session.add(
        FloorFormat(
            tournament_id=tid,
            discipline_id=discipline.id,
            pool_min=5,
            pool_max=7,
            slot_pool_bout=4,
            slot_elim_bout=6,
            pause_between_pools=5,
        )
    )
    session.add(FloorSettings(tournament_id=tid, params={}))
    plan = FloorPlan(tournament_id=tid, version=1, status="working", created_at=now)
    session.add(plan)
    session.flush()
    session.add(
        FloorPlanActivity(
            plan_id=plan.id,
            activity_id="LS:pool:1",
            discipline_id=discipline.id,
            kind="pool",
            ordinal=1,
            round=0,
            piste_id=piste.id,
            starts_at=now,
            ends_at=now,
        )
    )
    session.add(FloorPin(tournament_id=tid, kind="k", target="1", value={"k": 2}, created_at=now))
    session.add(FloorArrival(tournament_id=tid, person_key="reg:1", at=now))
    session.add(FloorWithdrawal(tournament_id=tid, entry_key="reg:1@1", at=now))
    session.add(FloorLineup(tournament_id=tid, team_key="team:1", person_key="reg:1", ordinal=1))
    session.add(FloorLocalPerson(tournament_id=tid, name="Local"))
    session.add(FloorSheetEdit(tournament_id=tid, subject="reg:1", field="club", value="Y", at=now))
    session.add(
        FloorSheetEntry(tournament_id=tid, person_key="reg:1", discipline_id=discipline.id, at=now)
    )
    session.add(FloorSheetTeam(tournament_id=tid, discipline_id=discipline.id, name="B", at=now))
    fetch = FloorSheetFetch(
        tournament_id=tid, discipline_id=discipline.id, fetched_at=now, asked=[1]
    )
    session.add(fetch)
    session.flush()
    session.add(FloorSheetRating(fetch_id=fetch.id, hr_id=1, rating=1500.0, rank=3))
    snapshot = FloorSnapshot(tournament_id=tid, discipline_id=discipline.id, closed_at=now, n=1)
    session.add(snapshot)
    session.flush()
    session.add(
        FloorSnapshotEntrant(snapshot_id=snapshot.id, entrant_key="reg:1", kind="person", name="A")
    )
    drawn = FloorDraw(tournament_id=tid, discipline_id=discipline.id, seed=1)
    session.add(drawn)
    session.flush()
    pool = FloorPool(draw_id=drawn.id, number=1, wave=1)
    session.add(pool)
    session.flush()
    session.add(FloorPoolMember(pool_id=pool.id, entrant_key="reg:1", ordinal=1, seed=1))
    session.add(
        FloorBout(
            tournament_id=tid,
            discipline_id=discipline.id,
            pool_id=pool.id,
            ordinal=1,
            a_key="reg:1",
            b_key="reg:2",
        )
    )
    session.add(
        FloorPoolRanking(
            tournament_id=tid, discipline_id=discipline.id, entrant_key="reg:1", place=1
        )
    )
    session.add(FloorRingKey(tournament_id=tid, piste_id=piste.id, key_hash="h", issued_at=now))
    bracket = FloorBracket(
        tournament_id=tid, discipline_id=discipline.id, size=2, advancing=2, confirmed_at=now
    )
    session.add(bracket)
    session.flush()
    session.add(FloorBracketSlot(bracket_id=bracket.id, round=0, position=0, entrant_key="reg:1"))
    session.add(
        FloorAssignment(
            tournament_id=tid,
            plan_id=plan.id,
            block_key="1:LS:pool:1",
            role="referee",
            slot=0,
            official_id=official.id,
            created_at=now,
        )
    )
    session.add(
        FloorPublishedResult(tournament_id=tid, discipline_id=discipline.id, published_at=now)
    )
    session.commit()


def floor_scope(table: Table, tid: int):
    if "tournament_id" in table.c:
        return table.c.tournament_id == tid
    fk = next(fk for fk in table.foreign_keys if fk.column.table.name.startswith("floor_"))
    return fk.parent.in_(select(fk.column).where(floor_scope(fk.column.table, tid)))


def rows_of(session, table: Table, tid: int, registration_ids: list[int]) -> int:
    """Rows of `table` belonging to the tournament: by its own tournament_id
    where it has one, else through the parent it hangs from."""
    if table.name == "tournaments":
        return session.scalar(select(func.count()).where(table.c.id == tid))
    if "tournament_id" in table.c:
        return session.scalar(select(func.count()).where(table.c.tournament_id == tid))
    if "registration_id" in table.c:
        return session.scalar(
            select(func.count()).where(table.c.registration_id.in_(registration_ids))
        )
    if table.name in ("team_members", "roster_changes"):
        teams = select(Team.id).where(Team.tournament_id == tid)
        return session.scalar(select(func.count()).where(table.c.team_id.in_(teams)))
    if table.name.startswith("floor_") and "tournament_id" not in table.c:
        # a floor child, however deep: through the floor parents it hangs from
        return session.scalar(select(func.count()).where(floor_scope(table, tid)))
    if table.name == "hr_snapshot_ratings":
        snapshots = select(HRRatingSnapshot.id).where(HRRatingSnapshot.tournament_id == tid)
        return session.scalar(select(func.count()).where(table.c.snapshot_id.in_(snapshots)))
    raise AssertionError(f"no way to scope {table.name} to a tournament; teach rows_of")


def test_cascade_removes_every_row_under_the_tournament_and_no_account(client, auth_headers):
    organizer = auth_headers()
    make_published_cup(client, organizer, "cup")
    make_published_cup(client, organizer, "other")
    for slug, email in (("cup", "f1@example.com"), ("other", "f2@example.com")):
        response = client.post(
            f"/api/tournaments/{slug}/register",
            json={"disciplines": ["LS"]},
            headers=auth_headers(email=email, name=email),
        )
        assert response.status_code == 201, response.text

    auth_headers(email="helper@example.com", name="Helper")
    added = client.post(
        "/api/tournaments/cup/team", json={"email": "helper@example.com"}, headers=organizer
    )
    assert added.status_code == 201, added.text

    session = db_session()
    cup = session.scalar(select(Tournament).where(Tournament.slug == "cup"))
    other = session.scalar(select(Tournament).where(Tournament.slug == "other"))
    assert cup is not None and other is not None
    registration = session.scalar(select(Registration).where(Registration.tournament_id == cup.id))
    assert registration is not None
    actor = session.scalar(select(Fencer).where(Fencer.id == cup.owner_id))
    assert actor is not None
    populate(session, cup, registration, actor)
    cup_id, registration_ids = cup.id, [registration.id]
    accounts_before = session.scalar(select(func.count()).select_from(Fencer))

    tables = tables_under_tournaments()
    unpopulated = [t.name for t in tables if rows_of(session, t, cup_id, registration_ids) == 0]
    assert unpopulated == [], f"populate() does not reach {unpopulated}"

    other_rows = {t.name: rows_of(session, t, other.id, []) for t in tables}

    delete_tournament(session, cup)
    session.commit()

    left = {t.name: n for t in tables if (n := rows_of(session, t, cup_id, registration_ids))}
    assert left == {}
    assert session.scalar(select(func.count()).select_from(Fencer)) == accounts_before
    # the other tournament keeps what it had, registrations counted by its own id
    assert {t.name: rows_of(session, t, other.id, []) for t in tables} == other_rows
