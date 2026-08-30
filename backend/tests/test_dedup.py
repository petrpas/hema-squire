"""LLM HR matching and three-band dedup: verdicts, queue, decision persistence."""

import io

from conftest import outcome, settle

from app.dedup import MergeProposal, ThreeBands, default_merge, get_dedup_llm
from app.hr_match import HRMatchResult, get_hr_matcher
from app.importer import ImportParser, ParsedFencer, get_import_parser
from app.main import app

CSV = (
    "Name,Club,Nationality,Email,HRID,Notes\n"
    "Jan Novak,Prague HEMA,CZ,jan@example.com,,\n"
    "Petra Dvorakova,Ostrava,CZ,petra@example.com,1234,\n"
    "Petra Dvořáková,Ostrava,CZ,petra@example.com,1234,přidávám rapír\n"
    "Karel Serm,Brno Sword Club,CZ,karel@example.com,,\n"
    "Karel Šerm,Brno Sword Club,CZ,karel@example.com,,druhá registrace\n"
    "Marie Nova,Praha,CZ,marie@example.com,,\n"
    "Marie Novakova,Kladno,,marie2@example.com,,\n"
)


class FakeParser(ImportParser):
    def parse_batch(self, rows, disciplines, rentals):
        parsed = []
        for index, raw in enumerate(rows):
            hr = raw.get("HRID", "")
            parsed.append(
                ParsedFencer(
                    registration_time=f"2026-04-01T10:{index:02d}:00",
                    name=raw["Name"],
                    nationality=raw.get("Nationality", ""),
                    email=raw.get("Email"),
                    club=raw.get("Club"),
                    hr_id=int(hr) if hr.strip().isdigit() else None,
                    disciplines=["SA"],
                    notes=raw.get("Notes") or None,
                )
            )
        return parsed


class FakeMatcher:
    """Matches Jan Novak to the stub index profile; finds nobody else."""

    def __init__(self):
        self.calls = 0

    def match(self, fencers, candidates):
        self.calls += 1
        results = []
        for fencer in fencers:
            if fencer["name"] == "Jan Novak":
                results.append(
                    HRMatchResult(
                        name=fencer["name"], club=fencer["club"], hr_id=10234,
                        matched_name="Jan Novák", matched_club="Prague HEMA",
                        nationality="CZ",
                    )
                )
            else:
                results.append(
                    HRMatchResult(
                        name=fencer["name"], club=fencer["club"], hr_id=None,
                        matched_name=None, matched_club=None,
                        nationality=fencer.get("nationality"),
                    )
                )
        return results


class FakeDedupLLM:
    def __init__(self):
        self.classify_calls = 0
        self.merge_calls = 0

    def propose_merge(self, records, language):
        self.merge_calls += 1
        return MergeProposal(fields=default_merge(records), note="records merged")

    def classify(self, records):
        self.classify_calls += 1
        karel = [r["id"] for r in records if r["name"].startswith("Karel")]
        marie = [r["id"] for r in records if r["name"].startswith("Marie")]
        return ThreeBands(surely=[karel], likely=[marie], possible=[])


def setup(client, organizer, parser=None):
    client.post(
        "/api/tournaments",
        json={"slug": "cup", "display_name": "Cup", "date": "2026-12-05"},
        headers=organizer,
    )
    client.post(
        "/api/tournaments/cup/disciplines",
        json={"slug": "SA", "weapon": "SA", "capacity": 20, "fee": 800},
        headers=organizer,
    )
    app.dependency_overrides[get_import_parser] = lambda: parser or FakeParser()
    response = client.post(
        "/api/tournaments/cup/import",
        files={"file": ("regs.csv", io.BytesIO(CSV.encode()), "text/csv")},
        headers=organizer,
    )
    assert response.status_code == 202, response.text
    settle(client, organizer)


