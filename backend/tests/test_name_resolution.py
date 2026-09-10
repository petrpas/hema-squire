"""Resolving a payment to a fencer by the words the payer wrote (spec
name-assisted-matching).

The property that matters more than every other test here: **a proposal moves
nothing**. It is asserted against the registration's credited amount, its
outstanding balance, its state and the mailbox — never against the
transaction's status string, which is the one thing a broken implementation
would get right."""

import io

import pytest
from sqlalchemy import select

from app.bank import ParsedStatementRow, get_statement_parser
from app.db import get_session
from app.mail import get_mailer
from app.main import app
from app.models import BankTransaction, Registration
from tests.conftest import enable_payments, publish


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


class NamingParser:
    """Stands in for the model, which reads each row and reports who the
    payment is *for*. The header carries the answer so a test can state its
    own case: `named` is what the model would have extracted, and empty means
    the text named nobody."""

    def parse_batch(self, rows):
        return [
            ParsedStatementRow(
                external_id=raw["ref"],
                date=raw["date"],
                amount_cents=int(round(float(raw["amount"]) * 100)),
                currency="CZK",
                vs=int(raw["vs"]) if raw.get("vs") else None,
                message=raw.get("note") or None,
                payer_name=raw.get("payer") or None,
                named_person=raw.get("named") or None,
            )
            for raw in rows
        ]


@pytest.fixture
def parser():
    app.dependency_overrides[get_statement_parser] = lambda: NamingParser()
    yield
    app.dependency_overrides.pop(get_statement_parser, None)


def statement(rows: list[dict]) -> bytes:
    cols = ["ref", "date", "amount", "vs", "note", "payer", "named"]
    lines = [",".join(cols)]
    for row in rows:
        lines.append(",".join(str(row.get(c, "")) for c in cols))
    return ("\n".join(lines) + "\n").encode()


def db_session():
    return next(app.dependency_overrides[get_session]())


def setup(client, organizer):
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    enable_payments(client, organizer, "cup")
    client.patch(
        "/api/tournaments/cup",
        json={"location": "Brno", "organizers": [{"name": "Cup Org", "link": None}]},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "LS", "weapon": "LS", "capacity": 30, "fee": 1000},
        headers=organizer,
    )
    publish(client, organizer, "cup")


def enroll(client, auth_headers, name, email=None):
    email = email or (name.lower().replace(" ", ".").replace("ě", "e") + "@example.com")
    fencer = auth_headers(email=email, name=name)
    response = client.post(
        "/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=fencer
    )
    assert response.status_code == 201, response.text
    return fencer, response.json()["vs"]


def upload(client, organizer, rows):
    response = client.post(
        "/api/tournaments/cup/payments/import-statement",
        files={"file": ("s.csv", io.BytesIO(statement(rows)), "text/csv")},
        headers=organizer,
    )
    assert response.status_code == 202, response.text
    return response.json()


def transactions():
    return db_session().scalars(select(BankTransaction).order_by(BankTransaction.id)).all()


def registration_by_vs(vs):
    return db_session().scalar(select(Registration).where(Registration.vs == vs))


# ------------------------------------------------ a proposal moves nothing


def test_a_proposal_credits_nothing_and_mails_nobody(client, auth_headers, mailbox, parser):
    organizer = auth_headers()
    setup(client, organizer)
    _, vs = enroll(client, auth_headers, "Josef Vejda")
    before = registration_by_vs(vs)
    state, paid, owed = before.state, before.credited_in("local"), before.outstanding_cents
    mailbox.sent.clear()

    upload(
        client,
        organizer,
        [
            {
                "ref": "1",
                "date": "2026-08-01",
                "amount": "1000",
                "note": "Vejda Josef",
                "named": "Vejda Josef",
            },
        ],
    )

    after = registration_by_vs(vs)
    # asserted on the money, not on the status string — the status is the one
    # thing a broken implementation would get right
    assert after.state == state
    assert after.credited_in("local") == paid
    assert after.outstanding_cents == owed
    assert mailbox.sent == []

    (transaction,) = transactions()
    assert transaction.status == "likely"
    assert transaction.proposed_fencer.display_name == "Josef Vejda"


