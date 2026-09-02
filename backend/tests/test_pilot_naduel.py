"""Task 6.3 — pilot replay on the real Na Duel! 2026 dataset.

The v1 archive is the ground truth: the actual Google-Form CSV (54 rows) plus
the LLM outputs the v1 pipeline produced and the organizer ran the tournament
on. Here the same CSV goes through the v2 intake, and the archived outputs
replay as parser/matcher/dedup stand-ins — validating the pipeline mechanics
and decision persistence on real data, without spending LLM calls. The final
sheet must reproduce fencers_deduped.json: 53 fencers, the duplicate Florian
Imhof registration merged, and the Bělina likely-pair still queued, exactly
as the v1 organizer left it.

One thing v2 does differently on purpose: v1 wrote HR's canonical name, club
and nationality straight into the roster, while v2 leaves the claim register in
the fencer's own words and files HR's reading in the evidence register until an
organizer confirms it (spec etl-console, The ledger idiom). So those three
fields are checked against `fencers_matched.json` through `hr_name`/`hr_club`
rather than through the roster comparison.

Runs only where the archive exists (skipped in CI); personal data never
enters this repository.
"""

import json
from pathlib import Path

import pytest

from app.dedup import MergeProposal, ThreeBands, default_merge, get_dedup_llm
from app.hr_match import HRMatchResult, get_hr_matcher
from app.importer import ParsedFencer, get_import_parser
from app.main import app
from tests.conftest import outcome as operation_outcome


# the v1 archive predates slugs: `disciplines` entries are {weapon, gender,
# material} dicts. This reproduces the taxonomy code they described (the old
# importer.ParsedDiscipline.code property) purely to replay/compare archived
# fixtures — the current pipeline itself never emits this shape (design
# discipline-identity D7).
def _legacy_code(d: dict) -> str:
    material = "" if d.get("material", "") in ("", "Steel") else d["material"]
    gender = d.get("gender", "") if d.get("gender", "") in ("W", "M") else ""
    return f"{material} {d['weapon']}{gender}".strip()

ARCHIVE = Path.home() / "hema/hema-agent/data/Na Duel! 2026"

pytestmark = pytest.mark.skipif(
    not ARCHIVE.exists(), reason="Na Duel! 2026 archive not present on this machine"
)


@pytest.fixture
def archive():
    parsed = json.loads((ARCHIVE / "fencers_parsed.json").read_text())
    matched = json.loads((ARCHIVE / "fencers_matched.json").read_text())
    deduped = json.loads((ARCHIVE / "fencers_deduped.json").read_text())
    likely = json.loads((ARCHIVE / "fencers_likely_groups_pending.json").read_text())
    # v1's pandas read a phantom empty row the csv module does not see
    keep = [i for i, r in enumerate(parsed) if r["name"] != "<UNKNOWN>"]
    return {
        "csv": (ARCHIVE / "registration_csv/registrations_v0.csv").read_bytes(),
        "parsed": [parsed[i] for i in keep],
        "matched": [matched[i] for i in keep],
        "deduped": [r for r in deduped if r["name"] != "<UNKNOWN>"],
        "likely_names": {r["name"] for group in likely.values() for r in group},
    }


class ArchiveParser:
    """Replays v1's stored parse output; order-aligned with the CSV.

    The importer parses in batches, so the archive is consumed with a cursor
    that advances across calls — the row/archive alignment still has to hold.
    """

    def __init__(self, parsed: list[dict]):
        self.parsed = parsed
        self.cursor = 0
        self.calls = 0

    def parse_batch(self, rows, disciplines, rentals):
        self.calls += 1
        archived_batch = self.parsed[self.cursor : self.cursor + len(rows)]
        assert len(archived_batch) == len(rows), "archive ran out of parsed rows"
        self.cursor += len(rows)
        records = []
        for raw, archived in zip(rows, archived_batch, strict=True):
            assert (raw["E-mailová adresa"] or None) == archived["email"], (
                "archive/CSV row alignment broke"
            )
            records.append(
                ParsedFencer(
                    **{
                        **archived,
                        "disciplines": [_legacy_code(d) for d in archived["disciplines"]],
                    }
                )
            )
        return records


