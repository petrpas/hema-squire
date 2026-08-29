"""The Matching row as a ledger line: what the fencer claimed, what HEMA
Ratings holds, and the verdict — and the verdict's consequences (spec
etl-console, The ledger idiom / HR matching review).
"""

import io

from conftest import outcome, settle

from app.hr_index import HRProfile, StubHRIndex, get_hr_index
from app.hr_match import HRMatchResult, get_hr_matcher
from app.importer import ImportParser, ParsedFencer, get_import_parser
from app.main import app

# One roster, five verdicts.
CSV = (
    "Name,Club,Nationality,HRID\n"
    # exact name, unambiguous, club spelled differently — still found
    "Jan Novak,SHS Krkavci,CZ,\n"
    # a spelling the model had to judge
    "Lukas Müller,Berlin Schwert,DE,\n"
    # a name two indexed fighters answer to
    "Petr Svoboda,Brno Sword Club,CZ,\n"
    # the fencer supplied their own id
    "Petra Dvorakova,Ostrava,CZ,1234\n"
    # nobody to find
    "Marie Nova,Praha,CZ,\n"
)

PROFILES = [
    HRProfile(hr_id=10234, name="Jan Novák", nationality="CZE", club="Prague HEMA"),
    HRProfile(hr_id=8821, name="Lukas Mueller", nationality="DEU", club="Berlin Schwert"),
    HRProfile(hr_id=5567, name="Petr Svoboda", nationality="CZE", club="Brno Sword Club"),
    HRProfile(hr_id=6000, name="Svoboda Petr", nationality="CZE", club="Plzeň HEMA"),
]

MATCHES = {
    "Jan Novak": (10234, "Jan Novák", "Prague HEMA"),
    "Lukas Müller": (8821, "Lukas Mueller", "Berlin Schwert"),
    "Petr Svoboda": (5567, "Petr Svoboda", "Brno Sword Club"),
}


class FakeParser(ImportParser):
    def parse_batch(self, rows, disciplines, rentals):
        return [
            ParsedFencer(
                registration_time=f"2026-04-01T10:{i:02d}:00",
                name=raw["Name"],
                nationality=raw.get("Nationality", ""),
                email=None,
                club=raw.get("Club"),
                hr_id=int(raw["HRID"]) if raw.get("HRID", "").strip().isdigit() else None,
                disciplines=["SA"],
                notes=None,
            )
            for i, raw in enumerate(rows)
        ]


class FakeMatcher:
    def match(self, fencers, candidates):
        results = []
        for fencer in fencers:
            hit = MATCHES.get(fencer["name"])
            results.append(
                HRMatchResult(
                    name=fencer["name"],
                    club=fencer["club"],
                    hr_id=hit[0] if hit else None,
                    matched_name=hit[1] if hit else None,
                    matched_club=hit[2] if hit else None,
                    nationality=fencer.get("nationality"),
                )
            )
        return results


def setup(client, organizer):
    app.dependency_overrides[get_hr_index] = lambda: StubHRIndex(PROFILES)
    app.dependency_overrides[get_import_parser] = lambda: FakeParser()
    app.dependency_overrides[get_hr_matcher] = lambda: FakeMatcher()
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
    response = client.post(
        "/api/tournaments/cup/import",
        files={"file": ("regs.csv", io.BytesIO(CSV.encode()), "text/csv")},
        headers=organizer,
    )
    assert response.status_code == 202, response.text
    settle(client, organizer)
    assert client.post(
        "/api/tournaments/cup/import/match", headers=organizer
    ).status_code == 202
    outcome(client, organizer, kind="match")


def rows(client, organizer):
    sheet = client.get("/api/tournaments/cup/sheet", headers=organizer).json()
    return {r["name"]: r for r in sheet["rows"] if r["id"].startswith("imp:")}


def row_by_id(client, organizer, row_id):
    """A promoted name can collide with another row's, so a row followed across
    a verdict is followed by its id."""
    sheet = client.get("/api/tournaments/cup/sheet", headers=organizer).json()
    return next(r for r in sheet["rows"] if r["id"] == row_id)


def resolve(client, organizer, row, value):
    return client.post(
        "/api/tournaments/cup/rules",
        json={
            "phase": "matching",
            "kind": "match_resolution",
            "target": row["id"],
            "payload": {"field": "hr_id", "value": value},
        },
        headers=organizer,
    )