# ------------------------------------------------------- the ambiguity rules


def test_a_shared_surname_proposes_nobody(client, auth_headers, mailbox, parser):
    organizer = auth_headers()
    setup(client, organizer)
    enroll(client, auth_headers, "Jindřich Pekárek")
    enroll(client, auth_headers, "Ondřej Pekárek")

    upload(
        client,
        organizer,
        [
            {"ref": "1", "date": "2026-08-01", "amount": "1000", "named": "Pekárek"},
        ],
    )
    (transaction,) = transactions()
    assert transaction.status == "unmatched"
    assert transaction.proposed_fencer_id is None


def test_a_name_nobody_here_carries_proposes_nobody(client, auth_headers, mailbox, parser):
    organizer = auth_headers()
    setup(client, organizer)
    enroll(client, auth_headers, "Josef Vejda")

    upload(
        client,
        organizer,
        [
            {"ref": "1", "date": "2026-08-01", "amount": "1000", "named": "Zdeněk Kroupa"},
        ],
    )
    (transaction,) = transactions()
    assert transaction.status == "unmatched"
    assert transaction.status_reason == "no_name_match"


def test_the_payer_name_alone_is_never_proposed(client, auth_headers, mailbox, parser):
    """Who paid is not who the payment is for. A row whose only text is the
    payer's own name is ranked so the dialog has something to show, and is
    never an answer (design Decision 2)."""
    organizer = auth_headers()
    setup(client, organizer)
    enroll(client, auth_headers, "Milan Diviš")

    upload(
        client,
        organizer,
        [
            {"ref": "1", "date": "2026-08-01", "amount": "1000", "payer": "Milan Diviš"},
        ],
    )
    (transaction,) = transactions()
    assert transaction.status == "unmatched"
    assert transaction.status_reason == "payer_name_only"
    assert transaction.proposed_fencer_id is None


# -------------------------------------------------------- the pilot's shape


def test_one_payer_paying_for_three_resolves_to_three_fencers(
    client, auth_headers, mailbox, parser
):
    """The failure the whole design turns on. Milan Diviš pays for three people
    in the pilot's statement; scoring his name alongside the message put *him*
    first on all three."""
    organizer = auth_headers()
    setup(client, organizer)
    enroll(client, auth_headers, "Milan Diviš")
    enroll(client, auth_headers, "Jindřich Pekárek")
    enroll(client, auth_headers, "Josef Vochozka")
    enroll(client, auth_headers, "Matěj Mazanec")

    upload(
        client,
        organizer,
        [
            {
                "ref": "1",
                "date": "2026-08-01",
                "amount": "1000",
                "payer": "Milan Diviš",
                "note": "NaDuel26: Jindřich Pekárek- SB",
                "named": "Jindřich Pekárek",
            },
            {
                "ref": "2",
                "date": "2026-08-01",
                "amount": "1000",
                "payer": "Milan Diviš",
                "note": "NaDuel26: Josef Vochozka - sabre",
                "named": "Josef Vochozka",
            },
            {
                "ref": "3",
                "date": "2026-08-01",
                "amount": "1000",
                "payer": "Milan Diviš",
                "note": "NaDuel26: Matěj Mazanec",
                "named": "Matěj Mazanec",
            },
        ],
    )

    proposed = [t.proposed_fencer.display_name for t in transactions()]
    assert proposed == ["Jindřich Pekárek", "Josef Vochozka", "Matěj Mazanec"]
    assert "Milan Diviš" not in proposed


def test_the_message_resolves_where_the_model_named_nobody(client, auth_headers, mailbox, parser):
    """With no model configured the message itself is the query, and that is
    what resolved 35 of the pilot's 43."""
    organizer = auth_headers()
    setup(client, organizer)
    enroll(client, auth_headers, "Josef Vejda")

    upload(
        client,
        organizer,
        [
            {
                "ref": "1",
                "date": "2026-08-01",
                "amount": "1000",
                "note": "NaDuel26: Josef Vejda - sabre",
            },
        ],
    )
    (transaction,) = transactions()
    assert transaction.status == "likely"
    assert transaction.proposed_fencer.display_name == "Josef Vejda"


