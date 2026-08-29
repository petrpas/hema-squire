"""Deduplication of imported records.

Two lanes (owner decision: nothing with an identity merges silently):
- same hr_id: an LLM prepares a merge proposal; the pair queues for review.
- no hr_id: an LLM classifies candidate groups into surely (auto-merged),
  likely (queued), possible (discarded).

LLM outputs are cached decisions; organizer verdicts persist twice — as a
resolution decision (so rejected items leave the queue for good) and, on
accept, as a dedup_decision rule that performs the merge at replay time.
"""

import hashlib
import json
from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import rules
from app.importer import get_decision, store_decision
from app.llm import get_model, llm_configured
from app.models import Fencer, Tournament
from app.rules import Row

if TYPE_CHECKING:
    from pydantic_ai.models import Model


class MergeProposal(BaseModel):
    fields: dict
    note: str


class ThreeBands(BaseModel):
    surely: list[list[str]] = []
    likely: list[list[str]] = []
    possible: list[list[str]] = []


class DedupLLM(Protocol):
    def propose_merge(self, records: list[dict], language: str) -> MergeProposal: ...

    def classify(self, records: list[dict]) -> ThreeBands: ...


_MERGE_PROMPT = """\
You are a data assistant for a HEMA tournament.
You will receive multiple registration records that belong to the same person,
sorted oldest first by registered_at.

First, check the notes for intent: a later record may explicitly be a correction
("correction of previous", "updated disciplines"). If so, treat its fields as
authoritative for what it mentions.

Default merge rules otherwise:
- name: the most complete / correctly spelled form
- registered_at: keep the earliest
- nationality, email, club, hr_id: prefer non-empty values
- disciplines, weapon_rentals: union across records
- afterparty: true if any record says so
- notes: concatenate non-empty notes with " | ", omitting correction meta-comments
- problems: note any inconsistencies between the records

Return `fields` — a JSON object with the merged values for exactly these keys:
name, nationality, email, club, hr_id, disciplines, weapon_rentals, afterparty,
notes, problems — and `note`, one sentence (language: {language}) explaining what
differed and what was decided.
"""

_CLASSIFY_PROMPT = """\
You are a data assistant for a HEMA tournament.
You will receive fencer registrations that do NOT have a HEMA Ratings ID, each
with a stable `id`. Identify groups that likely belong to the same person and
classify each group:

surely: identical or near-identical name AND at least one matching corroborating
field (nationality, club, email, or overlapping disciplines). Safe to auto-merge.

likely: same or similar name with fewer corroborating fields. Needs a human.

possible: vaguely similar names, no corroborating evidence. Prefer this over
"likely" to avoid false positives; these are silently discarded.

If a group fits no category, omit it. Every id may appear in at most one group.
Return the three lists of id groups.
"""


class LLMDedup:
    def __init__(self, model: Model):
        self._model = model

    def _agent(self, output_type, prompt: str):
        from pydantic_ai import Agent

        return Agent(
            model=self._model,
            output_type=output_type,
            system_prompt=prompt,
            retries=3,
        )

    def propose_merge(self, records: list[dict], language: str) -> MergeProposal:
        agent = self._agent(MergeProposal, _MERGE_PROMPT.format(language=language))
        result = agent.run_sync(
            f"```json\n{json.dumps(records, ensure_ascii=False)}\n```"
        )
        return result.output

    def classify(self, records: list[dict]) -> ThreeBands:
        agent = self._agent(ThreeBands, _CLASSIFY_PROMPT)
        result = agent.run_sync(
            f"```json\n{json.dumps(records, ensure_ascii=False)}\n```"
        )
        return result.output


def get_dedup_llm() -> DedupLLM | None:
    if not llm_configured():
        return None
    return LLMDedup(get_model())


MERGE_FIELDS = [
    "name", "nationality", "email", "club", "hr_id",
    "disciplines", "weapon_rentals", "afterparty", "notes", "problems",
]


