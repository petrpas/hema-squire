"""Deduplication of imported records.

Two lanes (owner decision: nothing with an identity merges silently):
- same hr_id: an LLM prepares a merge proposal; the pair queues for review.
- no hr_id: an LLM classifies candidate groups into surely (auto-merged),
  likely (queued), possible (discarded).

Every group the operation raises — the two queued lanes and the auto-merged one
— is a candidate the console lists with its verdict, so that a merge the machine
performed is stated and one action from being withdrawn.

LLM outputs are cached decisions. A verdict is recorded twice, and the two
records answer different questions: the `dedup_resolution` decision says who
decided and what they decided, and is what stops a run from acting on the group
again; the `dedup_decision` rule performs the merge at replay time, and is what
makes the group *merged*. Delete the rule and the group is unmerged and awaiting
a decision again, whatever the resolution remembers.
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


# What a group's member row states beside the fields a merge decides: the fixed
# number that names it, and the evidence register the console identifies it by
# (spec etl-console, HR identity in the phases after matching). The console
# renders a member from this alone, so what it needs is projected here rather
# than joined against the sheet (design D2).
VIEW_FIELDS = ["id", "number", "registered_at", "hr_name", "hr_nationality", "hr_club"]


def _record_view(row: Row) -> dict:
    view = {field: row.get(field) for field in MERGE_FIELDS}
    view.update({field: row.get(field) for field in VIEW_FIELDS})
    view["id"] = row["id"]
    return view


def _sorted_group(rows_by_id: dict[str, Row], ids: list[str]) -> list[Row]:
    members = [rows_by_id[i] for i in ids if i in rows_by_id]
    return sorted(members, key=lambda r: r.get("registered_at") or "")


def _group_members(rows_by_id: dict[str, Row], ids: list[str]) -> list[Row]:
    """A candidate group's surviving members, oldest first.

    `rows_by_id` is the table as it stands *before* any merge (design D2): a
    group merged long ago must still be able to show what it merged, and to
    offer each record's own values back when its conclusion is reopened. A
    deletion is not excluded that way — a row taken out of the table is no
    longer a duplicate of anything, and the group stands or falls on what is
    left (spec etl-console, Reversible row deletion).
    """
    members = [
        row
        for row in (rows_by_id[i] for i in ids if i in rows_by_id)
        if not row.get("_deleted")
    ]
    return sorted(members, key=lambda r: r.get("registered_at") or "")


def merge_rule_for(session: Session, tournament: Tournament, key: str):
    """The merge rule standing for a group, or None.

    A group is merged while its rule is live and not because a decision record
    says it was accepted: the rule is what performs the merge, and the
    manual-edits log can remove it (design D3). The rule identifies its group by
    the rows it names — target plus absorbed is the membership the key was
    hashed from — so nothing had to be written into the payload for this to be
    answerable about rules created before the question was asked.
    """
    for rule in rules.active_rules(session, tournament, "dedup_decision"):
        ids = [rule.target, *rule.payload.get("absorb", [])]
        if group_key(ids) == key:
            return rule
    return None


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


def _verdict(
    session: Session, tournament: Tournament, key: str
) -> tuple[str, str | None, dict | None]:
    """A group's verdict, whose it is, and the conclusion it stands on.

    Merged is read off the live rule and rejected off the resolution record: the
    two answer different questions — "is this merged right now?" and "has anyone
    decided this?" — and were one variable until they disagreed (design D3).
    Withdrawing the merge from the manual-edits log therefore returns the group
    to those awaiting a decision instead of settling it unmerged.
    """
    rule = merge_rule_for(session, tournament, key)
    resolution = get_decision(session, tournament, "dedup_resolution", key)
    if rule is not None:
        conclusion = {
            "fields": rule.payload.get("fields") or {},
            "note": rule.payload.get("note") or "",
        }
        return "merged", (resolution.source if resolution is not None else None), conclusion
    if resolution is not None and resolution.payload.get("accepted") is False:
        return "separate", resolution.source, None
    return "pending", None, None


def candidate_groups(session: Session, tournament: Tournament, rows: list[Row]) -> list[dict]:
    """Every candidate duplicate group the operation has raised, with its
    verdict — the whole of what the Deduplication phase shows (spec etl-console,
    Deduplication candidate review).

    All three lanes are here: same-hr_id proposals, and both bands the
    classifier acts on. The surely band is listed because it was merged, not
    despite it — a machine's verdict is stated and reversible, never silent
    (spec etl-console, The ledger idiom). The possible band is not listed: it
    was discarded to keep false positives off the screen.

    `rows` is the table replayed without its merges, so a settled group still
    states the records it merged (design D2).
    """
    by_id = {r["id"]: r for r in rows}
    groups: list[dict] = []

    from sqlalchemy import select

    from app.models import ImportDecision

    decisions = session.scalars(
        select(ImportDecision)
        .where(
            ImportDecision.tournament_id == tournament.id,
            ImportDecision.kind.in_(["merge", "dedup"]),
        )
        .order_by(ImportDecision.id)
    ).all()

    def group(key: str, kind: str, members: list[Row], fields: dict, note: str) -> dict:
        verdict, decided_by, conclusion = _verdict(session, tournament, key)
        return {
            "key": key,
            "kind": kind,
            "verdict": verdict,
            "decided_by": decided_by,
            "members": [_record_view(r) for r in members],
            "recommendation": {"fields": fields, "note": note},
            "conclusion": conclusion,
        }

    for decision in decisions:
        if decision.kind == "merge":
            members = _group_members(by_id, decision.payload["rows"])
            if len(members) < 2:
                continue
            groups.append(
                group(
                    decision.key,
                    "same_id",
                    members,
                    decision.payload["fields"],
                    decision.payload["note"],
                )
            )
            continue
        bands = ThreeBands(**decision.payload)
        for kind, band in (("surely", bands.surely), ("likely", bands.likely)):
            for ids in band:
                members = _group_members(by_id, ids)
                if len(members) < 2:
                    continue
                key = group_key([r["id"] for r in members])
                groups.append(group(key, kind, members, default_merge(members), ""))
    return groups


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
    """The organizer's verdict on a candidate group, whatever verdict it carried
    before (design D4).

    Total and idempotent: a group already merged can be kept separate, one kept
    separate can be merged, and a merged group's conclusion can be corrected and
    confirmed again. Re-confirming updates the standing rule rather than adding
    a second one — two merges absorbing the same rows would be one decision
    reported twice and undone once.
    """
    group = next(
        (g for g in candidate_groups(session, tournament, rows) if g["key"] == key), None
    )
    if group is None:
        return {"status": "unknown_group"}
    rule = merge_rule_for(session, tournament, key)
    if accept:
        ids = [member["id"] for member in group["members"]]
        payload = {
            "absorb": ids[1:],
            "fields": fields if fields is not None else group["recommendation"]["fields"],
            "note": note
            if note is not None
            else (group["recommendation"]["note"] or "merged by organizer"),
        }
        if rule is not None:
            rules.update_rule(session, rule, actor, payload)
        else:
            rules.create_rule(
                session,
                tournament,
                actor,
                phase="dedup",
                kind="dedup_decision",
                target=ids[0],
                payload=payload,
            )
    elif rule is not None:
        rules.delete_rule(session, rule, actor)
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
