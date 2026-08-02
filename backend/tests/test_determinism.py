"""Task 6.1 — determinism validation of the replay architecture.

Design Decision 2: current state = replay(source records, ordered rule set,
params), a pure function. These tests pin the property at two levels:

- engine level: replay() is pure — no input mutation, identical outputs on
  repeated calls, and removing a rule yields exactly the state that a history
  without that rule would have produced ("as if it never existed");
- API level: a rich scenario (registrations, payments, imported rows, every
  sheet-visible rule kind) computes an identical sheet on every fetch, and
  rule delete + identical re-create converges back to the same row state.
"""

import copy
import io
from datetime import UTC, datetime

from app.importer import get_import_parser
from app.main import app
from app.rules import replay
from tests.conftest import publish
from tests.test_import import CSV, FakeParser


class StubRule:
    """Minimal stand-in for the Rule ORM object (replay only reads attrs)."""

    _seq = 0

    def __init__(self, kind, target, payload, phase="parsing"):
        StubRule._seq += 1
        self.id = StubRule._seq
        self.phase = phase
        self.kind = kind
        self.target = target
        self.payload = payload
        self.created_at = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
        self.author = type("A", (), {"display_name": "Org"})()


def make_base():
    return {
        "reg:1": {"id": "reg:1", "name": "Jan Novak", "club": "Praha", "hr_id": None,
                  "disciplines": ["LS"], "notes": None, "_deleted": False},
        "imp:aa": {"id": "imp:aa", "name": "Jan Novák", "club": "Praha", "hr_id": None,
                   "disciplines": ["SA"], "notes": "dup", "_deleted": False},
        "imp:bb": {"id": "imp:bb", "name": "Marie Nová", "club": None, "hr_id": None,
                   "disciplines": ["SA"], "notes": None, "_deleted": False},
    }


def make_rules():
    return [
        StubRule("field_edit", "reg:1", {"field": "club", "value": "Praha HEMA"}),
        StubRule("match_resolution", "imp:bb", {"field": "hr_id", "value": 3340}),
        StubRule("row_delete", "imp:bb", {}),
        StubRule("row_restore", "imp:bb", {}),
        StubRule("dedup_decision", "reg:1",
                 {"absorb": ["imp:aa"], "fields": {"disciplines": ["LS", "SA"]},
                  "note": "merged"}),
        StubRule("field_edit", "reg:1", {"field": "club", "value": "Praha HEMA z.s."}),
    ]


def test_replay_is_pure_and_repeatable():
    base = make_base()
    rules = make_rules()
    snapshot = copy.deepcopy(base)

    first_rows, first_audit = replay(base, rules)
    second_rows, second_audit = replay(base, rules)

    assert base == snapshot  # inputs never mutated
    assert first_rows == second_rows
    assert first_audit == second_audit
    # the scenario actually exercised every handler
    assert first_rows["reg:1"]["club"] == "Praha HEMA z.s."  # latest wins
    assert first_rows["reg:1"]["disciplines"] == ["LS", "SA"]
    assert first_rows["imp:aa"]["_merged_into"] == "reg:1"
    assert first_rows["imp:bb"]["hr_id"] == 3340
    assert first_rows["imp:bb"]["_deleted"] is False  # delete then restore


def test_removed_rule_leaves_no_trace():
    """State after removal == state of a history that never had the rule,
    for every rule in the set — including merges and deletes."""
    base = make_base()
    rules = make_rules()
    for index in range(len(rules)):
        without = rules[:index] + rules[index + 1 :]
        rows_a, audit_a = replay(base, without)
        rows_b, audit_b = replay(base, without)
        assert rows_a == rows_b
        assert audit_a == audit_b
        # audit is a replay product: no entry from the removed rule survives
        removed_id = rules[index].id
        assert all(change.rule_id != removed_id for change in audit_a)


def test_rule_on_vanished_target_is_inert():
    base = make_base()
    rules = [StubRule("field_edit", "reg:404", {"field": "club", "value": "X"})]
    rows, audit = replay(base, rules)
    assert rows == make_base()
    assert audit == []