class ArchiveMatcher:
    """Replays v1's stored match output, keyed by the parsed identity."""

    def __init__(self, parsed: list[dict], matched: list[dict]):
        self.by_identity = {
            (p["name"], p["club"]): m for p, m in zip(parsed, matched, strict=True)
        }
        self.calls = 0

    def match(self, fencers, candidates):
        self.calls += 1
        results = []
        for fencer in fencers:
            archived = self.by_identity[(fencer["name"], fencer["club"])]
            results.append(
                HRMatchResult(
                    name=fencer["name"],
                    club=fencer["club"],
                    hr_id=archived["hr_id"],
                    matched_name=archived["name"] if archived["hr_id"] else None,
                    matched_club=archived["club"] if archived["hr_id"] else None,
                    nationality=archived["nationality"] or None,
                )
            )
        return results


class ArchiveDedup:
    """Same-id merges via the v1 default rules; likely groups from the archive."""

    def __init__(self, likely_names: set[str]):
        self.likely_names = likely_names
        self.classify_calls = 0

    def propose_merge(self, records, language):
        return MergeProposal(
            fields=default_merge(records), note="duplicate registration merged"
        )

    def classify(self, records):
        self.classify_calls += 1
        likely = [r["id"] for r in records if r["name"] in self.likely_names]
        return ThreeBands(likely=[likely] if len(likely) > 1 else [])


# v1 wrote HR's canonical name, club and nationality straight into the roster.
# v2 keeps them out of the claim register until an organizer confirms the match
# (spec etl-console, The ledger idiom), so those three are compared separately,
# against the evidence register, and the roster comparison covers the rest.
def fencer_view(hr_id, email, disciplines, afterparty, rentals, notes):
    # sortable: the roster comparison sorts these tuples, and both an absent
    # email and an unmatched hr_id are ordinary here
    return (email or "", hr_id or 0, tuple(sorted(disciplines)), afterparty,
            tuple(sorted(rentals)), notes or None)


def archive_view(record):
    codes = [_legacy_code(d) for d in record["disciplines"]]
    return fencer_view(
        record["hr_id"], record["email"], codes,
        record["after_party"] == "Yes", record["borrow"], record["notes"],
    )


def sheet_view(row):
    return fencer_view(
        row["hr_id"], row["email"], row["disciplines"], row["afterparty"],
        row["weapon_rentals"], row["notes"],
    )


