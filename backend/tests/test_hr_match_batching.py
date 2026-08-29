"""The matcher's batching: a roster too large for one answer, asked in pieces.

Regression for the whole-roster prompt, which asked for 55 verdicts at once and
came back truncated at the model's output ceiling — an empty tool call, three
retries, and a 500 on /import/match.
"""

import io
import json

from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from app.hr_index import HRProfile
from app.hr_match import (
    MATCH_BATCH_SIZE,
    MATCH_MAX_TOKENS,
    LLMHRMatcher,
    get_hr_matcher,
)
from app.importer import ImportParser, ParsedFencer, get_import_parser
from app.main import app


def _prompt_fencers(messages) -> list[dict]:
    text = messages[-1].parts[-1].content
    body = text.split("```json\n", 1)[1].split("\n```", 1)[0]
    return json.loads(body)


class RecordingModel:
    """A FunctionModel that echoes one null verdict per fencer and remembers
    the shape of every prompt it was handed."""

    def __init__(self):
        self.batches: list[int] = []
        self.candidates: list[list[str]] = []
        self.settings: list[dict | None] = []
        self.model = FunctionModel(self._respond)

    def _respond(self, messages, info: AgentInfo) -> ModelResponse:
        fencers = _prompt_fencers(messages)
        self.batches.append(len(fencers))
        self.settings.append(info.model_settings)
        lines = messages[-1].parts[-1].content.split("Candidate fighters:\n```\n", 1)[1]
        block = lines.split("\n```", 1)[0]
        self.candidates.append([line for line in block.split("\n") if line])
        matches = [
            {
                "name": f["name"],
                "club": f["club"],
                "hr_id": None,
                "matched_name": None,
                "matched_club": None,
                "nationality": f.get("nationality"),
            }
            for f in fencers
        ]
        return ModelResponse(
            parts=[ToolCallPart("final_result", {"matches": matches})]
        )


def test_roster_is_asked_in_batches_with_its_own_candidates():
    recorder = RecordingModel()
    matcher = LLMHRMatcher(recorder.model)
    fencers = [
        {"name": f"Given{i:02d} Sur{i:02d}", "club": "Club", "nationality": "CZ"}
        for i in range(MATCH_BATCH_SIZE + 5)
    ]
    candidates = [
        HRProfile(hr_id=i, name=f"Given{i:02d} Sur{i:02d}", nationality="CZ", club="Club")
        for i in range(MATCH_BATCH_SIZE + 5)
    ]

    results = matcher.match(fencers, candidates)

    assert len(results) == len(fencers)
    assert recorder.batches == [MATCH_BATCH_SIZE, 5]
    # the output ceiling is raised past the default that truncated the answer
    assert all(s and s.get("max_tokens") == MATCH_MAX_TOKENS for s in recorder.settings)
    # each prompt carries only the candidates its own batch could match
    assert len(recorder.candidates[0]) == MATCH_BATCH_SIZE
    assert len(recorder.candidates[1]) == 5


DUPLICATE_CSV = (
    "Name,Club,Nationality,Email\n"
    "Jan Novak,Prague HEMA,CZ,jan@example.com\n"
    "Jan Novak,Prague HEMA,CZ,jan.novak@example.com\n"
)


class TwoRowParser(ImportParser):
    def parse(self, rows, disciplines, rentals):
        return [
            ParsedFencer(
                name=raw["Name"],
                club=raw["Club"],
                nationality=raw["Nationality"],
                email=raw["Email"],
                disciplines=["SA"],
                registration_time=f"2026-04-01T10:{index:02d}:00",
            )
            for index, raw in enumerate(rows)
        ]


class CountingMatcher:
    """Answers nobody; counts how many fencers it was ever asked about."""

    def __init__(self):
        self.asked: list[str] = []

    def match(self, fencers, candidates):
        from app.hr_match import HRMatchResult

        self.asked.extend(f["name"] for f in fencers)
        return [
            HRMatchResult(
                name=f["name"], club=f["club"], hr_id=10234,
                matched_name="Jan Novák", matched_club="Prague HEMA",
                nationality="CZ",
            )
            for f in fencers
        ]


def test_identical_rows_are_one_question_and_both_count_as_matched(
    client, auth_headers
):
    organizer = auth_headers()
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
    app.dependency_overrides[get_import_parser] = lambda: TwoRowParser()
    assert client.post(
        "/api/tournaments/cup/import",
        files={"file": ("regs.csv", io.BytesIO(DUPLICATE_CSV.encode()), "text/csv")},
        headers=organizer,
    ).status_code == 200

    matcher = CountingMatcher()
    app.dependency_overrides[get_hr_matcher] = lambda: matcher
    body = client.post("/api/tournaments/cup/import/match", headers=organizer).json()

    assert matcher.asked == ["Jan Novak"]  # asked once, not twice
    assert body == {"matched": 2, "unmatched": 0, "reused": 0}
