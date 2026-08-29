"""Clearing the tournament's imported content: total, hard and final
(spec table-import, Clearing the tournament's imported content)."""

import io

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import dedup, hr_match
from app.importer import ParsedFencer, get_import_parser
from app.main import app
from app.models import (
    ImportBatch,
    ImportDecision,
    ImportedRow,
    Rule,
    RuleJournalEntry,
    SheetRowNumber,
)
from tests.conftest import publish

CSV = "Name,Club\nAnna Import,Twerchhau\nBoris Import,Mordschlag\n"
OTHER_CSV = "Name,Club\nCyril Import,Fechtschule\n"


class NameParser:
    """The row as the file states it, so a test can name its own rows."""

    def parse(self, rows, disciplines, rentals):
        return [
            ParsedFencer(
                registration_time="2026-04-01T14:15:27",
                name=raw["Name"],
                nationality="CZ",
                club=raw["Club"],
                disciplines=["LS"],
            )
            for raw in rows
        ]


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
    app.dependency_overrides[get_import_parser] = lambda: NameParser()


def upload(client, organizer, content=CSV, filename="regs.csv"):
    return client.post(
        "/api/tournaments/cup/import",
        files={"file": (filename, io.BytesIO(content.encode()), "text/csv")},
        headers=organizer,
    )


def clear(client, organizer):
    return client.delete("/api/tournaments/cup/import", headers=organizer)


def sheet_rows(client, organizer):
    return client.get("/api/tournaments/cup/sheet", headers=organizer).json()["rows"]


def register(client, auth_headers, email="live@example.com", name="Live Registration"):
    fencer = auth_headers(email=email, name=name)
    response = client.post(
        "/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=fencer
    )
    assert response.status_code == 201, response.text
    return fencer


def test_clear_removes_every_trace_of_the_import(client, auth_headers, engine):
    """1.1 — every table the import wrote to is empty for the tournament."""
    organizer = auth_headers()
    setup(client, organizer)
    upload(client, organizer)
    rows = sheet_rows(client, organizer)
    client.post(
        "/api/tournaments/cup/rules",
        json={
            "phase": "import",
            "kind": "field_edit",
            "target": rows[0]["id"],
            "payload": {"field": "club", "value": "Corrected"},
        },
        headers=organizer,
    )

    assert clear(client, organizer).json() == {"rows": 2, "files": 1}

    with Session(engine) as session:
        assert session.scalars(select(ImportedRow)).all() == []
        assert session.scalars(select(ImportBatch)).all() == []
        assert session.scalars(select(ImportDecision)).all() == []
        assert session.scalars(select(Rule)).all() == []
        assert session.scalars(select(RuleJournalEntry)).all() == []
        assert session.scalars(select(SheetRowNumber)).all() == []
    assert sheet_rows(client, organizer) == []
    assert client.get("/api/tournaments/cup/import/status", headers=organizer).json() == {
        "batch": None,
        "total": {"rows": 0, "files": 0},
    }


def test_clear_requires_console_access(client, auth_headers):
    """1.2 — an account without console access is refused."""
    organizer = auth_headers()
    setup(client, organizer)
    upload(client, organizer)
    outsider = auth_headers(email="outsider@example.com", name="Outsider")

    assert clear(client, outsider).status_code in (403, 404)
    assert len(sheet_rows(client, organizer)) == 2


def test_clear_counts_what_it_removed(client, auth_headers):
    """1.2 — the counts the confirmation stated are what comes back."""
    organizer = auth_headers()
    setup(client, organizer)
    upload(client, organizer)
    upload(client, organizer, content=OTHER_CSV, filename="more.csv")

    assert clear(client, organizer).json() == {"rows": 3, "files": 2}


def test_clear_on_a_tournament_that_imported_nothing(client, auth_headers):
    """1.2 — nothing to clear is not an error."""
    organizer = auth_headers()
    setup(client, organizer)

    assert clear(client, organizer).json() == {"rows": 0, "files": 0}


def test_registrations_survive_a_clear(client, auth_headers, engine):
    """1.3 — content, number, rules and journal of a registration untouched."""
    organizer = auth_headers()
    setup(client, organizer)
    register(client, auth_headers)
    upload(client, organizer)
    registration = next(r for r in sheet_rows(client, organizer) if r["id"].startswith("reg:"))
    client.post(
        "/api/tournaments/cup/rules",
        json={
            "phase": "fencers",
            "kind": "field_edit",
            "target": registration["id"],
            "payload": {"field": "club", "value": "Twerchhau"},
        },
        headers=organizer,
    )

    clear(client, organizer)

    rows = sheet_rows(client, organizer)
    assert [row["id"] for row in rows] == [registration["id"]]
    assert rows[0]["number"] == registration["number"]
    assert rows[0]["club"] == "Twerchhau"
    with Session(engine) as session:
        assert len(session.scalars(select(Rule)).all()) == 1
        assert session.scalars(select(RuleJournalEntry)).all() != []