def test_pilot_replay_reproduces_v1_final_state(client, auth_headers, archive):
    organizer = auth_headers()
    client.post(
        "/api/tournaments",
        json={"slug": "na-duel-2026", "display_name": "Na Duel! 2026",
              "date": "2026-10-17"},
        headers=organizer,
    )
    for code in ("SA", "SB"):
        client.post(
            "/api/tournaments/na-duel-2026/disciplines",
            json={"slug": code, "weapon": code, "capacity": 64, "fee": 800},
            headers=organizer,
        )

    parser = ArchiveParser(archive["parsed"])
    matcher = ArchiveMatcher(archive["parsed"], archive["matched"])
    dedup = ArchiveDedup(archive["likely_names"])
    app.dependency_overrides[get_import_parser] = lambda: parser
    app.dependency_overrides[get_hr_matcher] = lambda: matcher
    app.dependency_overrides[get_dedup_llm] = lambda: dedup

    # 1. intake: the real Google-Form export, every row parsed, problems surfaced
    client.post(
        "/api/tournaments/na-duel-2026/import",
        files={"file": ("registrations_v0.csv", archive["csv"], "text/csv")},
        headers=organizer,
    )
    # the parse runs behind the request now, so the counts come off the record
    parsed = operation_outcome(client, organizer, "na-duel-2026", "parse")
    assert parsed["rows"] == 54
    assert parsed["parsed"] == 54
    problem_rows = {p["problems"] for p in parsed["problems"]}
    assert any("Duplicate registration" in p for p in problem_rows)
    assert len(parsed["problems"]) == 4
    # the parser runs a batch at a time; what matters below is that the
    # re-import in step 6 adds no calls at all, not the batch count itself
    parse_calls = parser.calls

    # 2. matching: v1 matched 51 of 54; canonical names apply, reg_name retained
    client.post("/api/tournaments/na-duel-2026/import/match", headers=organizer)
    result = operation_outcome(client, organizer, "na-duel-2026", "match")
    assert result == {"matched": 51, "unmatched": 3, "reused": 0}

    def rows():
        sheet = client.get(
            "/api/tournaments/na-duel-2026/sheet", headers=organizer
        ).json()
        return [r for r in sheet["rows"] if not r["_deleted"]]

    by_name = {r["name"]: r for r in rows()}
    # the form split this fencer across the two fields; the row still says what
    # they typed, and HR's reading of it sits beside it as evidence
    sourek = by_name["Jan"]
    assert sourek["club"] == "Šourek"
    assert sourek["hr_name"] == "Jan Šourek"
    assert sourek["hr_club"] == "AKA - Akademie rytířských umění"
    assert sourek["match_verdict"] == "proposed"
    szucs = by_name["Szücs Kornél Antal"]  # HR canonicalizes the name order
    assert szucs["hr_name"] == "Kornél Antal Szücs"
    assert by_name["Jan Sax Bělina"]["match_verdict"] == "none_found"

    # 3. dedup: the Florian pair queues (nothing merges silently), Bělinas likely
    client.post("/api/tournaments/na-duel-2026/import/dedup", headers=organizer)
    result = operation_outcome(client, organizer, "na-duel-2026", "dedup")
    assert result == {"proposals": 1, "auto_merged": 0, "likely": 1}
    groups = client.get(
        "/api/tournaments/na-duel-2026/import/dedup/groups", headers=organizer
    ).json()
    assert len(groups) == 2
    assert all(g["verdict"] == "pending" for g in groups)
    florian_item = next(g for g in groups if g["kind"] == "same_id")
    assert {r["name"] for r in florian_item["members"]} == {"Florian Imhof"}
    belina_item = next(g for g in groups if g["kind"] == "likely")
    assert {r["name"] for r in belina_item["members"]} == {
        "Jan Sax Bělina", "Daniel Bělina",
    }

    # 4. the organizer confirms the Florian merge (as they did in v1)
    client.post(
        "/api/tournaments/na-duel-2026/import/dedup/decide",
        json={"key": florian_item["key"], "accept": True},
        headers=organizer,
    )

    # 5. final state == the roster v1 ran the tournament on
    final = rows()
    assert len(final) == len(archive["deduped"]) == 53
    ours = sorted(sheet_view(r) for r in final)
    v1 = sorted(archive_view(r) for r in archive["deduped"])
    # the merged Florian: v1 kept problems=None on the surviving record; ours
    # does the same via default_merge — compare full tuples
    assert ours == v1

    # and what v1 wrote into the roster, v2 holds as evidence against the words
    # the fencer actually gave — every matched row's canonical name and club
    canonical = {
        (p["name"], p["club"]): m
        for p, m in zip(archive["parsed"], archive["matched"], strict=True)
    }
    matched_rows = [r for r in final if r["hr_id"] is not None]
    assert len(matched_rows) == 51 - 1  # 51 matched, less the merged Florian
    for row in matched_rows:
        archived = canonical[(row["name"], row["club"])]
        assert row["hr_id"] == archived["hr_id"]
        assert row["hr_name"] == archived["name"]
        assert row["hr_club"] == archived["club"]

    # the Bělina pair stays pending, matching the archived likely-groups file;
    # the Florian pair stays listed, now stating the merge the organizer made
    groups = client.get(
        "/api/tournaments/na-duel-2026/import/dedup/groups", headers=organizer
    ).json()
    verdicts = {g["kind"]: g["verdict"] for g in groups}
    assert verdicts == {"same_id": "merged", "likely": "pending"}

    # 6. incrementality on real data: reruns of every stage cost nothing
    # nothing is left undecided, so the re-upload answers without an operation
    # at all (spec table-import, Reused rows are not work)
    reimport = client.post(
        "/api/tournaments/na-duel-2026/import",
        files={"file": ("registrations_v0.csv", archive["csv"], "text/csv")},
        headers=organizer,
    ).json()
    assert reimport["reused"] == 54 and reimport["parsed"] == 0
    client.post("/api/tournaments/na-duel-2026/import/match", headers=organizer)
    result = operation_outcome(client, organizer, "na-duel-2026", "match")
    assert result["matched"] == 0 and result["unmatched"] == 0
    client.post("/api/tournaments/na-duel-2026/import/dedup", headers=organizer)
    assert parser.calls == parse_calls
    assert matcher.calls == 1
    assert dedup.classify_calls == 1

    # 7. determinism: the replayed sheet is stable across fetches
    first = client.get("/api/tournaments/na-duel-2026/sheet", headers=organizer).json()
    assert client.get(
        "/api/tournaments/na-duel-2026/sheet", headers=organizer
    ).json() == first