# ------------------------------------------------ a symbol still short-cuts


def test_a_quoted_symbol_never_reaches_the_resolver(client, auth_headers, mailbox, parser):
    """Nothing before the no-symbol branch changes: a payment quoting a symbol
    is credited as it always was, whatever its message says."""
    organizer = auth_headers()
    setup(client, organizer)
    _, vs = enroll(client, auth_headers, "Josef Vejda")
    enroll(client, auth_headers, "Milan Diviš")

    upload(
        client,
        organizer,
        [
            {
                "ref": "1",
                "date": "2026-08-01",
                "amount": "1000",
                "vs": str(vs),
                "note": "Milan Diviš",
                "named": "Milan Diviš",
            },
        ],
    )
    (transaction,) = transactions()
    assert transaction.status == "matched"
    assert registration_by_vs(vs).settled


# ------------------------------------------------------ confirm and reject


def confirm(client, organizer, transaction_id):
    return client.post(
        f"/api/tournaments/cup/payments/likely/{transaction_id}/confirm", headers=organizer
    )


def reject(client, organizer, transaction_id):
    return client.post(
        f"/api/tournaments/cup/payments/likely/{transaction_id}/reject", headers=organizer
    )


def test_confirming_credits_exactly_as_a_quoted_symbol_would(client, auth_headers, mailbox, parser):
    """Confirming is the organizer supplying the symbol the payer omitted, so
    it goes through the manual-link path and the outcome is indistinguishable
    from a payment that quoted one (design Decision 5)."""
    organizer = auth_headers()
    setup(client, organizer)
    fencer, vs = enroll(client, auth_headers, "Josef Vejda")

    upload(
        client,
        organizer,
        [
            {"ref": "1", "date": "2026-08-01", "amount": "1000", "named": "Josef Vejda"},
        ],
    )
    mailbox.sent.clear()
    (transaction,) = transactions()
    assert confirm(client, organizer, transaction.id).status_code == 201

    after = registration_by_vs(vs)
    assert after.settled
    assert after.credited_in("local") == 100000
    assert after.outstanding_cents == 0
    # and it sends what a credit sends
    assert any("Platba" in message["Subject"] for message in mailbox.sent)


def test_a_confirmed_proposal_is_an_ordinary_payment_link(client, auth_headers, mailbox, parser):
    organizer = auth_headers()
    setup(client, organizer)
    _, vs = enroll(client, auth_headers, "Josef Vejda")
    upload(
        client,
        organizer,
        [
            {"ref": "1", "date": "2026-08-01", "amount": "1000", "named": "Josef Vejda"},
        ],
    )
    confirm(client, organizer, transactions()[0].id)

    listed = client.get("/api/tournaments/cup/rules?phase=payments", headers=organizer).json()
    assert [r["kind"] for r in listed] == ["payment_link"]
    # addressed by registration, because the proposal named a person
    assert listed[0]["payload"]["registration_ids"]


def test_rejecting_returns_it_and_does_not_propose_again(client, auth_headers, mailbox, parser):
    organizer = auth_headers()
    setup(client, organizer)
    _, vs = enroll(client, auth_headers, "Josef Vejda")
    upload(
        client,
        organizer,
        [
            {"ref": "1", "date": "2026-08-01", "amount": "1000", "named": "Josef Vejda"},
        ],
    )
    transaction_id = transactions()[0].id

    response = reject(client, organizer, transaction_id)
    assert response.status_code == 200
    assert response.json()["status"] == "unmatched"

    after = transactions()[0]
    assert after.proposed_fencer_id is None
    assert after.status_reason == "proposal_rejected"
    # nothing was credited on the way through
    assert registration_by_vs(vs).credited_in("local") == 0

    # and the same reading is not offered a second time
    client.post("/api/tournaments/cup/payments/process", headers=organizer)
    assert transactions()[0].status == "unmatched"


