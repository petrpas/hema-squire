"""Account deletion (spec account-deletion): asked for with the password, held
for seven days, then the account becomes a credential-less record that keeps a
name only where a held roster lists it."""

import datetime
from datetime import UTC, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import account_deletion, nameresolve
from app.mail import get_mailer
from app.main import app
from app.models import (
    AccountErasure,
    Fencer,
    FencerProfileAudit,
    OutgoingMail,
    PaymentCredit,
    PaymentWaiver,
    Registration,
    RegistrationState,
    Role,
    Rule,
    RuleJournalEntry,
    Tournament,
    TournamentOrganizer,
)
from tests.conftest import credit_registration, enable_payments, publish

PASSWORD = "correct-horse"


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


def body(message) -> str:
    return message.get_body(preferencelist=("plain",)).get_content()


def make_cup(client, organizer, slug="cup", payments=False):
    client.post(
        "/api/tournaments",
        json={"slug": slug, "display_name": slug.title(), "date": "2099-12-05"},
        headers=organizer,
    )
    client.post(
        f"/api/tournaments/{slug}/disciplines",
        json={"slug": "LS", "weapon": "LS", "capacity": 10, "fee": 800},
        headers=organizer,
    )
    if payments:
        enable_payments(client, organizer, slug)
    publish(client, organizer, slug)