def test_five_verdicts_over_one_roster(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)
    table = rows(client, organizer)

    # a lookup, not a judgment — and a differing club does not demote it
    jan = table["Jan Novak"]
    assert jan["match_verdict"] == "found"
    assert jan["club"] == "SHS Krkavci"
    assert jan["hr_club"] == "Prague HEMA"

    # a spelling the model reached by judgment
    assert table["Lukas Müller"]["match_verdict"] == "proposed"

    # two fighters answer to this name key, however exact the hit
    assert table["Petr Svoboda"]["match_verdict"] == "proposed"

    # the fencer's own id is a verdict at birth
    petra = table["Petra Dvorakova"]
    assert petra["match_verdict"] == "confirmed"
    assert petra["hr_id"] == 1234
    assert petra["hr_name"] is None  # the index does not carry that id

    assert table["Marie Nova"]["match_verdict"] == "none_found"


def test_the_claim_register_survives_every_verdict(client, auth_headers):
    """No operation writes what the fencer told us; the profile's values sit
    beside them in the evidence register."""
    organizer = auth_headers()
    setup(client, organizer)
    table = rows(client, organizer)

    for name, club, nationality in (
        ("Jan Novak", "SHS Krkavci", "CZ"),
        ("Lukas Müller", "Berlin Schwert", "DE"),
        ("Marie Nova", "Praha", "CZ"),
    ):
        row = table[name]
        assert row["name"] == name
        assert row["club"] == club
        assert row["nationality"] == nationality
        assert row["reg_name"] is None

    lukas = table["Lukas Müller"]
    assert lukas["hr_name"] == "Lukas Mueller"
    assert lukas["hr_nationality"] == "DE"
    assert lukas["hr_club"] == "Berlin Schwert"


def test_ratifying_promotes_the_canonical_name(client, auth_headers):
    """Promotion follows the verdict, not the proposal (spec hr-integration,
    Canonical naming)."""
    organizer = auth_headers()
    setup(client, organizer)
    lukas = rows(client, organizer)["Lukas Müller"]
    assert resolve(client, organizer, lukas, lukas["hr_id"]).status_code == 201

    promoted = row_by_id(client, organizer, lukas["id"])
    assert promoted["name"] == "Lukas Mueller"
    assert promoted["match_verdict"] == "confirmed"
    assert promoted["reg_name"] == "Lukas Müller"  # the original stays retrievable
    assert promoted["hr_id"] == 8821


def test_a_typed_id_is_a_verdict(client, auth_headers):
    """An id entered into the row carries what a search selection carries."""
    organizer = auth_headers()
    setup(client, organizer)
    marie = rows(client, organizer)["Marie Nova"]
    assert resolve(client, organizer, marie, 10234).status_code == 201

    promoted = row_by_id(client, organizer, marie["id"])
    assert promoted["match_verdict"] == "confirmed"
    assert promoted["hr_id"] == 10234
    assert promoted["hr_club"] == "Prague HEMA"
    assert promoted["reg_name"] == "Marie Nova"


def test_clearing_the_id_states_no_profile(client, auth_headers):
    organizer = auth_headers()
    setup(client, organizer)
    jan = rows(client, organizer)["Jan Novak"]
    assert resolve(client, organizer, jan, None).status_code == 201

    cleared = row_by_id(client, organizer, jan["id"])
    assert cleared["match_verdict"] == "none_found"
    assert cleared["hr_id"] is None
    assert cleared["hr_name"] is None


def test_a_settled_row_is_revisable(client, auth_headers):
    """Found and confirmed rows still accept an alternative."""
    organizer = auth_headers()
    setup(client, organizer)
    jan = rows(client, organizer)["Jan Novak"]
    assert resolve(client, organizer, jan, 5567).status_code == 201

    revised = row_by_id(client, organizer, jan["id"])
    assert revised["hr_id"] == 5567
    assert revised["match_verdict"] == "confirmed"
    assert revised["name"] == "Petr Svoboda"
    assert revised["reg_name"] == "Jan Novak"


def edits(client, organizer):
    sheet = client.get("/api/tournaments/cup/sheet", headers=organizer).json()
    return {(e["target"], e["field"]): e for e in sheet["edits"]}


