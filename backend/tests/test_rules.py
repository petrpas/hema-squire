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
    assert entry["rule_ids"] == [rule_id]
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


def post_rule(client, organizer, kind, target, payload, phase="parsing"):
    response = client.post(
        "/api/tournaments/cup/rules",
        json={"phase": phase, "kind": kind, "target": target, "payload": payload},
        headers=organizer,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_edit_chain_reads_as_one_net_entry(client, auth_headers):
    """Two edits of a cell are one difference from the source, stated once."""
    organizer = auth_headers()
    setup(client, organizer)
    enroll(client, auth_headers, "a@example.com", "Jan Novak")

    first = add_rule(client, organizer, "reg:1", "name", "Jan Novák")
    second = add_rule(client, organizer, "reg:1", "name", "Honza Novák")

    edits = get_sheet(client, organizer)["edits"]
    assert len(edits) == 1
    assert edits[0]["before"] == "Jan Novak"
    assert edits[0]["after"] == "Honza Novák"
    assert edits[0]["rule_ids"] == [first, second]


def test_cancelling_operations_leave_no_entry(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)
    enroll(client, auth_headers, "a@example.com", "Jan")

    add_rule(client, organizer, "reg:1", "", "", kind="row_delete")
    add_rule(client, organizer, "reg:1", "", "", kind="row_restore")

    sheet = get_sheet(client, organizer)
    assert sheet["edits"] == []
    assert not row_by_id(sheet, "reg:1")["_deleted"]

    # the journal keeps what the log no longer shows
    journal = client.get("/api/tournaments/cup/rules/journal", headers=organizer).json()
    assert [e["action"] for e in journal] == ["created", "created"]
    assert [e["content"]["kind"] for e in journal] == ["row_delete", "row_restore"]


def test_repeated_operations_do_not_stack(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)
    enroll(client, auth_headers, "a@example.com", "Jan")

    add_rule(client, organizer, "reg:1", "", "", kind="row_delete")
    add_rule(client, organizer, "reg:1", "", "", kind="row_restore")
    third = add_rule(client, organizer, "reg:1", "", "", kind="row_delete")

    edits = get_sheet(client, organizer)["edits"]
    assert len(edits) == 1
    assert (edits[0]["field"], edits[0]["before"], edits[0]["after"]) == (
        "_deleted",
        False,
        True,
    )
    assert edits[0]["rule_ids"][-1] == third


def test_entry_sits_in_the_phase_of_its_newest_rule(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)
    enroll(client, auth_headers, "a@example.com", "Jan")

    add_rule(client, organizer, "reg:1", "club", "A", phase="parsing")
    add_rule(client, organizer, "reg:1", "club", "B", phase="matching")

    edits = get_sheet(client, organizer)["edits"]
    assert [e["phase"] for e in edits] == ["matching"]


def test_match_verdict_folds_into_its_hr_id_entry(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)
    enroll(client, auth_headers, "a@example.com", "Jan")

    add_rule(client, organizer, "reg:1", "hr_id", 4711, kind="match_resolution")
    edits = get_sheet(client, organizer)["edits"]
    assert [e["field"] for e in edits] == ["hr_id"]

    # resolved back to the source id, the verdict alone still stands
    add_rule(client, organizer, "reg:1", "hr_id", None, kind="match_resolution")
    edits = get_sheet(client, organizer)["edits"]
    assert [e["field"] for e in edits] == ["match_verdict"]
    assert edits[0]["after"] == "none_found"


def test_merge_reads_as_one_entry_per_absorbed_row(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)
    enroll(client, auth_headers, "a@example.com", "Jan Novak")
    enroll(client, auth_headers, "b@example.com", "Jan Novák")

    post_rule(
        client,
        organizer,
        "dedup_decision",
        "reg:1",
        {"absorb": ["reg:2"], "fields": {"club": "SK Praha"}},
        phase="dedup",
    )

    sheet = get_sheet(client, organizer)
    absorbed = [e for e in sheet["edits"] if e["target"] == "reg:2"]
    assert [e["field"] for e in absorbed] == ["_merged_into"]
    assert absorbed[0]["after"] == "reg:1"
    assert row_by_id(sheet, "reg:2")["_deleted"] is True


def test_undoing_an_entry_reverts_the_cell(client, auth_headers):
    """An entry carries every rule behind it, so removing them all is what the
    console's undo does — one action back to the source value."""
    organizer = auth_headers()
    setup(client, organizer)
    enroll(client, auth_headers, "a@example.com", "Jan Novak")

    add_rule(client, organizer, "reg:1", "name", "Jan Novák")
    add_rule(client, organizer, "reg:1", "name", "Honza Novák")

    entry = get_sheet(client, organizer)["edits"][0]
    for rule_id in entry["rule_ids"]:
        assert (
            client.delete(f"/api/tournaments/cup/rules/{rule_id}", headers=organizer).status_code
            == 204
        )

    sheet = get_sheet(client, organizer)
    assert row_by_id(sheet, "reg:1")["name"] == "Jan Novak"
    assert sheet["edits"] == []


def removed_in(sheet, target):
    """Where a row says it was removed, absent on a row still in the table."""
    return row_by_id(sheet, target).get("_removed_in")


def test_a_deletion_states_the_phase_it_was_made_on(client, auth_headers):
    """The console lists a removed row on the phases before the one that
    removed it, so a removal has to say which phase that was."""
    organizer = auth_headers()
    setup(client, organizer)
    enroll(client, auth_headers, "a@example.com", "Jan")
    enroll(client, auth_headers, "b@example.com", "Petra")

    add_rule(client, organizer, "reg:2", "", "", kind="row_delete", phase="payments")

    sheet = get_sheet(client, organizer)
    assert row_by_id(sheet, "reg:2")["_deleted"] is True
    assert removed_in(sheet, "reg:2") == "payments"
    # a row nobody removed says nothing at all: absence is what "still here" means
    assert "_removed_in" not in row_by_id(sheet, "reg:1")


def test_a_restoration_clears_the_removing_phase(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)
    enroll(client, auth_headers, "a@example.com", "Jan")

    add_rule(client, organizer, "reg:1", "", "", kind="row_delete", phase="fencers")
    add_rule(client, organizer, "reg:1", "", "", kind="row_restore", phase="fencers")

    sheet = get_sheet(client, organizer)
    assert row_by_id(sheet, "reg:1")["_deleted"] is False
    assert "_removed_in" not in row_by_id(sheet, "reg:1")


def test_the_latest_removal_states_the_phase(client, auth_headers):
    """Deleted, brought back, deleted again elsewhere: the removal standing is
    the one the table has to place, not the one that was undone."""
    organizer = auth_headers()
    setup(client, organizer)
    enroll(client, auth_headers, "a@example.com", "Jan")

    add_rule(client, organizer, "reg:1", "", "", kind="row_delete", phase="import")
    add_rule(client, organizer, "reg:1", "", "", kind="row_restore", phase="import")
    add_rule(client, organizer, "reg:1", "", "", kind="row_delete", phase="dedup")

    assert removed_in(get_sheet(client, organizer), "reg:1") == "dedup"


def test_a_merge_states_the_phase_it_was_decided_on(client, auth_headers):
    """A merge removes the absorbed row without ever reporting a deletion, so
    the phase has to be read off the merge itself."""
    organizer = auth_headers()
    setup(client, organizer)
    enroll(client, auth_headers, "a@example.com", "Jan Novak")
    enroll(client, auth_headers, "b@example.com", "Jan Novák")

    post_rule(
        client,
        organizer,
        "dedup_decision",
        "reg:1",
        {"absorb": ["reg:2"], "fields": {}},
        phase="dedup",
    )

    sheet = get_sheet(client, organizer)
    assert row_by_id(sheet, "reg:2")["_merged_into"] == "reg:1"
    assert removed_in(sheet, "reg:2") == "dedup"
    assert "_removed_in" not in row_by_id(sheet, "reg:1")


def test_withdrawing_the_rule_withdraws_the_removing_phase(client, auth_headers):
    """Derived on every replay and stored nowhere: nothing to clean up."""
    organizer = auth_headers()
    setup(client, organizer)
    enroll(client, auth_headers, "a@example.com", "Jan")

    rule_id = add_rule(client, organizer, "reg:1", "", "", kind="row_delete", phase="fencers")
    assert removed_in(get_sheet(client, organizer), "reg:1") == "fencers"

    client.delete(f"/api/tournaments/cup/rules/{rule_id}", headers=organizer)

    sheet = get_sheet(client, organizer)
    assert row_by_id(sheet, "reg:1")["_deleted"] is False
    assert "_removed_in" not in row_by_id(sheet, "reg:1")