def register(client, headers, slug="cup"):
    response = client.post(
        f"/api/tournaments/{slug}/register", json={"disciplines": ["LS"]}, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()


def fencer_row(session, email) -> Fencer:
    return session.scalars(select(Fencer).where(Fencer.email == email)).one()


def hold(engine, slug="cup"):
    """Move a tournament into the past: it has been fenced."""
    with Session(engine) as session:
        tournament = session.scalars(select(Tournament).where(Tournament.slug == slug)).one()
        tournament.date = datetime.datetime.now(UTC).date() - timedelta(days=30)
        session.commit()


def run_due(engine, email, mailer=None) -> int:
    """Age the request past its seven days and run the scheduler's pass."""
    with Session(engine) as session:
        fencer = fencer_row(session, email)
        fencer_id = fencer.id
        fencer.deletion_requested_at = datetime.datetime.now(UTC) - timedelta(days=8)
        session.commit()
        account_deletion.run_pass(session, mailer or CollectingMailer())
    return fencer_id


def request(client, headers, password=PASSWORD):
    return client.post("/api/account/deletion", json={"password": password}, headers=headers)


# ------------------------------------------------------------------ request


def test_a_request_confirmed_by_password_is_recorded_and_mailed(client, auth_headers, mailbox):
    me = auth_headers(email="me@example.com", name="Me", role=Role.FENCER)

    response = request(client, me)

    assert response.status_code == 200, response.text
    assert response.json()["deletion_effective_at"] is not None
    (message,) = mailbox.sent
    assert message["To"] == "me@example.com"


def test_a_wrong_password_records_nothing(client, auth_headers, engine):
    me = auth_headers(email="me@example.com", name="Me", role=Role.FENCER)

    assert request(client, me, "wrong-password").status_code == 403
    with Session(engine) as session:
        assert fencer_row(session, "me@example.com").deletion_requested_at is None


def test_a_withdrawal_leaves_the_account_as_it_was(client, auth_headers, engine, mailbox):
    me = auth_headers(email="me@example.com", name="Me", role=Role.FENCER)
    request(client, me)

    response = client.post("/api/account/deletion/withdraw", headers=me)

    assert response.status_code == 200
    assert response.json()["deletion_effective_at"] is None
    assert len(mailbox.sent) == 2
    with Session(engine) as session:
        account_deletion.run_pass(session, CollectingMailer())
        fencer = fencer_row(session, "me@example.com")
        assert fencer.deleted_at is None
        assert fencer.password_hash is not None


def test_an_owner_is_refused_and_told_what_to_hand_over(client, auth_headers):
    owner = auth_headers()
    make_cup(client, owner)

    impact = client.get("/api/account/deletion", headers=owner).json()
    assert impact["blockers"] == [{"kind": "owner", "tournaments": ["Cup"]}]
    assert request(client, owner).status_code == 409


def test_ownership_acquired_in_the_grace_period_holds_execution(client, auth_headers, engine):
    admin = auth_headers(email="admin@example.com", name="Admin", role=Role.ADMIN)
    me = auth_headers(email="me@example.com", name="Me")
    request(client, me)
    make_cup(client, me)

    fencer_id = run_due(engine, "me@example.com")

    with Session(engine) as session:
        fencer = session.get(Fencer, fencer_id)
        assert fencer is not None
        assert fencer.deleted_at is None
        assert fencer.deletion_requested_at is not None
    deferred = client.get("/api/admin/deletions", headers=admin).json()
    assert [(d["fencer_id"], d["blockers"][0]["kind"]) for d in deferred] == [(fencer_id, "owner")]


def test_the_last_admin_is_refused(client, auth_headers):
    admin = auth_headers(email="admin@example.com", name="Admin", role=Role.ADMIN)
    assert request(client, admin).status_code == 409


# ---------------------------------------------------------------- execution


def test_execution_ends_the_login_and_a_new_signup_is_unconnected(client, auth_headers, engine):
    organizer = auth_headers()
    make_cup(client, organizer)
    me = auth_headers(email="me@example.com", name="Me Fencer", role=Role.FENCER)
    register(client, me)
    request(client, me)
    final = CollectingMailer()

    fencer_id = run_due(engine, "me@example.com", final)

    assert client.get("/api/account", headers=me).status_code == 401
    # the owner of the cancelled entry is told, and the person is sent the
    # last message to the address they had
    assert sorted(m["To"] for m in final.sent) == ["me@example.com", "organizer@example.com"]
    with Session(engine) as session:
        fencer = session.get(Fencer, fencer_id)
        assert fencer is not None
        assert (fencer.email, fencer.password_hash, fencer.role) == (None, None, Role.FENCER)
        assert fencer.deleted_at is not None
        assert (
            session.scalar(
                select(func.count())
                .select_from(FencerProfileAudit)
                .where(FencerProfileAudit.fencer_id == fencer_id)
            )
            == 0
        )
        assert session.scalars(select(AccountErasure.kind)).all() == ["account"]

    again = auth_headers(email="me@example.com", name="Me Again", role=Role.FENCER)
    with Session(engine) as session:
        fresh = fencer_row(session, "me@example.com")
        assert fresh.id != fencer_id
        assert fresh.registrations == []
    assert client.get("/api/account", headers=again).status_code == 200


def test_a_name_stays_on_a_held_roster(client, auth_headers, engine):
    organizer = auth_headers()
    make_cup(client, organizer)
    me = auth_headers(email="me@example.com", name="Jana Held", role=Role.FENCER)
    client.patch("/api/account", json={"club": "Klub H"}, headers=me)
    register(client, me)
    hold(engine)
    request(client, me)

    fencer_id = run_due(engine, "me@example.com")

    with Session(engine) as session:
        fencer = session.get(Fencer, fencer_id)
        assert fencer is not None
        assert (fencer.display_name, fencer.club) == ("Jana Held", "Klub H")
    (roster,) = client.get("/api/tournaments/cup/entrants").json()["rosters"][:1]
    (row,) = roster["seated"]
    assert row["name"] == "Jana Held"
    assert (row["paid"], row["faded"]) == (None, False)


def test_a_name_without_a_held_roster_goes(client, auth_headers, engine):
    me = auth_headers(email="me@example.com", name="Never Fenced", role=Role.FENCER)
    request(client, me)

    fencer_id = run_due(engine, "me@example.com")

    with Session(engine) as session:
        fencer = session.get(Fencer, fencer_id)
        assert fencer is not None
        assert fencer.display_name == account_deletion.DELETED_LABEL
        assert (fencer.hr_id, fencer.club, fencer.nationality) == (None, None, None)


def test_a_paid_future_entry_is_cancelled_and_its_owner_told(client, auth_headers, engine):
    organizer = auth_headers()
    make_cup(client, organizer, payments=True)
    me = auth_headers(email="me@example.com", name="Petra Paid", role=Role.FENCER)
    entry = register(client, me)
    with Session(engine) as session:
        registration = session.scalars(select(Registration)).one()
        credit_registration(session, registration, 80000)
    request(client, me)
    mailer = CollectingMailer()

    run_due(engine, "me@example.com", mailer)

    with Session(engine) as session:
        registration = session.scalars(select(Registration)).one()
        assert registration.state is RegistrationState.CANCELLED
        # money is not moved: the credit stands, unreversed
        credits = session.scalars(select(PaymentCredit)).all()
        assert [(c.amount_cents, c.reversed_at) for c in credits] == [(80000, None)]
    (notice,) = [m for m in mailer.sent if m["To"] == "organizer@example.com"]
    text = body(notice)
    assert "Petra Paid" in text
    assert str(entry["vs"]) in text
    assert "800" in text


def test_every_address_is_taken_out_of_the_copies(client, auth_headers, engine):
    organizer = auth_headers()
    make_cup(client, organizer)
    me = auth_headers(email="old@example.com", name="Mover", role=Role.FENCER)
    register(client, me)
    client.patch("/api/account", json={"email": "new@example.com"}, headers=me)
    other = auth_headers(email="other@example.com", name="Other", role=Role.FENCER)
    register(client, other)
    with Session(engine) as session:
        cup = session.scalars(select(Tournament)).one()
        org = fencer_row(session, "organizer@example.com")
        mine = session.scalars(
            select(Registration).join(Fencer).where(Fencer.display_name == "Mover")
        ).one()
        mine.notes = "vegetarian"
        theirs = session.scalars(
            select(Registration).join(Fencer).where(Fencer.email == "other@example.com")
        ).one()
        # a child's seat entered under the parent's address keeps it
        theirs.contact_email = "old@example.com"
        rule = Rule(
            tournament_id=cup.id,
            phase="fencers",
            kind="field_edit",
            target="reg:1",
            payload={"field": "email", "value": "OLD@example.com"},
            created_by=org.id,
        )
        session.add(rule)
        session.flush()
        session.add(
            RuleJournalEntry(
                tournament_id=cup.id,
                rule_id=rule.id,
                action="created",
                actor_id=org.id,
                content={"payload": {"field": "email", "value": "old@example.com"}},
            )
        )
        session.add(
            PaymentWaiver(
                tournament_id=cup.id,
                registration_id=mine.id,
                granted_by="Mover <new@example.com>",
            )
        )
        session.commit()
    request(client, me)

    run_due(engine, "new@example.com")

    with Session(engine) as session:
        rule = session.scalars(select(Rule)).one()
        assert rule.payload == {"field": "email", "value": None}
        entry = session.scalars(select(RuleJournalEntry)).one()
        assert entry.content == {"payload": {"field": "email", "value": None}}
        waiver = session.scalars(select(PaymentWaiver)).one()
        assert waiver.granted_by == "Mover"
        mine = session.scalars(
            select(Registration).join(Fencer).where(Fencer.display_name != "Other")
        ).one()
        assert (mine.notes, mine.contact_email) == (None, None)
        theirs = session.scalars(
            select(Registration).join(Fencer).where(Fencer.display_name == "Other")
        ).one()
        assert theirs.contact_email == "old@example.com"
        assert all(
            mail.recipient not in ("old@example.com", "new@example.com")
            for mail in session.scalars(select(OutgoingMail))
        )


def test_execution_is_idempotent(client, auth_headers, engine):
    me = auth_headers(email="me@example.com", name="Me", role=Role.FENCER)
    request(client, me)
    fencer_id = run_due(engine, "me@example.com")

    with Session(engine) as session:
        fencer = session.get(Fencer, fencer_id)
        assert fencer is not None
        assert account_deletion.execute(session, fencer, CollectingMailer()) is True
        session.commit()
        assert session.scalar(select(func.count()).select_from(AccountErasure)) == 1


def test_team_memberships_go(client, auth_headers, engine):
    owner = auth_headers()
    make_cup(client, owner)
    helper = auth_headers(email="helper@example.com", name="Helper")
    client.post("/api/tournaments/cup/team", json={"email": "helper@example.com"}, headers=owner)
    request(client, helper)

    run_due(engine, "helper@example.com")

    with Session(engine) as session:
        assert session.scalars(select(TournamentOrganizer)).all() == []


# ------------------------------------------------------------ deleted records


def test_a_deleted_record_shares_no_hr_id_and_is_never_proposed(client, auth_headers, engine):
    admin = auth_headers(email="admin@example.com", name="Admin", role=Role.ADMIN)
    organizer = auth_headers()
    make_cup(client, organizer)
    me = auth_headers(email="me@example.com", name="Jana Held", role=Role.FENCER)
    register(client, me)
    hold(engine)
    with Session(engine) as session:
        fencer_row(session, "me@example.com").hr_id = 4242
        session.commit()
    request(client, me)
    fencer_id = run_due(engine, "me@example.com")
    back = auth_headers(email="back@example.com", name="Jana Held", role=Role.FENCER)
    with Session(engine) as session:
        fencer_row(session, "back@example.com").hr_id = 4242
        session.commit()

    people = {p["id"]: p for p in client.get("/api/admin/accounts", headers=admin).json()}
    assert people[fencer_id]["deleted"] is True
    assert not any(p["hr_shared"] for p in people.values())
    assert back is not None
    with Session(engine) as session:
        cup = session.scalars(select(Tournament)).one()
        assert fencer_id not in {fid for fid, _ in nameresolve.roster(session, cup)}


def test_an_admin_erases_an_identity(client, auth_headers, engine):
    admin = auth_headers(email="admin@example.com", name="Admin", role=Role.ADMIN)
    organizer = auth_headers()
    make_cup(client, organizer)
    me = auth_headers(email="me@example.com", name="Jana Held", role=Role.FENCER)
    register(client, me)
    hold(engine)
    request(client, me)
    fencer_id = run_due(engine, "me@example.com")

    response = client.post(f"/api/admin/accounts/{fencer_id}/erase-identity", headers=admin)

    assert response.status_code == 200, response.text
    (roster,) = client.get("/api/tournaments/cup/entrants").json()["rosters"][:1]
    (row,) = roster["seated"]
    assert (row["name"], row["hr_id"]) == (account_deletion.DELETED_LABEL, None)
    with Session(engine) as session:
        assert sorted(session.scalars(select(AccountErasure.kind)).all()) == [
            "account",
            "identity",
        ]


def test_an_admin_cannot_erase_a_live_account(client, auth_headers, engine):
    admin = auth_headers(email="admin@example.com", name="Admin", role=Role.ADMIN)
    auth_headers(email="me@example.com", name="Me", role=Role.FENCER)
    with Session(engine) as session:
        fencer_id = fencer_row(session, "me@example.com").id
    assert (
        client.post(f"/api/admin/accounts/{fencer_id}/erase-identity", headers=admin).status_code
        == 409
    )


def test_a_restore_erases_again(client, auth_headers, engine):
    me = auth_headers(email="me@example.com", name="Me", role=Role.FENCER)
    with Session(engine) as session:
        fencer_id = fencer_row(session, "me@example.com").id

    # the restored database predates the deletion; the log from the replica
    # says it happened
    with Session(engine) as session:
        changed = account_deletion.reapply(session, [(fencer_id, "account")])
        session.commit()
        fencer = session.get(Fencer, fencer_id)
        assert fencer is not None
        assert changed == 1
        assert (fencer.email, fencer.password_hash) == (None, None)
        assert fencer.deleted_at is not None
    assert client.get("/api/account", headers=me).status_code == 401
    with Session(engine) as session:
        assert account_deletion.reapply(session, [(fencer_id, "account")]) == 0


def test_a_deleted_account_survives_export_and_restore(client, auth_headers, engine):
    organizer = auth_headers()
    make_cup(client, organizer)
    me = auth_headers(email="me@example.com", name="Jana Held", role=Role.FENCER)
    register(client, me)
    hold(engine)
    request(client, me)
    run_due(engine, "me@example.com")

    document = client.get("/api/tournaments/cup/export/json", headers=organizer).json()
    (record,) = [f for f in document["fencers"] if f["display_name"] == "Jana Held"]
    assert record["deleted_at"] is not None
    assert record["email"] is None