def test_a_rejected_transaction_cannot_be_confirmed(client, auth_headers, mailbox, parser):
    organizer = auth_headers()
    setup(client, organizer)
    enroll(client, auth_headers, "Josef Vejda")
    upload(
        client,
        organizer,
        [
            {"ref": "1", "date": "2026-08-01", "amount": "1000", "named": "Josef Vejda"},
        ],
    )
    transaction_id = transactions()[0].id
    reject(client, organizer, transaction_id)
    assert confirm(client, organizer, transaction_id).status_code == 409


def test_both_actions_refuse_without_console_access(client, auth_headers, mailbox, parser):
    organizer = auth_headers()
    setup(client, organizer)
    enroll(client, auth_headers, "Josef Vejda")
    upload(
        client,
        organizer,
        [
            {"ref": "1", "date": "2026-08-01", "amount": "1000", "named": "Josef Vejda"},
        ],
    )
    transaction_id = transactions()[0].id
    outsider = auth_headers(email="nobody@example.com", name="Nobody")
    assert confirm(client, outsider, transaction_id).status_code == 403
    assert reject(client, outsider, transaction_id).status_code == 403


def test_the_queue_lists_only_proposals(client, auth_headers, mailbox, parser):
    organizer = auth_headers()
    setup(client, organizer)
    enroll(client, auth_headers, "Josef Vejda")
    upload(
        client,
        organizer,
        [
            {"ref": "1", "date": "2026-08-01", "amount": "1000", "named": "Josef Vejda"},
            {"ref": "2", "date": "2026-08-01", "amount": "500", "named": "Nobody Here"},
        ],
    )
    queue = client.get("/api/tournaments/cup/payments/likely", headers=organizer).json()
    assert [t["external_id"] for t in queue] == ["1"]
    assert queue[0]["proposed_fencer_name"] == "Josef Vejda"


# ------------------------------------------------------- the ranked roster


def test_the_roster_comes_back_whole_and_ordered(client, auth_headers, mailbox, parser):
    organizer = auth_headers()
    setup(client, organizer)
    enroll(client, auth_headers, "Josef Vejda")
    enroll(client, auth_headers, "Milan Diviš")
    enroll(client, auth_headers, "Matěj Mazanec")
    upload(
        client,
        organizer,
        [
            {"ref": "1", "date": "2026-08-01", "amount": "1000", "named": "Josef Vejda"},
        ],
    )
    transaction_id = transactions()[0].id

    body = client.get(
        f"/api/tournaments/cup/payments/transactions/{transaction_id}/roster",
        headers=organizer,
    ).json()
    assert body["query"] == "Josef Vejda"
    # every fencer, ordered, with exactly one marked as the proposal
    assert len(body["fencers"]) == 3
    assert [f["name"] for f in body["fencers"]][0] == "Josef Vejda"
    assert [f["score"] for f in body["fencers"]] == sorted(
        (f["score"] for f in body["fencers"]), reverse=True
    )
    assert sum(1 for f in body["fencers"] if f["proposed"]) == 1
    assert all(f["registration_id"] for f in body["fencers"])


def test_a_refused_fencer_is_marked_in_the_roster(client, auth_headers, mailbox, parser):
    organizer = auth_headers()
    setup(client, organizer)
    enroll(client, auth_headers, "Josef Vejda")
    upload(
        client,
        organizer,
        [
            {"ref": "1", "date": "2026-08-01", "amount": "1000", "named": "Josef Vejda"},
        ],
    )
    transaction_id = transactions()[0].id
    reject(client, organizer, transaction_id)

    body = client.get(
        f"/api/tournaments/cup/payments/transactions/{transaction_id}/roster",
        headers=organizer,
    ).json()
    vejda = next(f for f in body["fencers"] if f["name"] == "Josef Vejda")
    assert vejda["rejected"] is True
    assert vejda["proposed"] is False
