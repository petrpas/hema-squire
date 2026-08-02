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


def enroll(client, auth_headers, email, name):
    fencer = auth_headers(email=email, name=name)
    response = client.post(
        "/api/tournaments/cup/register", json={"disciplines": ["LS"]}, headers=fencer
    )
    assert response.status_code == 201
    return fencer


def add_rule(client, organizer, target, field, value, phase="parsing", kind="field_edit"):
    response = client.post(
        "/api/tournaments/cup/rules",
        json={"phase": phase, "kind": kind, "target": target,
              "payload": {"field": field, "value": value}},
        headers=organizer,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def get_sheet(client, organizer):
    return client.get("/api/tournaments/cup/sheet", headers=organizer).json()


def row_by_id(sheet, target):
    return next(r for r in sheet["rows"] if r["id"] == target)


def test_field_edit_applies_and_survives_rerun(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)
    enroll(client, auth_headers, "a@example.com", "Jan Novak")

    add_rule(client, organizer, "reg:1", "name", "Jan Novák")
    first = get_sheet(client, organizer)
    assert row_by_id(first, "reg:1")["name"] == "Jan Novák"

    # deterministic replay: a second computation is identical
    assert get_sheet(client, organizer) == first


def test_latest_wins_and_removal_exposes_earlier(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)
    enroll(client, auth_headers, "a@example.com", "Jan Novak")

    add_rule(client, organizer, "reg:1", "name", "Jan Novák")
    second_id = add_rule(client, organizer, "reg:1", "name", "Honza Novák")
    assert row_by_id(get_sheet(client, organizer), "reg:1")["name"] == "Honza Novák"

    delete = client.delete(f"/api/tournaments/cup/rules/{second_id}", headers=organizer)
    assert delete.status_code == 204
    assert row_by_id(get_sheet(client, organizer), "reg:1")["name"] == "Jan Novák"


def test_row_delete_and_restore(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)
    enroll(client, auth_headers, "a@example.com", "Jan")
    enroll(client, auth_headers, "b@example.com", "Petra")

    add_rule(client, organizer, "reg:2", "", "", kind="row_delete")
    sheet = get_sheet(client, organizer)
    assert {r["id"]: r["_deleted"] for r in sheet["rows"]} == {
        "reg:1": False,
        "reg:2": True,
    }

    add_rule(client, organizer, "reg:2", "", "", kind="row_restore")
    sheet = get_sheet(client, organizer)
    assert all(not r["_deleted"] for r in sheet["rows"])


def test_audit_shows_actor_and_before_after(client, auth_headers):
    organizer = auth_headers(email="boss@example.com", name="Šéf")
    setup(client, organizer)
    enroll(client, auth_headers, "a@example.com", "Jan Novak")

    rule_id = add_rule(client, organizer, "reg:1", "club", "SK Praha")
    edits = get_sheet(client, organizer)["edits"]
    assert len(edits) == 1
    entry = edits[0]
    assert entry["rule_id"] == rule_id
    assert entry["field"] == "club"
    assert entry["before"] is None
    assert entry["after"] == "SK Praha"
    assert entry["actor"] == "Šéf"

    # audit lives only as long as its causing rule
    client.delete(f"/api/tournaments/cup/rules/{rule_id}", headers=organizer)
    assert get_sheet(client, organizer)["edits"] == []


def test_rule_edit_changes_replay_and_is_journaled(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)
    enroll(client, auth_headers, "a@example.com", "Jan")

    rule_id = add_rule(client, organizer, "reg:1", "nationality", "CZE")
    patched = client.patch(
        f"/api/tournaments/cup/rules/{rule_id}",
        json={"payload": {"field": "nationality", "value": "SVK"}},
        headers=organizer,
    )
    assert patched.status_code == 200
    assert row_by_id(get_sheet(client, organizer), "reg:1")["nationality"] == "SVK"

    journal = client.get("/api/tournaments/cup/rules/journal", headers=organizer).json()
    assert [e["action"] for e in journal] == ["created", "updated"]


def test_meta_journal_survives_rule_deletion(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)
    enroll(client, auth_headers, "a@example.com", "Jan")

    rule_id = add_rule(client, organizer, "reg:1", "name", "Oprava")
    client.delete(f"/api/tournaments/cup/rules/{rule_id}", headers=organizer)

    # data-side: as if the rule never existed
    assert client.get("/api/tournaments/cup/rules", headers=organizer).json() == []
    assert row_by_id(get_sheet(client, organizer), "reg:1")["name"] == "Jan"

    # journal-side: full lifecycle retained, including rule content
    journal = client.get("/api/tournaments/cup/rules/journal", headers=organizer).json()
    assert [e["action"] for e in journal] == ["created", "deleted"]
    assert journal[1]["content"]["payload"] == {"field": "name", "value": "Oprava"}


def test_rules_are_listable_per_phase(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)
    enroll(client, auth_headers, "a@example.com", "Jan")

    add_rule(client, organizer, "reg:1", "name", "A", phase="parsing")
    add_rule(client, organizer, "reg:1", "club", "B", phase="matching")

    parsing = client.get(
        "/api/tournaments/cup/rules", params={"phase": "parsing"}, headers=organizer
    ).json()
    assert [r["phase"] for r in parsing] == ["parsing"]


def test_validation_and_authorization(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)
    outsider = auth_headers(email="x@example.com", name="X")

    bad_kind = client.post(
        "/api/tournaments/cup/rules",
        json={"phase": "parsing", "kind": "nonsense", "target": "reg:1", "payload": {}},
        headers=organizer,
    )
    assert bad_kind.status_code == 422

    bad_payload = client.post(
        "/api/tournaments/cup/rules",
        json={"phase": "parsing", "kind": "field_edit", "target": "reg:1", "payload": {}},
        headers=organizer,
    )
    assert bad_payload.status_code == 422

    denied = client.post(
        "/api/tournaments/cup/rules",
        json={"phase": "parsing", "kind": "field_edit", "target": "reg:1",
              "payload": {"field": "name", "value": "x"}},
        headers=outsider,
    )
    assert denied.status_code == 403
