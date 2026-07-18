"""LLM fuzzy-matching of imported fencers against the HEMA Ratings index.

Matches are cached decisions keyed by the fencer's identity fingerprint
(name|club), so a rerun never re-asks about an already-matched fencer. The
organizer reviews verdicts in the Matching phase; corrections persist as
match_resolution rules and always win over the cached LLM proposal.
"""

import hashlib
import json
from typing import Protocol

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.hr_index import HRIndex, HRProfile
from app.importer import get_decision, store_decision
from app.models import Tournament


class HRMatchResult(BaseModel):
    name: str
    club: str | None
    hr_id: int | None
    matched_name: str | None
    matched_club: str | None
    nationality: str | None


class HRMatcher(Protocol):
    def match(
        self, fencers: list[dict], candidates: list[HRProfile]
    ) -> list[HRMatchResult]: ...


_SYSTEM_PROMPT = """\
You are a data assistant for HEMA (Historical European Martial Arts) tournaments.
You will receive:
1. A list of registered unmatched fencers (name, club, nationality) that need their
   HEMA Ratings ID found.
2. A pre-filtered list of the most likely candidate fighters from hemaratings.com:
   id;name;nationality;club (one per line). This is NOT the complete HR database —
   if no good match appears, set hr_id to null.

For each unmatched fencer, fuzzy-match against the candidates using name similarity
(handle transliterations, nicknames, diacritics: "Honza" <-> "Jan", "Blažek" <->
"Blazek"), club as a secondary signal, nationality as a tertiary signal.
Only set hr_id if you are confident (>80%) it is the same person.

Output per fencer:
- name, club: echo back exactly as given (used to key results)
- hr_id: matched HR id, or null
- matched_name: canonical name from the HR list, or null
- matched_club: HR club if the registration club is blank or an alternate spelling
  of it; keep the registration club if they are clearly different organizations
- nationality: keep the registration's if provided, otherwise take HR's
"""


class _MatchBatch(BaseModel):
    matches: list[HRMatchResult]


class LLMHRMatcher:
    def __init__(self, model: str):
        self._model = model

    def match(
        self, fencers: list[dict], candidates: list[HRProfile]
    ) -> list[HRMatchResult]:
        from pydantic_ai import Agent
        from pydantic_ai.settings import ModelSettings

        agent = Agent(
            model=self._model,
            model_settings=ModelSettings(temperature=0.0),
            output_type=_MatchBatch,
            system_prompt=_SYSTEM_PROMPT,
            retries=3,
        )
        candidate_lines = "\n".join(
            f"{p.hr_id};{p.name};{p.nationality or ''};{p.club or ''}" for p in candidates
        )
        result = agent.run_sync(
            f"Unmatched fencers:\n```json\n{json.dumps(fencers, ensure_ascii=False)}\n```\n\n"
            f"Candidate fighters:\n```\n{candidate_lines}\n```\n\n"
            f"Return exactly {len(fencers)} results in the same order."
        )
        return result.output.matches


def get_hr_matcher() -> HRMatcher | None:
    if not settings.anthropic_api_key:
        return None
    import os

    os.environ.setdefault("ANTHROPIC_API_KEY", settings.anthropic_api_key)
    return LLMHRMatcher(settings.llm_model)


def identity_key(name: str | None, club: str | None) -> str:
    canonical = f"{(name or '').strip().lower()}|{(club or '').strip().lower()}"
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def candidate_profiles(index: HRIndex, fencers: list[dict]) -> list[HRProfile]:
    """Pre-filter the fighters index by name tokens; the LLM sees the union."""
    profiles: dict[int, HRProfile] = {}
    for fencer in fencers:
        tokens = [fencer.get("name") or ""] + (fencer.get("name") or "").split()
        for token in tokens:
            if len(token.strip()) < 3:
                continue
            for profile in index.search(token):
                profiles[profile.hr_id] = profile
    return list(profiles.values())


def run_matching(
    session: Session,
    tournament: Tournament,
    matcher: HRMatcher,
    index: HRIndex,
    rows: list[dict],
) -> dict:
    """Match every imported row without an hr_id and without a cached verdict.

    `rows` are replayed sheet rows (imp:* only) — replay first means organizer
    edits and confirmed resolutions are respected, not re-litigated.
    """
    pending = [
        row
        for row in rows
        if row.get("hr_id") is None
        and not row.get("_deleted")
        and row.get("match_verdict") not in ("confirmed", "none_found")
        and get_decision(
            session, tournament, "hr_match", identity_key(row.get("name"), row.get("club"))
        )
        is None
        and row.get("name")
    ]
    if not pending:
        return {"matched": 0, "unmatched": 0, "reused": len(rows) - len(pending)}

    fencers = [
        {
            "name": row["name"],
            "club": row.get("club"),
            "nationality": row.get("nationality"),
        }
        for row in pending
    ]
    candidates = candidate_profiles(index, fencers)
    results = matcher.match(fencers, candidates)

    matched = 0
    for row, result in zip(pending, results, strict=True):
        key = identity_key(row.get("name"), row.get("club"))
        store_decision(session, tournament, "hr_match", key, result.model_dump())
        if result.hr_id is not None:
            matched += 1
    session.commit()
    return {
        "matched": matched,
        "unmatched": len(pending) - matched,
        "reused": len(rows) - len(pending),
    }
