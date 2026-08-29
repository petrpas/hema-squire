"""LLM fuzzy-matching of imported fencers against the HEMA Ratings index.

Matches are cached decisions keyed by the fencer's identity fingerprint
(name|club), so a rerun never re-asks about an already-matched fencer. The
organizer reviews verdicts in the Matching phase; corrections persist as
match_resolution rules and always win over the cached LLM proposal.
"""

import hashlib
import json
from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.hr_index import HRIndex, HRProfile, fold
from app.importer import get_decision, store_decision
from app.llm import get_model, llm_configured
from app.models import Tournament

if TYPE_CHECKING:
    from pydantic_ai.models import Model


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


# One result per fencer is ~70 output tokens; a whole import at once overruns
# the model's output budget and comes back truncated, so the roster goes out in
# batches the way parsing does (importer.PARSE_BATCH_SIZE).
MATCH_BATCH_SIZE = 20
MATCH_MAX_TOKENS = 8192


def _batch_candidates(
    batch: list[dict], candidates: list[HRProfile]
) -> list[HRProfile]:
    """The slice of the pre-filtered union that shares a name token with this
    batch — the other batches' candidates are noise in this prompt."""
    tokens = {
        token
        for fencer in batch
        for token in fold(fencer.get("name") or "").split()
        if len(token) >= 3
    }
    return [
        profile
        for profile in candidates
        if any(token in fold(profile.name) for token in tokens)
    ]


class LLMHRMatcher:
    def __init__(self, model: Model, batch_size: int = MATCH_BATCH_SIZE):
        self._model = model
        self._batch_size = batch_size

    def match(
        self, fencers: list[dict], candidates: list[HRProfile]
    ) -> list[HRMatchResult]:
        from pydantic_ai import Agent
        from pydantic_ai.settings import ModelSettings

        agent = Agent(
            model=self._model,
            output_type=_MatchBatch,
            system_prompt=_SYSTEM_PROMPT,
            retries=3,
            model_settings=ModelSettings(max_tokens=MATCH_MAX_TOKENS),
        )
        results: list[HRMatchResult] = []
        for start in range(0, len(fencers), self._batch_size):
            batch = fencers[start : start + self._batch_size]
            candidate_lines = "\n".join(
                f"{p.hr_id};{p.name};{p.nationality or ''};{p.club or ''}"
                for p in _batch_candidates(batch, candidates)
            )
            result = agent.run_sync(
                f"Unmatched fencers:\n```json\n{json.dumps(batch, ensure_ascii=False)}\n```\n\n"
                f"Candidate fighters:\n```\n{candidate_lines}\n```\n\n"
                f"Return exactly {len(batch)} results in the same order."
            )
            results.extend(result.output.matches)
        return results


def get_hr_matcher() -> HRMatcher | None:
    if not llm_configured():
        return None
    return LLMHRMatcher(get_model())


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


def _pending_rows(session: Session, tournament: Tournament, rows: list[dict]) -> list[dict]:
    """The rows this run will actually ask about: no hr_id, not removed, no
    verdict already settled, and no cached decision for their identity."""
    return [
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


def pending_count(session: Session, tournament: Tournament, rows: list[dict]) -> int:
    """What an operation's total counts — rows to be asked about, not rows on
    the sheet (spec console-operations, Reused rows are not work)."""
    return len(_pending_rows(session, tournament, rows))


def run_matching(
    session: Session,
    tournament: Tournament,
    matcher: HRMatcher,
    index: HRIndex,
    rows: list[dict],
    progress: Callable[[Session, int], None] | None = None,
) -> dict:
    """Match every imported row without an hr_id and without a cached verdict.

    `rows` are replayed sheet rows (imp:* only) — replay first means organizer
    edits and confirmed resolutions are respected, not re-litigated.

    `progress` commits, and is where the operation's count is raised — the
    decision and the count of it travel together (design D4).
    """
    commit = progress or (lambda session, _units: session.commit())
    pending = _pending_rows(session, tournament, rows)
    if not pending:
        return {"matched": 0, "unmatched": 0, "reused": len(rows) - len(pending)}

    # A verdict is cached per identity, so rows that share a name and club are
    # one question, asked once and stored once — an import with the same fencer
    # twice is what deduplication is for, not a reason to pay for the match
    # twice or to write the same decision key twice.
    by_identity: dict[str, list[dict]] = {}
    for row in pending:
        by_identity.setdefault(
            identity_key(row.get("name"), row.get("club")), []
        ).append(row)

    fencers = [
        {
            "name": same[0]["name"],
            "club": same[0].get("club"),
            "nationality": same[0].get("nationality"),
        }
        for same in by_identity.values()
    ]
    candidates = candidate_profiles(index, fencers)
    results = matcher.match(fencers, candidates)

    matched = 0
    for (key, same), result in zip(by_identity.items(), results, strict=True):
        store_decision(session, tournament, "hr_match", key, result.model_dump())
        if result.hr_id is not None:
            matched += len(same)
        # the rows this identity stands for, so the count is in rows the
        # organizer recognises rather than in questions asked
        commit(session, len(same))
    return {
        "matched": matched,
        "unmatched": len(pending) - matched,
        "reused": len(rows) - len(pending),
    }
