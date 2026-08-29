"""Fencers entered by hand: the third source population, and the strict
validation that guards the way in (spec etl-console, Manual entry of a fencer)."""

import io

from app.dedup import MergeProposal, ThreeBands, default_merge, get_dedup_llm
from app.importer import ParsedFencer, get_import_parser
from app.main import app
from tests.conftest import publish, set_features

ENTRY = {"name": "Hand Entered", "disciplines": ["LS"], "nationality": "CZ"}


class NameParser:
    def parse(self, rows, disciplines, rentals):
        return [
            ParsedFencer(
                registration_time=raw.get("When") or "2026-05-01T10:00:00",
                name=raw["Name"],
                nationality="CZ",
                club=raw.get("Club"),
                hr_id=int(raw["HR"]) if raw.get("HR", "").strip().isdigit() else None,
                disciplines=["LS"],
            )
            for raw in rows
        ]


def setup(client, organizer, *, team=False, rental=False):
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
    if team:
        set_features(client, organizer, "cup", feature_teams=True)
        client.post(
            "/api/tournaments/cup/disciplines",
            json={
                "slug": "TEAM",
                "weapon": "LS",
                "kind": "team",
                "team_min": 2,
                "team_max": 3,
                "capacity": 4,
                "fee": 2000,
            },
            headers=organizer,
        )
    if rental:
        set_features(client, organizer, "cup", feature_extras=True)
        client.post(
            "/api/tournaments/cup/extra-items",
            json={"name": "longsword", "category": "rental", "price": 100},
            headers=organizer,
        )
    publish(client, organizer, "cup")
    app.dependency_overrides[get_import_parser] = lambda: NameParser()


def enter(client, organizer, **fields):
    return client.post(
        "/api/tournaments/cup/manual-rows", json={**ENTRY, **fields}, headers=organizer
    )


def sheet_rows(client, organizer):
    return client.get("/api/tournaments/cup/sheet", headers=organizer).json()["rows"]


def upload(client, organizer, content, filename="regs.csv"):
    return client.post(
        "/api/tournaments/cup/import",
        files={"file": (filename, io.BytesIO(content.encode()), "text/csv")},
        headers=organizer,
    )


def test_manual_row_joins_the_fencer_list(client, auth_headers):
    """3.3 / 4.3 — the row is listed, with its selections resolved."""
    organizer = auth_headers()
    setup(client, organizer, rental=True)

    response = enter(
        client,
        organizer,
        club="Twerchhau",
        weapon_rentals=["longsword"],
        afterparty=True,
        notes="paid at the door",
    )
    assert response.status_code == 201, response.text

    rows = sheet_rows(client, organizer)
    assert len(rows) == 1
    row = rows[0]
    assert row["id"].startswith("man:")
    assert row["name"] == "Hand Entered"
    assert row["club"] == "Twerchhau"
    assert row["disciplines"] == ["LS"]
    assert row["weapon_rentals"] == ["longsword"]
    assert row["afterparty"] is True
    assert row["notes"] == "paid at the door"
    assert row["state"] == "manual"
    assert row["match_verdict"] == "unknown"
    assert row["vs"] is None


def test_manual_row_with_an_hr_id_enters_matched(client, auth_headers):
    """3.3 — an organizer-supplied id is a confirmed identity."""
    organizer = auth_headers()
    setup(client, organizer)

    enter(client, organizer, hr_id=1234)

    assert sheet_rows(client, organizer)[0]["match_verdict"] == "confirmed"


def test_manual_row_takes_the_next_number_and_keeps_it(client, auth_headers):
    """3.2 — allocated at entry, unmoved by a later import."""
    organizer = auth_headers()
    setup(client, organizer)
    enter(client, organizer)
    number = sheet_rows(client, organizer)[0]["number"]
    assert number == 1

    upload(client, organizer, "Name,When,HR\nLater Import,2026-01-01T09:00:00,\n")

    rows = {row["id"].split(":")[0]: row for row in sheet_rows(client, organizer)}
    assert rows["man"]["number"] == number
    assert rows["imp"]["number"] == 2


def test_backdated_manual_entry_interleaves(client, auth_headers):
    """3.6 — sorted by the moment it states, not by when it was typed."""
    organizer = auth_headers()
    setup(client, organizer)
    upload(
        client,
        organizer,
        "Name,When,HR\nEarly Import,2026-01-01T09:00:00,\nLate Import,2026-06-01T09:00:00,\n",
    )

    enter(client, organizer, registered_at="2026-03-01T12:00:00")

    assert [row["name"] for row in sheet_rows(client, organizer)] == [
        "Early Import",
        "Hand Entered",
        "Late Import",
    ]


def test_manual_row_never_appears_among_the_imported_rows(client, auth_headers):
    """3.7 — the Import view records a file, and nobody typed a file."""
    organizer = auth_headers()
    setup(client, organizer)
    upload(client, organizer, "Name,When,HR\nAnna Import,2026-01-01T09:00:00,\n")
    enter(client, organizer)

    imported = [row for row in sheet_rows(client, organizer) if row["id"].startswith("imp:")]
    assert [row["name"] for row in imported] == ["Anna Import"]
    assert all(row.get("_source") is None for row in sheet_rows(client, organizer)
               if row["id"].startswith("man:"))


class FakeDedupLLM:
    def propose_merge(self, records, language):
        return MergeProposal(fields=default_merge(records), note="records merged")

    def classify(self, records):
        return ThreeBands(surely=[], likely=[], possible=[])


