"""A draft holds no participants and no money (spec tournament-publication, A
tournament is a draft until it is published).

Every write of a tournament's data is refused until publication, and the export
is refused with them because its product leaves the console (spec data-export).
The refusal is 409 naming publication rather than 404: what reaches these
routes on a draft is a retry, a tab left open, or a script, and each should
learn why (design D5).

The reads are deliberately absent from the table below. They stay open, and
they answer with nothing — which is the rule working rather than a gap in it.
"""

import io

import pytest
from sqlalchemy import select

from app.db import get_session
from app.main import app
from app.models import (
    ImportedRow,
    ManualPayment,
    ManualRow,
    Registration,
    Rule,
    Tournament,
)
from tests.conftest import publish


def db_session():
    return next(app.dependency_overrides[get_session]())


def setup_draft(client, organizer, slug="cup"):
    """Setup-complete and unpublished: nothing but the publication record
    stands between this tournament and its data work."""
    client.post(
        "/api/tournaments",
        json={"slug": slug, "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    client.patch(
        f"/api/tournaments/{slug}",
        json={
            "city": "Brno",
            "organizers": [{"name": "Cup Org", "link": None}],
            "bank_account": "CZ6508000000192000145399",
        },
        headers=organizer,
    )
    client.post(
        f"/api/tournaments/{slug}/disciplines",
        json={"slug": "SA", "weapon": "SA", "capacity": 20, "fee": 800},
        headers=organizer,
    )
    tournament = db_session().scalar(select(Tournament).where(Tournament.slug == slug))
    assert tournament.published_at is None
    return tournament


CSV = b"name,email\nJan Novak,jan@example.com\n"


def a_file():
    return {"file": ("regs.csv", io.BytesIO(CSV), "text/csv")}


# (label, method, path, body-or-files). Every gated route, so a route added to
# the gate without a line here is a route this file does not speak for.
GATED = [
    ("roster upload", "post", "/import", {"files": a_file()}),
    ("import clear", "delete", "/import", {}),
    ("hr matching", "post", "/import/match", {}),
    ("deduplication", "post", "/import/dedup", {}),
    ("dedup verdict", "post", "/import/dedup/decide", {"json": {"key": "k", "accept": True}}),
    ("issuing", "post", "/import/issue", {}),
    ("ratings snapshot", "post", "/ratings/snapshot", {}),
    ("statement import", "post", "/payments/import-statement", {"files": a_file()}),
    ("bank poll", "post", "/payments/fio-poll", {}),
    ("lifecycle process", "post", "/payments/process", {}),
    (
        "transaction link",
        "post",
        "/payments/link",
        {"json": {"transaction_id": 1, "registration_ids": [1]}},
    ),
    ("likely confirm", "post", "/payments/likely/1/confirm", {}),
    ("likely reject", "post", "/payments/likely/1/reject", {}),
    ("resettle", "post", "/payments/resettle", {}),
    ("payments clear", "delete", "/payments", {}),
    ("reinstate", "post", "/payments/transactions/1/reinstate", {}),
    ("mark for refund", "post", "/payments/transactions/1/mark-for-refund", {}),
    (
        "recorded payment",
        "post",
        "/payments/manual",
        {
            "json": {
                "registration_id": 1,
                "amount": "800.00",
                "currency": "CZK",
                "received_on": "2026-05-01",
                "method": "cash",
            }
        },
    ),
    ("recorded payment removal", "delete", "/payments/manual/1", {}),
    ("manual row", "post", "/manual-rows", {"json": {"name": "Jan Novák", "disciplines": ["SA"]}}),
    (
        "rule creation",
        "post",
        "/rules",
        {
            "json": {
                "phase": "fencers",
                "kind": "edit",
                "target": "imp:1",
                "payload": {"club": "Twerchhau"},
            }
        },
    ),
    ("rule edit", "patch", "/rules/1", {"json": {"payload": {"club": "Other"}}}),
    ("rule removal", "delete", "/rules/1", {}),
    ("settled mark", "post", "/registrations/1/settled", {}),
    ("substitute admission", "post", "/registrations/1/admit/SA", {}),
    ("return to queue", "post", "/registrations/1/return-to-queue/SA", {}),
    ("seating settlement", "post", "/settle-seating", {}),
    ("worksheet export", "post", "/export/sheet", {}),
    ("canonical document", "get", "/export/json", {}),
    ("export tab band", "get", "/export/tables", {}),
    ("one export table", "get", "/export/table", {"params": {"kind": "fencers", "key": ""}}),
]


@pytest.mark.parametrize("label,method,path,kwargs", GATED, ids=[case[0] for case in GATED])
def test_a_draft_refuses_it(client, auth_headers, label, method, path, kwargs):
    """The reason names publication, and it is reached before the route looks
    anything up: the ids below name nothing, and the answer is still the
    refusal rather than a not-found."""
    organizer = auth_headers()
    setup_draft(client, organizer)

    response = getattr(client, method)(f"/api/tournaments/cup{path}", headers=organizer, **kwargs)

    assert response.status_code == 409, f"{label}: {response.text}"
    assert response.json()["detail"] == {"code": "not_published"}


def test_a_draft_is_left_holding_nothing(client, auth_headers):
    """The other half of every refusal above, asserted once over the whole
    tournament rather than once per route: no row, no registration, no rule, no
    recorded payment."""
    organizer = auth_headers()
    setup_draft(client, organizer)
    for _label, method, path, kwargs in GATED:
        getattr(client, method)(f"/api/tournaments/cup{path}", headers=organizer, **kwargs)

    session = db_session()
    tournament = session.scalar(select(Tournament).where(Tournament.slug == "cup"))
    for model in (ImportedRow, ManualRow, Registration, Rule, ManualPayment):
        held = session.scalars(select(model).where(model.tournament_id == tournament.id)).all()
        assert held == [], f"{model.__name__} on a draft"


def test_publication_opens_the_data_work(client, auth_headers):
    """The refusal is about the draft and nothing else: the same upload, on the
    same tournament, runs the moment it is published."""
    organizer = auth_headers()
    setup_draft(client, organizer)
    refused = client.post("/api/tournaments/cup/import", headers=organizer, files=a_file())
    assert refused.status_code == 409

    publish(client, organizer, "cup")

    accepted = client.post("/api/tournaments/cup/import", headers=organizer, files=a_file())
    assert accepted.status_code == 202, accepted.text


def test_a_draft_still_reads(client, auth_headers):
    """Reachable means readable (spec tournament-publication). The console's
    tables, the operation records and the manual-edits journal all answer on a
    draft — with nothing, which is the rule rather than a gap in it."""
    organizer = auth_headers()
    setup_draft(client, organizer)

    for path in ("/sheet", "/import/status", "/rules", "/rules/journal", "/operations"):
        response = client.get(f"/api/tournaments/cup{path}", headers=organizer)
        assert response.status_code == 200, f"{path}: {response.text}"


def test_a_draft_that_already_holds_data_keeps_it(client, auth_headers):
    """The migration claim, asserted rather than assumed (proposal, Impact). A
    draft holding rows from before this rule keeps them and can still be read;
    what it loses is the ability to add to them, and publication gives that
    back."""
    organizer = auth_headers()
    setup_draft(client, organizer)
    publish(client, organizer, "cup")
    uploaded = client.post("/api/tournaments/cup/import", headers=organizer, files=a_file())
    assert uploaded.status_code == 202, uploaded.text

    # back to a draft, which no route can do — this is the state a deployment
    # would carry across the deploy, not one Squire can now reach
    session = db_session()
    tournament = session.scalar(select(Tournament).where(Tournament.slug == "cup"))
    tournament.published_at = None
    tournament.published_by_id = None
    session.commit()

    sheet = client.get("/api/tournaments/cup/sheet", headers=organizer)
    assert sheet.status_code == 200, sheet.text
    assert sheet.json()["rows"], "the rows it already held are still readable"

    assert client.post("/api/tournaments/cup/import/issue", headers=organizer).status_code == 409

    publish(client, organizer, "cup")
    assert client.get("/api/tournaments/cup/import/issue", headers=organizer).status_code == 200


def test_a_draft_carries_no_symbol_less_registration_into_automatic_mode(client, auth_headers):
    """The hole this change exists to close (spec imported-registrations,
    Issuing waits for publication).

    A manual tournament issues registrations with no variable symbol, correctly
    — it has told no payer a number to quote. A draft may still change its
    mode. So a draft that issued could publish as an automatic tournament whose
    matching resolves through symbols, holding registrations that have none.
    Removing the source rather than guarding the switch: the switch is
    legitimate on a draft, the participants are what do not belong there."""
    organizer = auth_headers()
    setup_draft(client, organizer)
    client.patch(
        "/api/tournaments/cup/registrations-kept-by",
        json={"registrations_kept_by": "organizer"},
        headers=organizer,
    )
    client.patch(
        "/api/tournaments/cup",
        json={"external_registration_url": "https://elsewhere.example/e"},
        headers=organizer,
    )

    assert (
        client.post("/api/tournaments/cup/import", headers=organizer, files=a_file()).status_code
        == 409
    )
    assert client.post("/api/tournaments/cup/import/issue", headers=organizer).status_code == 409

    # back to automatic while it is still a draft, which is its right, and then
    # published: there is nothing to carry over
    client.patch(
        "/api/tournaments/cup/registrations-kept-by",
        json={"registrations_kept_by": "squire"},
        headers=organizer,
    )
    publish(client, organizer, "cup")

    session = db_session()
    tournament = session.scalar(select(Tournament).where(Tournament.slug == "cup"))
    assert (
        session.scalars(
            select(Registration).where(Registration.tournament_id == tournament.id)
        ).all()
        == []
    )

    # and the import runs from here, taking the symbols the mode calls for
    uploaded = client.post("/api/tournaments/cup/import", headers=organizer, files=a_file())
    assert uploaded.status_code == 202, uploaded.text