def run_match(client, organizer):
    """Start matching and wait it out. The endpoint returns the moment the
    record exists; the outcome is read off the record (conftest.settle)."""
    response = client.post("/api/tournaments/cup/import/match", headers=organizer)
    assert response.status_code == 202, response.text
    return outcome(client, organizer, kind="match")


def run_dedup(client, organizer):
    response = client.post("/api/tournaments/cup/import/dedup", headers=organizer)
    assert response.status_code == 202, response.text
    return outcome(client, organizer, kind="dedup")


def get_rows(client, organizer):
    sheet = client.get("/api/tournaments/cup/sheet", headers=organizer).json()
    return [r for r in sheet["rows"] if r["id"].startswith("imp:")]


def by_name(rows, name):
    return next(r for r in rows if r["name"] == name)


def groups(client, organizer):
    return client.get(
        "/api/tournaments/cup/import/dedup/groups", headers=organizer
    ).json()


def group_of(client, organizer, kind):
    return next(g for g in groups(client, organizer) if g["kind"] == kind)


def decide(client, organizer, key, accept, **body):
    return client.post(
        "/api/tournaments/cup/import/dedup/decide",
        json={"key": key, "accept": accept, **body},
        headers=organizer,
    )


def dedup_rules(client, organizer):
    listing = client.get(
        "/api/tournaments/cup/rules", headers=organizer, params={"phase": "dedup"}
    ).json()
    return [r for r in listing if r["kind"] == "dedup_decision"]


def test_matching_verdicts_and_decision_reuse(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)
    matcher = FakeMatcher()
    app.dependency_overrides[get_hr_matcher] = lambda: matcher

    body = run_match(client, organizer)
    assert body["matched"] == 1
    assert matcher.calls == 1

    rows = get_rows(client, organizer)
    # the proposal binds the id and fills the evidence register; the claim
    # register stays the fencer's words until a verdict (spec etl-console, The
    # ledger idiom)
    jan = by_name(rows, "Jan Novak")
    assert jan["hr_id"] == 10234
    assert jan["name"] == "Jan Novak"
    assert jan["reg_name"] is None
    assert jan["hr_name"] == "Jan Novák"
    assert jan["hr_nationality"] == "CZ"
    assert jan["hr_club"] == "Prague HEMA"
    # same name key, unambiguous in the index, nationality does not contradict
    assert jan["match_verdict"] == "found"
    marie = by_name(rows, "Marie Nova")
    assert marie["match_verdict"] == "none_found"
    petra = by_name(rows, "Petra Dvorakova")
    assert petra["match_verdict"] == "confirmed"  # fencer supplied the id

    # rerun: everything is decided, no LLM call
    body = run_match(client, organizer)
    assert matcher.calls == 1
    assert body["matched"] == 0

    # organizer correction persists as a rule and beats the cached proposal
    client.post(
        "/api/tournaments/cup/rules",
        json={"phase": "matching", "kind": "match_resolution", "target": jan["id"],
              "payload": {"field": "hr_id", "value": None}},
        headers=organizer,
    )
    jan = by_name(get_rows(client, organizer), "Jan Novak")
    assert jan["hr_id"] is None
    assert jan["match_verdict"] == "none_found"
    assert jan["hr_name"] is None