def default_merge(records: list[Row]) -> dict:
    """v1's non-LLM merge rules; the prefill for queued no-id groups."""
    merged: dict = {}
    for field in ("name", "nationality", "email", "club", "hr_id"):
        values = [r.get(field) for r in records if r.get(field)]
        if field == "name":
            merged[field] = max(values, key=lambda v: len(str(v)), default=None)
        else:
            # records arrive oldest first: most recent explicit value wins
            merged[field] = values[-1] if values else None
    for field in ("disciplines", "weapon_rentals"):
        union: list = []
        for record in records:
            for item in record.get(field) or []:
                if item not in union:
                    union.append(item)
        merged[field] = union
    merged["afterparty"] = any(r.get("afterparty") for r in records)
    notes = [r.get("notes") for r in records if r.get("notes")]
    merged["notes"] = " | ".join(dict.fromkeys(notes)) or None
    merged["problems"] = None
    return merged


def group_key(row_ids: list[str]) -> str:
    canonical = "|".join(sorted(row_ids))
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def _record_view(row: Row) -> dict:
    view = {field: row.get(field) for field in MERGE_FIELDS}
    view["id"] = row["id"]
    view["registered_at"] = row.get("registered_at")
    return view


def _sorted_group(rows_by_id: dict[str, Row], ids: list[str]) -> list[Row]:
    members = [rows_by_id[i] for i in ids if i in rows_by_id]
    return sorted(members, key=lambda r: r.get("registered_at") or "")


def _work_units(session: Session, tournament: Tournament, rows: list[Row]) -> tuple[int, int]:
    """How many LLM questions this run will ask: one per undecided same-hr_id
    group, plus one for the classification of the no-id set when it has unseen
    rows in it. Returned as (groups, classifications)."""
    active = {r["id"]: r for r in rows if not r.get("_deleted")}
    by_hr: dict[int, list[Row]] = {}
    for row in active.values():
        if row.get("hr_id") is not None:
            by_hr.setdefault(row["hr_id"], []).append(row)
    groups = 0
    for members in by_hr.values():
        if len(members) < 2:
            continue
        key = group_key(sorted(r["id"] for r in members))
        if get_decision(session, tournament, "merge", key) is None:
            groups += 1

    no_id = [row for row in active.values() if row.get("hr_id") is None]
    unseen = [
        r for r in no_id if get_decision(session, tournament, "dedup_seen", r["id"]) is None
    ]
    classifications = 1 if len(no_id) >= 2 and unseen else 0
    return groups, classifications


def pending_count(session: Session, tournament: Tournament, rows: list[Row]) -> int:
    """What an operation's total counts — the questions to be asked, not the
    rows on the sheet (spec console-operations, Reused rows are not work)."""
    groups, classifications = _work_units(session, tournament, rows)
    return groups + classifications


def run_dedup(
    session: Session,
    tournament: Tournament,
    llm: DedupLLM,
    rows: list[Row],
    actor: Fencer,
    progress: Callable[[Session, int], None] | None = None,
) -> dict:
    """Prepare merge proposals for same-hr_id groups and classify no-id
    candidates. Surely groups auto-merge; everything else waits in the queue.

    `progress` commits, and is where the operation's count is raised — each
    question's decision and the count of it travel together (design D4).
    """
    commit = progress or (lambda session, _units: session.commit())
    active = {r["id"]: r for r in rows if not r.get("_deleted")}

    by_hr: dict[int, list[Row]] = {}
    for row in active.values():
        if row.get("hr_id") is not None:
            by_hr.setdefault(row["hr_id"], []).append(row)

    proposals = 0
    for members in by_hr.values():
        if len(members) < 2:
            continue
        members.sort(key=lambda r: r.get("registered_at") or "")
        ids = [r["id"] for r in members]
        key = group_key(ids)
        if get_decision(session, tournament, "merge", key) is not None:
            continue
        proposal = llm.propose_merge(
            [_record_view(r) for r in members], tournament.language
        )
        store_decision(
            session,
            tournament,
            "merge",
            key,
            {"rows": ids, "fields": proposal.fields, "note": proposal.note},
        )
        proposals += 1
        commit(session, 1)

    no_id = [row for row in active.values() if row.get("hr_id") is None]
    auto_merged = 0
    likely = 0
    # incrementality: the classifier runs only when rows it has never seen
    # exist; new rows may pair with old ones, so it re-reads the whole set
    unseen = [
        r for r in no_id
        if get_decision(session, tournament, "dedup_seen", r["id"]) is None
    ]
    if len(no_id) >= 2 and unseen:
        bands = llm.classify([_record_view(r) for r in no_id])
        store_decision(
            session,
            tournament,
            "dedup",
            group_key([r["id"] for r in no_id]),
            bands.model_dump(),
        )
        for row in no_id:
            store_decision(session, tournament, "dedup_seen", row["id"], {})
        for ids in bands.surely:
            members = _sorted_group(active, ids)
            if len(members) < 2:
                continue
            key = group_key([r["id"] for r in members])
            if get_decision(session, tournament, "dedup_resolution", key) is not None:
                continue
            _merge(session, tournament, actor, members, default_merge(members),
                   note="auto-merged (surely duplicate)")
            store_decision(session, tournament, "dedup_resolution", key,
                           {"accepted": True, "auto": True}, source="llm")
            auto_merged += 1
        likely = len(bands.likely)
        commit(session, 1)
    else:
        # no classification to do. The proposal loop above commits per proposal,
        # so there is nothing outstanding — this settles the session for the
        # run that made no proposals either.
        session.commit()

    return {"proposals": proposals, "auto_merged": auto_merged, "likely": likely}