def test_manual_row_reaches_deduplication(client, auth_headers):
    """3.8 — it shares an hr_id with an imported row and the pair is queued."""
    organizer = auth_headers()
    setup(client, organizer)
    upload(client, organizer, "Name,When,HR\nHand Entered,2026-01-01T09:00:00,1234\n")
    enter(client, organizer, hr_id=1234)
    app.dependency_overrides[get_dedup_llm] = lambda: FakeDedupLLM()

    assert client.post("/api/tournaments/cup/import/dedup", headers=organizer).json()[
        "proposals"
    ] == 1

    queue = client.get("/api/tournaments/cup/import/dedup/queue", headers=organizer).json()
    ids = {row["id"] for item in queue for row in item["rows"]}
    assert any(row_id.startswith("man:") for row_id in ids)
    assert any(row_id.startswith("imp:") for row_id in ids)


def test_manual_row_is_editable_and_deletable_like_any_other(client, auth_headers):
    """Spec: Manual row is editable afterwards."""
    organizer = auth_headers()
    setup(client, organizer)
    enter(client, organizer)
    row_id = sheet_rows(client, organizer)[0]["id"]

    response = client.post(
        "/api/tournaments/cup/rules",
        json={
            "phase": "fencers",
            "kind": "field_edit",
            "target": row_id,
            "payload": {"field": "club", "value": "Mordschlag"},
        },
        headers=organizer,
    )
    assert response.status_code == 201, response.text

    sheet = client.get("/api/tournaments/cup/sheet", headers=organizer).json()
    assert sheet["rows"][0]["club"] == "Mordschlag"
    assert [edit["phase"] for edit in sheet["edits"]] == ["fencers"]


def test_blank_name_is_refused(client, auth_headers):
    """4.1 / 4.4 — refused whole, and no row is added."""
    organizer = auth_headers()
    setup(client, organizer)

    assert enter(client, organizer, name="   ").status_code == 422
    assert sheet_rows(client, organizer) == []


def test_a_discipline_is_required(client, auth_headers):
    """4.4 — a row that enters nobody into anything is refused."""
    organizer = auth_headers()
    setup(client, organizer)

    response = enter(client, organizer, disciplines=[])
    assert response.status_code == 422
    assert response.json()["detail"] == "no_disciplines"
    assert sheet_rows(client, organizer) == []


def test_unknown_discipline_is_refused(client, auth_headers):
    """4.2 — only what the tournament offers."""
    organizer = auth_headers()
    setup(client, organizer)

    response = enter(client, organizer, disciplines=["SA"])
    assert response.status_code == 422
    assert response.json()["detail"] == {"unknown_disciplines": ["SA"]}


def test_team_discipline_is_refused(client, auth_headers):
    """4.2 — a team is entered through the tournament's team handling."""
    organizer = auth_headers()
    setup(client, organizer, team=True)

    response = enter(client, organizer, disciplines=["TEAM"])
    assert response.status_code == 422
    assert response.json()["detail"] == {"team_discipline_not_individual": ["TEAM"]}


def test_unlent_item_is_refused(client, auth_headers):
    """4.2 — an item to borrow is one the tournament lends."""
    organizer = auth_headers()
    setup(client, organizer, rental=True)

    response = enter(client, organizer, weapon_rentals=["halberd"])
    assert response.status_code == 422
    assert response.json()["detail"] == {"unknown_rentals": ["halberd"]}


def test_non_numeric_hr_id_is_refused(client, auth_headers):
    """4.1 — a profile URL is not a whole number."""
    organizer = auth_headers()
    setup(client, organizer)

    assert enter(client, organizer, hr_id="hemaratings.com/f/4321").status_code == 422
    assert sheet_rows(client, organizer) == []


def test_malformed_email_is_refused(client, auth_headers):
    """4.1 — an e-mail has the shape of an e-mail address."""
    organizer = auth_headers()
    setup(client, organizer)

    assert enter(client, organizer, email="not-an-address").status_code == 422


def test_empty_optionals_are_recorded_as_absent(client, auth_headers):
    """4.1 — an empty club is no club, not an empty one."""
    organizer = auth_headers()
    setup(client, organizer)

    enter(client, organizer, club="", notes="", nationality="")

    row = sheet_rows(client, organizer)[0]
    assert row["club"] is None
    assert row["notes"] is None
    assert row["nationality"] is None


def test_duplicate_is_allowed_through(client, auth_headers):
    """4.5 — duplicates are deduplication's business, not the dialog's."""
    organizer = auth_headers()
    setup(client, organizer)
    enter(client, organizer, hr_id=1234)

    assert enter(client, organizer, hr_id=1234).status_code == 201
    assert len(sheet_rows(client, organizer)) == 2


def test_manual_entry_requires_console_access(client, auth_headers):
    """4.3 — the console's own action, behind the console's own gate."""
    organizer = auth_headers()
    setup(client, organizer)
    outsider = auth_headers(email="outsider@example.com", name="Outsider")

    assert enter(client, outsider).status_code in (403, 404)
    assert sheet_rows(client, organizer) == []


def test_tournament_with_manual_rows_can_still_be_deleted(client, auth_headers):
    """An empty tournament is hard-deletable, and a hand-entered row is a child
    row like any other — it must go with it rather than block the delete."""
    organizer = auth_headers()
    setup(client, organizer)
    enter(client, organizer)

    deleted = client.delete("/api/tournaments/cup", headers=organizer)

    assert deleted.status_code == 204, deleted.text
    assert client.get("/api/tournaments/cup", headers=organizer).status_code == 404