def test_same_hr_id_queues_and_merges_on_confirm(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)
    llm = FakeDedupLLM()
    app.dependency_overrides[get_dedup_llm] = lambda: llm

    body = run_dedup(client, organizer)
    assert body["proposals"] == 1

    same_id = [g for g in groups(client, organizer) if g["kind"] == "same_id"]
    assert len(same_id) == 1
    item = same_id[0]
    assert item["verdict"] == "pending"
    assert item["conclusion"] is None
    assert item["recommendation"]["fields"]["hr_id"] == 1234
    # most recent explicit value prefilled; nothing merged yet
    rows = get_rows(client, organizer)
    assert len([r for r in rows if r["hr_id"] == 1234 and not r["_deleted"]]) == 2

    assert decide(client, organizer, item["key"], True).json()["status"] == "merged"

    rows = get_rows(client, organizer)
    survivors = [r for r in rows if r["hr_id"] == 1234 and not r["_deleted"]]
    absorbed = [r for r in rows if r.get("_merged_into") and r["hr_id"] == 1234]
    assert len(survivors) == 1
    assert survivors[0]["merge_note"] == "records merged"
    assert len(absorbed) == 1
    assert absorbed[0]["_merged_into"] == survivors[0]["id"]

    # the group stays listed, now stating the organizer's verdict and the
    # conclusion it stands on; the proposal decision is not re-asked
    item = group_of(client, organizer, "same_id")
    assert item["verdict"] == "merged"
    assert item["decided_by"] == "organizer"
    assert item["conclusion"]["fields"]["hr_id"] == 1234
    assert item["conclusion"]["note"] == "records merged"
    # and it still states both records it merged, not the survivor alone
    assert len(item["members"]) == 2
    run_dedup(client, organizer)
    assert llm.merge_calls == 1


def test_three_band_classification(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)
    llm = FakeDedupLLM()
    app.dependency_overrides[get_dedup_llm] = lambda: llm

    body = run_dedup(client, organizer)
    assert body["auto_merged"] == 1  # surely: the two Karels
    assert body["likely"] == 1

    rows = get_rows(client, organizer)
    karels = [r for r in rows if (r["name"] or "").startswith("Karel") and not r["_deleted"]]
    assert len(karels) == 1
    assert "druhá registrace" in (karels[0]["notes"] or "")

    # likely: queued, nothing merged until the organizer decides
    maries = [r for r in rows if (r["name"] or "").startswith("Marie") and not r["_deleted"]]
    assert len(maries) == 2
    likely = [g for g in groups(client, organizer) if g["kind"] == "likely"]
    assert len(likely) == 1

    # rejection persists: the group reads as kept separate and stays unmerged
    decide(client, organizer, likely[0]["key"], False)
    assert group_of(client, organizer, "likely")["verdict"] == "separate"
    assert len([r for r in get_rows(client, organizer)
                if (r["name"] or "").startswith("Marie") and not r["_deleted"]]) == 2

    # rerun with an unchanged candidate set does not re-classify
    run_dedup(client, organizer)
    assert llm.classify_calls == 1


def test_removing_merge_rule_reverts_the_merge(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)
    llm = FakeDedupLLM()
    app.dependency_overrides[get_dedup_llm] = lambda: llm
    run_dedup(client, organizer)

    item = group_of(client, organizer, "same_id")
    decide(client, organizer, item["key"], True)

    merge_rule = next(r for r in dedup_rules(client, organizer)
                      if r["payload"].get("fields", {}).get("hr_id") == 1234)
    client.delete(f"/api/tournaments/cup/rules/{merge_rule['id']}", headers=organizer)

    rows = get_rows(client, organizer)
    petras = [r for r in rows if r["hr_id"] == 1234 and not r["_deleted"]]
    assert len(petras) == 2  # merge reverted, both records back

    # and the group is awaiting a decision again rather than settled unmerged:
    # a group is merged while its rule stands, not because a record says it was
    # accepted (spec etl-console, Withdrawing a merge in the log reopens it)
    assert group_of(client, organizer, "same_id")["verdict"] == "pending"


