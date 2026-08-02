"""LLM HR matching and three-band dedup: verdicts, queue, decision persistence."""

import io

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
    def parse(self, rows, disciplines):
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
    assert response.status_code == 200, response.text


def get_rows(client, organizer):
    sheet = client.get("/api/tournaments/cup/sheet", headers=organizer).json()
    return [r for r in sheet["rows"] if r["id"].startswith("imp:")]


def by_name(rows, name):
    return next(r for r in rows if r["name"] == name)


def test_matching_verdicts_and_decision_reuse(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)
    matcher = FakeMatcher()
    app.dependency_overrides[get_hr_matcher] = lambda: matcher

    body = client.post("/api/tournaments/cup/import/match", headers=organizer).json()
    assert body["matched"] == 1
    assert matcher.calls == 1

    rows = get_rows(client, organizer)
    jan = by_name(rows, "Jan Novák")  # canonical HR name applied
    assert jan["hr_id"] == 10234
    assert jan["match_verdict"] == "proposed"
    assert jan["reg_name"] == "Jan Novak"  # original registration name retained
    marie = by_name(rows, "Marie Nova")
    assert marie["match_verdict"] == "none_found"
    petra = by_name(rows, "Petra Dvorakova")
    assert petra["match_verdict"] == "confirmed"  # fencer supplied the id

    # rerun: everything is decided, no LLM call
    body = client.post("/api/tournaments/cup/import/match", headers=organizer).json()
    assert matcher.calls == 1
    assert body["matched"] == 0

    # organizer correction persists as a rule and beats the cached proposal
    client.post(
        "/api/tournaments/cup/rules",
        json={"phase": "matching", "kind": "match_resolution", "target": jan["id"],
              "payload": {"field": "hr_id", "value": None}},
        headers=organizer,
    )
    jan = by_name(get_rows(client, organizer), "Jan Novák")
    assert jan["hr_id"] is None
    assert jan["match_verdict"] == "none_found"


def test_same_hr_id_queues_and_merges_on_confirm(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)
    llm = FakeDedupLLM()
    app.dependency_overrides[get_dedup_llm] = lambda: llm

    body = client.post("/api/tournaments/cup/import/dedup", headers=organizer).json()
    assert body["proposals"] == 1

    queue = client.get("/api/tournaments/cup/import/dedup/queue", headers=organizer).json()
    same_id = [item for item in queue if item["kind"] == "same_id"]
    assert len(same_id) == 1
    item = same_id[0]
    assert item["fields"]["hr_id"] == 1234
    # most recent explicit value prefilled; nothing merged yet
    rows = get_rows(client, organizer)
    assert len([r for r in rows if r["hr_id"] == 1234 and not r["_deleted"]]) == 2

    decision = client.post(
        "/api/tournaments/cup/import/dedup/decide",
        json={"key": item["key"], "accept": True},
        headers=organizer,
    ).json()
    assert decision["status"] == "merged"

    rows = get_rows(client, organizer)
    survivors = [r for r in rows if r["hr_id"] == 1234 and not r["_deleted"]]
    absorbed = [r for r in rows if r.get("_merged_into") and r["hr_id"] == 1234]
    assert len(survivors) == 1
    assert survivors[0]["merge_note"] == "records merged"
    assert len(absorbed) == 1
    assert absorbed[0]["_merged_into"] == survivors[0]["id"]

    # the item left the queue; the proposal decision is not re-asked
    queue = client.get("/api/tournaments/cup/import/dedup/queue", headers=organizer).json()
    assert all(i["kind"] != "same_id" for i in queue)
    client.post("/api/tournaments/cup/import/dedup", headers=organizer)
    assert llm.merge_calls == 1


def test_three_band_classification(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)
    llm = FakeDedupLLM()
    app.dependency_overrides[get_dedup_llm] = lambda: llm

    body = client.post("/api/tournaments/cup/import/dedup", headers=organizer).json()
    assert body["auto_merged"] == 1  # surely: the two Karels
    assert body["likely"] == 1

    rows = get_rows(client, organizer)
    karels = [r for r in rows if (r["name"] or "").startswith("Karel") and not r["_deleted"]]
    assert len(karels) == 1
    assert "druhá registrace" in (karels[0]["notes"] or "")

    # likely: queued, nothing merged until the organizer decides
    maries = [r for r in rows if (r["name"] or "").startswith("Marie") and not r["_deleted"]]
    assert len(maries) == 2
    queue = client.get("/api/tournaments/cup/import/dedup/queue", headers=organizer).json()
    likely = [item for item in queue if item["kind"] == "likely"]
    assert len(likely) == 1

    # rejection persists: the group leaves the queue and stays unmerged
    client.post(
        "/api/tournaments/cup/import/dedup/decide",
        json={"key": likely[0]["key"], "accept": False},
        headers=organizer,
    )
    queue = client.get("/api/tournaments/cup/import/dedup/queue", headers=organizer).json()
    assert all(i["kind"] != "likely" for i in queue)
    assert len([r for r in get_rows(client, organizer)
                if (r["name"] or "").startswith("Marie") and not r["_deleted"]]) == 2

    # rerun with an unchanged candidate set does not re-classify
    client.post("/api/tournaments/cup/import/dedup", headers=organizer)
    assert llm.classify_calls == 1


def test_removing_merge_rule_reverts_the_merge(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)
    llm = FakeDedupLLM()
    app.dependency_overrides[get_dedup_llm] = lambda: llm
    client.post("/api/tournaments/cup/import/dedup", headers=organizer)

    queue = client.get("/api/tournaments/cup/import/dedup/queue", headers=organizer).json()
    item = next(i for i in queue if i["kind"] == "same_id")
    client.post(
        "/api/tournaments/cup/import/dedup/decide",
        json={"key": item["key"], "accept": True},
        headers=organizer,
    )

    rules = client.get(
        "/api/tournaments/cup/rules", headers=organizer, params={"phase": "dedup"}
    ).json()
    merge_rule = next(r for r in rules if r["kind"] == "dedup_decision"
                      and r["payload"].get("fields", {}).get("hr_id") == 1234)
    client.delete(f"/api/tournaments/cup/rules/{merge_rule['id']}", headers=organizer)

    rows = get_rows(client, organizer)
    petras = [r for r in rows if r["hr_id"] == 1234 and not r["_deleted"]]
    assert len(petras) == 2  # merge reverted, both records back