def _merge(
    session: Session,
    tournament: Tournament,
    actor: Fencer,
    members: list[Row],
    fields: dict,
    note: str,
) -> None:
    primary, *absorbed = members
    rules.create_rule(
        session,
        tournament,
        actor,
        phase="dedup",
        kind="dedup_decision",
        target=primary["id"],
        payload={"absorb": [r["id"] for r in absorbed], "fields": fields, "note": note},
    )


def pending_queue(session: Session, tournament: Tournament, rows: list[Row]) -> list[dict]:
    """Decision queue: same-hr_id merge proposals and likely no-id groups the
    organizer has not resolved yet."""
    active = {r["id"]: r for r in rows if not r.get("_deleted")}
    queue: list[dict] = []

    from sqlalchemy import select

    from app.models import ImportDecision

    decisions = session.scalars(
        select(ImportDecision).where(
            ImportDecision.tournament_id == tournament.id,
            ImportDecision.kind.in_(["merge", "dedup"]),
        )
    ).all()

    def resolved(key: str) -> bool:
        return get_decision(session, tournament, "dedup_resolution", key) is not None

    for decision in decisions:
        if decision.kind == "merge":
            ids = decision.payload["rows"]
            members = _sorted_group(active, ids)
            if len(members) < 2 or resolved(decision.key):
                continue
            queue.append(
                {
                    "key": decision.key,
                    "kind": "same_id",
                    "rows": [_record_view(r) for r in members],
                    "fields": decision.payload["fields"],
                    "note": decision.payload["note"],
                }
            )
        else:
            for ids in ThreeBands(**decision.payload).likely:
                members = _sorted_group(active, ids)
                key = group_key([r["id"] for r in members])
                if len(members) < 2 or resolved(key):
                    continue
                queue.append(
                    {
                        "key": key,
                        "kind": "likely",
                        "rows": [_record_view(r) for r in members],
                        "fields": default_merge(members),
                        "note": "",
                    }
                )
    return queue


def decide(
    session: Session,
    tournament: Tournament,
    actor: Fencer,
    rows: list[Row],
    key: str,
    accept: bool,
    fields: dict | None,
    note: str | None,
) -> dict:
    item = next((i for i in pending_queue(session, tournament, rows) if i["key"] == key), None)
    if item is None:
        return {"status": "not_pending"}
    if accept:
        active = {r["id"]: r for r in rows if not r.get("_deleted")}
        members = _sorted_group(active, [r["id"] for r in item["rows"]])
        _merge(
            session,
            tournament,
            actor,
            members,
            fields if fields is not None else item["fields"],
            note if note is not None else (item["note"] or "merged by organizer"),
        )
    store_decision(
        session,
        tournament,
        "dedup_resolution",
        key,
        {"accepted": accept},
        source="organizer",
    )
    session.commit()
    return {"status": "merged" if accept else "rejected"}