def test_one_decision_reads_as_one_entry(client, auth_headers):
    """Accepting a proposal binds the id the proposal had already put on the
    row, so the verdict is the whole of what the organizer decided. Its
    consequences — the promoted name, the name it displaced, the evidence
    register — are the verdict's, not second decisions, and none of them earns
    a line of its own."""
    organizer = auth_headers()
    setup(client, organizer)
    lukas = rows(client, organizer)["Lukas Müller"]
    resolve(client, organizer, lukas, lukas["hr_id"])

    log = edits(client, organizer)
    assert [key for key in log if key[0] == lukas["id"]] == [
        (lukas["id"], "match_verdict")
    ]
    verdict = log[(lukas["id"], "match_verdict")]
    assert (verdict["before"], verdict["after"]) == ("proposed", "confirmed")
    # the promotion still happened, it simply is not a second entry
    assert row_by_id(client, organizer, lukas["id"])["name"] == "Lukas Mueller"


def test_a_verdict_that_moves_the_id_is_not_logged_twice(client, auth_headers):
    """Where the id does change, the resolution states its verdict alongside
    it, and as two entries they would say the same thing twice (spec
    edit-rules, Audit of applied changes)."""
    organizer = auth_headers()
    setup(client, organizer)
    marie = rows(client, organizer)["Marie Nova"]
    resolve(client, organizer, marie, 10234)

    log = edits(client, organizer)
    assert [key for key in log if key[0] == marie["id"]] == [(marie["id"], "hr_id")]
    assert log[(marie["id"], "hr_id")]["after"] == 10234


def test_undoing_a_ratification_restores_the_claim(client, auth_headers):
    """Removing the rule removes its consequences: the fencer's name comes
    back, because promotion lives exactly as long as the verdict."""
    organizer = auth_headers()
    setup(client, organizer)
    lukas = rows(client, organizer)["Lukas Müller"]
    rule = resolve(client, organizer, lukas, lukas["hr_id"]).json()

    client.delete(f"/api/tournaments/cup/rules/{rule['id']}", headers=organizer)
    restored = row_by_id(client, organizer, lukas["id"])
    assert restored["name"] == "Lukas Müller"
    assert restored["match_verdict"] == "proposed"


def test_stored_decisions_take_a_tier_without_a_rerun(client, auth_headers):
    """The tier is a replay product, so decisions stored before it existed take
    one on the next read of the table — no matcher is invoked (spec
    table-import, Existing decisions take a tier without a rerun)."""
    organizer = auth_headers()
    setup(client, organizer)

    class RefusingMatcher:
        def match(self, fencers, candidates):
            raise AssertionError("the tier must not re-invoke the model")

    app.dependency_overrides[get_hr_matcher] = lambda: RefusingMatcher()
    table = rows(client, organizer)
    assert table["Jan Novak"]["match_verdict"] == "found"
    assert table["Lukas Müller"]["match_verdict"] == "proposed"


def test_the_evidence_register_speaks_in_codes(client, auth_headers):
    """The register sits beside a claim written in ISO codes, so it states the
    profile's country as one: a reader comparing "PL" against "Poland" would be
    reading a difference that is not there."""
    organizer = auth_headers()
    setup(client, organizer)
    # an index spelling its countries the way the real one does
    app.dependency_overrides[get_hr_index] = lambda: StubHRIndex(
        [HRProfile(hr_id=42, name="Jakub Rejmus", nationality="Poland", club="Kraków")]
    )
    marie = rows(client, organizer)["Marie Nova"]
    resolve(client, organizer, marie, 42)

    bound = row_by_id(client, organizer, marie["id"])
    assert bound["hr_nationality"] == "PL"


def test_a_rule_stored_before_the_codes_still_reads_as_one(client, auth_headers):
    """A resolution recorded when the register spoke the index's English is
    resolved again on the way out, so no two rows disagree about a spelling."""
    organizer = auth_headers()
    setup(client, organizer)
    marie = rows(client, organizer)["Marie Nova"]
    client.post(
        "/api/tournaments/cup/rules",
        json={
            "phase": "matching",
            "kind": "match_resolution",
            "target": marie["id"],
            # the shape stored before evidence carried codes
            "payload": {"field": "hr_id", "value": 8821, "hr_name": "Lukas Mueller",
                        "hr_nationality": "Germany", "hr_club": "Berlin Schwert"},
        },
        headers=organizer,
    )
    assert row_by_id(client, organizer, marie["id"])["hr_nationality"] == "DE"