# --- API level: the whole pipeline recomputes identically -------------------


def build_scenario(client, auth_headers):
    organizer = auth_headers()
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
    for code in ("LS", "SA"):
        client.post(
            "/api/tournaments/cup/disciplines",
            json={"slug": code, "weapon": code, "capacity": 10, "fee": 1000},
            headers=organizer,
        )
    publish(client, organizer, "cup")
    fencer = auth_headers(email="jan@example.com", name="Jan Novak")
    vs = client.post(
        "/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=fencer
    ).json()["vs"]

    # payment through the statement path
    header = (
        "ID pohybu;Datum;Objem;Měna;VS;KS;SS;Zpráva pro příjemce;Název protiúčtu;Protiúčet"
    )
    statement = (
        f"meta;data\n\n{header}\n9001;14.07.2026;1 000,00;CZK;{vs};;;VS {vs};Jan;123/0800\n"
    ).encode()
    client.post(
        "/api/tournaments/cup/payments/import-statement",
        files={"file": ("v.csv", io.BytesIO(statement), "text/csv")},
        headers=organizer,
    )

    # imported table
    app.dependency_overrides[get_import_parser] = lambda: FakeParser()
    client.post(
        "/api/tournaments/cup/import",
        files={"file": ("regs.csv", io.BytesIO(CSV.encode()), "text/csv")},
        headers=organizer,
    )

    # one rule of each sheet-visible kind
    imported = [
        r["id"]
        for r in client.get("/api/tournaments/cup/sheet", headers=organizer).json()["rows"]
        if r["id"].startswith("imp:")
    ]
    for kind, target, payload in [
        ("field_edit", "reg:1", {"field": "club", "value": "Praha HEMA"}),
        ("match_resolution", imported[0], {"field": "hr_id", "value": 10234}),
        ("row_delete", imported[1], {}),
        ("dedup_decision", "reg:1",
         {"absorb": [imported[0]], "fields": {"notes": "merged demo"}, "note": "m"}),
    ]:
        response = client.post(
            "/api/tournaments/cup/rules",
            json={"phase": "parsing", "kind": kind, "target": target, "payload": payload},
            headers=organizer,
        )
        assert response.status_code == 201, response.text
    return organizer


def test_sheet_recomputes_identically_across_fetches(client, auth_headers):
    organizer = build_scenario(client, auth_headers)
    first = client.get("/api/tournaments/cup/sheet", headers=organizer).json()
    for _ in range(3):
        assert client.get("/api/tournaments/cup/sheet", headers=organizer).json() == first
    # the scenario is non-trivial: paid row, merge, delete, resolution all present
    states = {r["id"]: r for r in first["rows"]}
    assert states["reg:1"]["paid"] is True
    assert states["reg:1"]["notes"] == "merged demo"
    assert any(r.get("_merged_into") == "reg:1" for r in first["rows"])
    assert any(r["_deleted"] for r in first["rows"])


def test_delete_and_identical_recreate_converges(client, auth_headers):
    organizer = build_scenario(client, auth_headers)

    def row_states():
        sheet = client.get("/api/tournaments/cup/sheet", headers=organizer).json()
        return sorted(
            tuple(sorted((k, str(v)) for k, v in row.items())) for row in sheet["rows"]
        )

    before = row_states()
    rule = next(
        r
        for r in client.get("/api/tournaments/cup/rules", headers=organizer).json()
        if r["kind"] == "field_edit"
    )
    client.delete(f"/api/tournaments/cup/rules/{rule['id']}", headers=organizer)
    assert row_states() != before  # removal really reverts the effect

    client.post(
        "/api/tournaments/cup/rules",
        json={"phase": rule["phase"], "kind": rule["kind"], "target": rule["target"],
              "payload": rule["payload"]},
        headers=organizer,
    )
    assert row_states() == before  # identical inputs → identical state