def test_every_batch_goes_not_only_the_latest(client, auth_headers):
    """1.4 — clearing does not fall back to an earlier upload."""
    organizer = auth_headers()
    setup(client, organizer)
    upload(client, organizer)
    upload(client, organizer, content=OTHER_CSV, filename="more.csv")
    upload(client, organizer, content="Name,Club\nDora Import,Halbschwert\n", filename="c.csv")

    clear(client, organizer)

    assert sheet_rows(client, organizer) == []
    assert client.get("/api/tournaments/cup/import/status", headers=organizer).json() == {
        "batch": None,
        "total": {"rows": 0, "files": 0},
    }


def test_every_decision_kind_is_removed(client, auth_headers, engine):
    """1.5 — parse, hr_match, merge, dedup and their siblings all go."""
    organizer = auth_headers()
    setup(client, organizer)
    upload(client, organizer)
    rows = sheet_rows(client, organizer)
    ids = [row["id"] for row in rows]
    with Session(engine) as session:
        from app.models import Tournament

        tournament = session.scalar(select(Tournament).where(Tournament.slug == "cup"))
        from app.importer import store_decision

        store_decision(
            session,
            tournament,
            "hr_match",
            hr_match.identity_key(rows[0]["name"], rows[0]["club"]),
            {"hr_id": 42},
        )
        store_decision(session, tournament, "merge", dedup.group_key(ids), {"rows": ids})
        store_decision(session, tournament, "dedup", dedup.group_key(ids), {"likely": []})
        store_decision(session, tournament, "dedup_seen", ids[0], {})
        store_decision(
            session, tournament, "dedup_resolution", dedup.group_key(ids), {"accepted": True}
        )
        session.commit()

    clear(client, organizer)

    with Session(engine) as session:
        assert session.scalars(select(ImportDecision)).all() == []


def test_merge_naming_a_cleared_row_goes_with_it(client, auth_headers, engine):
    """1.6 — the registration stands on its own, unmerged and listed."""
    organizer = auth_headers()
    setup(client, organizer)
    register(client, auth_headers)
    upload(client, organizer)
    rows = sheet_rows(client, organizer)
    registration = next(r for r in rows if r["id"].startswith("reg:"))
    imported = next(r for r in rows if r["id"].startswith("imp:"))
    response = client.post(
        "/api/tournaments/cup/rules",
        json={
            "phase": "dedup",
            "kind": "dedup_decision",
            "target": registration["id"],
            "payload": {
                "absorb": [imported["id"]],
                "fields": {"club": "Twerchhau"},
                "note": "same fencer",
            },
        },
        headers=organizer,
    )
    assert response.status_code == 201, response.text

    clear(client, organizer)

    rows = sheet_rows(client, organizer)
    assert [row["id"] for row in rows] == [registration["id"]]
    assert rows[0].get("merge_note") is None
    assert rows[0]["club"] != "Twerchhau"
    with Session(engine) as session:
        assert session.scalars(select(Rule)).all() == []


def test_re_import_after_a_clear_starts_clean(client, auth_headers):
    """1.7 — every row is parsed afresh, no decision or correction reused."""
    organizer = auth_headers()
    setup(client, organizer)
    upload(client, organizer)
    rows = sheet_rows(client, organizer)
    client.post(
        "/api/tournaments/cup/rules",
        json={
            "phase": "import",
            "kind": "field_edit",
            "target": rows[0]["id"],
            "payload": {"field": "name", "value": "Corrected Name"},
        },
        headers=organizer,
    )

    clear(client, organizer)
    result = upload(client, organizer).json()

    assert result["parsed"] == 2
    assert result["reused"] == 0
    assert sorted(row["name"] for row in sheet_rows(client, organizer)) == [
        "Anna Import",
        "Boris Import",
    ]
    assert client.get("/api/tournaments/cup/sheet", headers=organizer).json()["edits"] == []


def test_clearing_releases_the_cleared_numbers(client, auth_headers):
    """1.8 — the survivors keep theirs, the next row takes the next free one."""
    organizer = auth_headers()
    setup(client, organizer)
    register(client, auth_headers)
    upload(client, organizer)
    numbers = sorted(row["number"] for row in sheet_rows(client, organizer))
    assert numbers == [1, 2, 3]

    clear(client, organizer)
    assert [row["number"] for row in sheet_rows(client, organizer)] == [1]

    upload(client, organizer, content=OTHER_CSV, filename="more.csv")
    assert sorted(row["number"] for row in sheet_rows(client, organizer)) == [1, 2]