def test_auto_merged_group_is_listed_and_withdrawable(client, auth_headers):
    """The surely band merges without asking, and says so. A machine's verdict
    is stated among the phase's decision units and is one action from its
    opposite (spec etl-console, The ledger idiom / table-import, Three-band
    deduplication)."""
    organizer = auth_headers()
    setup(client, organizer)
    llm = FakeDedupLLM()
    app.dependency_overrides[get_dedup_llm] = lambda: llm
    run_dedup(client, organizer)

    karel = group_of(client, organizer, "surely")
    assert karel["verdict"] == "merged"
    assert karel["decided_by"] == "llm"
    # it states what it merged: both records, not the survivor alone
    assert {m["name"] for m in karel["members"]} == {"Karel Serm", "Karel Šerm"}
    assert karel["conclusion"]["note"] == "auto-merged (surely duplicate)"

    # the organizer disagrees: one action, and the records stand apart again
    assert decide(client, organizer, karel["key"], False).json()["status"] == "rejected"
    karels = [r for r in get_rows(client, organizer)
              if (r["name"] or "").startswith("Karel") and not r["_deleted"]]
    assert len(karels) == 2
    karel = group_of(client, organizer, "surely")
    assert karel["verdict"] == "separate"
    assert karel["decided_by"] == "organizer"

    # and a rerun does not merge it back: the resolution is what stops the run
    run_dedup(client, organizer)
    assert len([r for r in get_rows(client, organizer)
                if (r["name"] or "").startswith("Karel") and not r["_deleted"]]) == 2


def test_a_settled_group_can_be_decided_again(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)
    app.dependency_overrides[get_dedup_llm] = lambda: FakeDedupLLM()
    run_dedup(client, organizer)

    marie = group_of(client, organizer, "likely")
    decide(client, organizer, marie["key"], False)
    assert group_of(client, organizer, "likely")["verdict"] == "separate"

    # merging a group kept separate merges it, with one rule standing
    decide(client, organizer, marie["key"], True)
    marie = group_of(client, organizer, "likely")
    assert marie["verdict"] == "merged"
    maries = [r for r in get_rows(client, organizer)
              if (r["name"] or "").startswith("Marie") and not r["_deleted"]]
    assert len(maries) == 1
    assert len([r for r in dedup_rules(client, organizer)
                if r["target"] == marie["members"][0]["id"]]) == 1


def test_confirming_twice_updates_the_standing_rule(client, auth_headers):
    """One group, one merge rule, whatever the organizer does to it: two rules
    absorbing the same rows would be one decision reported twice in the log and
    undone once (design D4)."""
    organizer = auth_headers()
    setup(client, organizer)
    app.dependency_overrides[get_dedup_llm] = lambda: FakeDedupLLM()
    run_dedup(client, organizer)

    item = group_of(client, organizer, "same_id")
    decide(client, organizer, item["key"], True)
    first = dedup_rules(client, organizer)
    petra_rules = [r for r in first if r["payload"]["fields"].get("hr_id") == 1234]
    assert len(petra_rules) == 1

    decide(client, organizer, item["key"], True, fields={**item["recommendation"]["fields"],
                                                         "club": "Ostrava HEMA"})
    after = [r for r in dedup_rules(client, organizer)
             if r["payload"]["fields"].get("hr_id") == 1234]
    assert len(after) == 1
    assert after[0]["id"] == petra_rules[0]["id"]  # same rule, same log entry
    assert after[0]["payload"]["fields"]["club"] == "Ostrava HEMA"


def test_an_edited_conclusion_is_what_takes_effect(client, auth_headers):
    """Spec table-import: the proposal is corrected before it is confirmed."""
    organizer = auth_headers()
    setup(client, organizer)
    app.dependency_overrides[get_dedup_llm] = lambda: FakeDedupLLM()
    run_dedup(client, organizer)

    item = group_of(client, organizer, "same_id")
    edited = {**item["recommendation"]["fields"], "name": "Petra Dvořáková-Nová",
              "club": "Ostrava HEMA"}
    decide(client, organizer, item["key"], True, fields=edited, note="organizer merged by hand")

    survivor = next(r for r in get_rows(client, organizer)
                    if r["hr_id"] == 1234 and not r["_deleted"])
    assert survivor["name"] == "Petra Dvořáková-Nová"
    assert survivor["club"] == "Ostrava HEMA"
    assert survivor["merge_note"] == "organizer merged by hand"

    # reopening offers each record's own values back, not the merged one
    item = group_of(client, organizer, "same_id")
    assert {m["name"] for m in item["members"]} == {"Petra Dvorakova", "Petra Dvořáková"}


def test_a_deleted_row_is_no_longer_a_duplicate(client, auth_headers):
    """Spec etl-console: a candidate group loses a member a deletion removed."""
    organizer = auth_headers()
    setup(client, organizer)
    app.dependency_overrides[get_dedup_llm] = lambda: FakeDedupLLM()
    run_dedup(client, organizer)

    marie = group_of(client, organizer, "likely")
    client.post(
        "/api/tournaments/cup/rules",
        json={"phase": "fencers", "kind": "row_delete",
              "target": marie["members"][0]["id"], "payload": {}},
        headers=organizer,
    )
    assert all(g["kind"] != "likely" for g in groups(client, organizer))


def test_group_members_carry_number_and_evidence(client, auth_headers):
    """A member row is rendered from the group payload alone (design D2)."""
    organizer = auth_headers()
    setup(client, organizer)
    app.dependency_overrides[get_hr_matcher] = lambda: FakeMatcher()
    run_match(client, organizer)
    app.dependency_overrides[get_dedup_llm] = lambda: FakeDedupLLM()
    run_dedup(client, organizer)

    member = group_of(client, organizer, "same_id")["members"][0]
    assert member["number"] is not None
    assert {"hr_name", "hr_nationality", "hr_club", "email", "registered_at"} <= set(member)


def test_deciding_an_unknown_group_is_not_found(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)
    app.dependency_overrides[get_dedup_llm] = lambda: FakeDedupLLM()
    run_dedup(client, organizer)
    assert decide(client, organizer, "0" * 16, True).status_code == 404


def test_a_merge_reads_as_one_entry(client, auth_headers):
    """One decision, one line. The merged values and the merge note are
    consequences of a single click and are not reported one by one — the
    conclusion the organizer confirmed is on the group, where it can be read
    against the records it came from (spec etl-console, A merge reads as one
    entry)."""
    organizer = auth_headers()
    setup(client, organizer)
    app.dependency_overrides[get_dedup_llm] = lambda: FakeDedupLLM()
    run_dedup(client, organizer)

    item = group_of(client, organizer, "same_id")
    survivor_id = item["members"][0]["id"]
    absorbed_id = item["members"][1]["id"]
    decide(client, organizer, item["key"], True,
           fields={**item["recommendation"]["fields"], "club": "Ostrava HEMA"},
           note="sloučeno pořadatelem")

    edits = client.get("/api/tournaments/cup/sheet", headers=organizer).json()["edits"]
    # this group's own entries: the surely band merged another pair in the same
    # run, which is a different decision and carries its own entry
    dedup_edits = [
        e for e in edits
        if e["phase"] == "dedup" and e["target"] in (survivor_id, absorbed_id)
    ]
    assert len(dedup_edits) == 1
    entry = dedup_edits[0]
    assert entry["target"] == absorbed_id
    assert entry["field"] == "_merged_into"
    assert entry["after"] == survivor_id
    # nothing reports the fields the merge decided, and nothing reports a field
    # that merged one empty value onto another
    assert not any(e["target"] == survivor_id for e in dedup_edits)

    # the consequences are still applied, and undo still reaches the whole merge
    rows = get_rows(client, organizer)
    assert next(r for r in rows if r["id"] == survivor_id)["club"] == "Ostrava HEMA"
    for rule_id in entry["rule_ids"]:
        client.delete(f"/api/tournaments/cup/rules/{rule_id}", headers=organizer)
    rows = get_rows(client, organizer)
    assert len([r for r in rows if r["hr_id"] == 1234 and not r["_deleted"]]) == 2
    assert next(r for r in rows if r["id"] == survivor_id)["club"] != "Ostrava HEMA"
