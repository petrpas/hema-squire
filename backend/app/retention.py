"""Storage limitation: what ages out, and when (spec data-retention).

Two kinds of period. Finished mail and expired tokens are plain deletes by age.
A tournament, twelve months after its date, loses the personal details nobody
needs once it is long over: payer text on its bank rows, contact addresses and
free text on its registrations, manual rows and imported rows. It keeps every
figure money is reconciled from and every name a roster lists — rosters are
outside any period by decision.

Each tournament is pruned once, in its own transaction, and stamped. Nothing
here is reversible, so the whole pass is gated by
`settings.retention_writes_enabled`: off, it does the same work, logs what it
would have changed and rolls back (design data-retention, Migration Plan).
"""

import logging
import re
from collections import Counter
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    BankTransaction,
    ImportDecision,
    ImportedRow,
    ManualRow,
    OutgoingMail,
    PasswordReset,
    PendingSignup,
    Registration,
    Rule,
    RuleJournalEntry,
    Tournament,
)

logger = logging.getLogger(__name__)

MAIL_DAYS = 30

# bank text blanked on a pruned tournament (design D2). Amount, currency, date,
# VS, status, the matched registration and `external_id` stay: credits and
# revenue read them, and `external_id` is what keeps a later statement import
# from bringing the row back
_BANK_TEXT = (
    "payer_name",
    "payer_account",
    "message",
    "named_person",
    "user_identification",
    "comment",
    "specification",
    "specific_symbol",
)

# the fields of a fencer-list row that hold an address or free text. Wherever a
# stored record names one of them — a parse result, a rule's edit, a merge's
# fields — its value goes (design D3)
_FREE_FIELDS = frozenset({"email", "contact_email", "notes", "accommodation"})

_ADDRESS = re.compile(r"[^\s@<>()\[\],;:\"']+@[^\s@<>()\[\],;:\"']+\.[A-Za-z]{2,}")


def _now() -> datetime:
    return datetime.now(UTC)


def cutoff(today: date) -> date:
    """The latest tournament date that is twelve months old on `today`."""
    try:
        return today.replace(year=today.year - 1)
    except ValueError:  # 29 February
        return today.replace(year=today.year - 1, day=28)


# ------------------------------------------------------------------ by age


def prune_by_age(session: Session, now: datetime) -> Counter[str]:
    """Delete finished mail 30 days on, and every expired signup and reset.
    A message still waiting for delivery is neither sent nor failed, so the
    age test never reaches it (spec data-retention, Waiting message stays)."""
    aged = now - timedelta(days=MAIL_DAYS)
    counts: Counter[str] = Counter()
    for name, statement in (
        (
            "mail",
            delete(OutgoingMail).where(
                or_(OutgoingMail.sent_at <= aged, OutgoingMail.failed_at <= aged)
            ),
        ),
        ("signups", delete(PendingSignup).where(PendingSignup.expires_at <= now)),
        ("resets", delete(PasswordReset).where(PasswordReset.expires_at <= now)),
    ):
        # a DML statement returns a CursorResult, which `execute` types as the
        # plain Result; read the count the way app.outgoing does
        counts[name] = getattr(session.execute(statement), "rowcount", 0)
    return counts


# ------------------------------------------------------------ by tournament


def _scrub(value: object, drop: frozenset[str]) -> tuple[object, bool]:
    """`value` with every address and every free-text field taken out.

    A key naming a free field loses its value; so does the `value`/`base` of an
    edit whose `field` names one. A string equal to one of `drop` becomes empty,
    and any address inside a string is cut out of it. Whether anything changed
    comes back with it, so an untouched JSON column is not rewritten."""
    if isinstance(value, dict):
        edits_free_field = value.get("field") in _FREE_FIELDS
        out: dict[object, object] = {}
        changed = False
        for key, item in value.items():
            if (key in _FREE_FIELDS or (edits_free_field and key in ("value", "base"))) and (
                item not in (None, "")
            ):
                out[key] = None
                changed = True
                continue
            out[key], hit = _scrub(item, drop)
            changed = changed or hit
        return out, changed
    if isinstance(value, list):
        items: list[object] = []
        changed = False
        for item in value:
            new, hit = _scrub(item, drop)
            items.append(new)
            changed = changed or hit
        return items, changed
    if isinstance(value, str):
        if value.strip() and value.strip() in drop:
            return "", True
        stripped = _ADDRESS.sub("", value)
        return stripped, stripped != value
    return value, False


def _free_values(record: object) -> frozenset[str]:
    """The non-empty free-field values of a parse record: what the cells of the
    raw row they were read from held, as near as can be known without a
    column mapping (design D3)."""
    if not isinstance(record, dict):
        return frozenset()
    return frozenset(
        value.strip()
        for key, value in record.items()
        if key in _FREE_FIELDS and isinstance(value, str) and value.strip()
    )


def _prune_bank(session: Session, tournament: Tournament) -> int:
    count = 0
    for row in session.scalars(
        select(BankTransaction).where(BankTransaction.tournament_id == tournament.id)
    ):
        changed = bool(row.rejected_fencer_ids)
        row.rejected_fencer_ids = []
        for column in _BANK_TEXT:
            if getattr(row, column) is not None:
                setattr(row, column, None)
                changed = True
        count += changed
    return count


def _prune_registrations(session: Session, tournament: Tournament) -> int:
    count = 0
    for registration in session.scalars(
        select(Registration).where(Registration.tournament_id == tournament.id)
    ):
        if registration.contact_email or registration.notes or registration.accommodation:
            registration.contact_email = None
            registration.notes = None
            registration.accommodation = None
            count += 1
    return count


def _prune_manual_rows(session: Session, tournament: Tournament) -> int:
    count = 0
    for row in session.scalars(select(ManualRow).where(ManualRow.tournament_id == tournament.id)):
        if row.email or row.notes:
            row.email = None
            row.notes = None
            count += 1
    return count


def _prune_imports(session: Session, tournament: Tournament) -> tuple[int, int]:
    """Imported rows and the decisions read from them. A row keeps its `key`,
    the fingerprint of the cells as uploaded, so uploading the same file again
    still finds it and adds nothing; it is never rehashed."""
    parses = {
        decision.key: decision
        for decision in session.scalars(
            select(ImportDecision).where(
                ImportDecision.tournament_id == tournament.id, ImportDecision.kind == "parse"
            )
        )
    }
    rows = 0
    for row in session.scalars(
        select(ImportedRow).where(ImportedRow.tournament_id == tournament.id)
    ):
        parse = parses.get(row.key)
        drop = _free_values(parse.payload) if parse is not None else frozenset()
        raw, changed = _scrub(row.raw, drop)
        if changed and isinstance(raw, dict):
            row.raw = raw
            rows += 1
    decisions = 0
    for decision in session.scalars(
        select(ImportDecision).where(ImportDecision.tournament_id == tournament.id)
    ):
        payload, changed = _scrub(decision.payload, frozenset())
        if changed and isinstance(payload, dict):
            decision.payload = payload
            decisions += 1
    return rows, decisions


def _prune_rules(session: Session, tournament: Tournament) -> int:
    """A rule that wrote an address or a note onto a row would write it back on
    every replay, so its payload loses it too, and so does the journal's
    snapshot of it."""
    count = 0
    for rule in session.scalars(select(Rule).where(Rule.tournament_id == tournament.id)):
        payload, changed = _scrub(rule.payload, frozenset())
        if changed and isinstance(payload, dict):
            rule.payload = payload
            count += 1
    for entry in session.scalars(
        select(RuleJournalEntry).where(RuleJournalEntry.tournament_id == tournament.id)
    ):
        content, changed = _scrub(entry.content, frozenset())
        if changed and isinstance(content, dict):
            entry.content = content
            count += 1
    return count


def prune_tournament(session: Session, tournament: Tournament, now: datetime) -> Counter[str]:
    """Remove one tournament's personal details and stamp it (design D1–D3)."""
    counts: Counter[str] = Counter()
    counts["bank_rows"] = _prune_bank(session, tournament)
    counts["registrations"] = _prune_registrations(session, tournament)
    counts["manual_rows"] = _prune_manual_rows(session, tournament)
    counts["imported_rows"], counts["decisions"] = _prune_imports(session, tournament)
    counts["rules"] = _prune_rules(session, tournament)
    tournament.personal_data_pruned_at = now
    return counts


def due_tournaments(session: Session, today: date) -> list[int]:
    """Ids of the tournaments twelve months past their date and not yet pruned.
    Every tournament, whoever keeps its registrations and whether or not it was
    ever published: a period does not depend on how the data arrived."""
    return list(
        session.scalars(
            select(Tournament.id)
            .where(
                Tournament.date <= cutoff(today),
                Tournament.personal_data_pruned_at.is_(None),
            )
            .order_by(Tournament.id)
        ).all()
    )


# ---------------------------------------------------------------- the pass


def _finish(session: Session, what: str, counts: Counter[str]) -> None:
    summary = ", ".join(f"{name} {count}" for name, count in sorted(counts.items()))
    if settings.retention_writes_enabled:
        session.commit()
        logger.info("retention: %s: %s", what, summary)
    else:
        session.rollback()
        logger.info("retention (writes disabled, rolled back): %s: would change %s", what, summary)


def run_pass(session: Session, now: datetime | None = None) -> None:
    """The scheduler's retention pass. The age deletes go first, then each due
    tournament in its own transaction, so one that fails is rolled back alone
    and is tried again by the next pass (design D1)."""
    moment = now or _now()
    try:
        _finish(session, "by age", prune_by_age(session, moment))
    except Exception:
        session.rollback()
        logger.exception("retention by age failed")
    for tournament_id in due_tournaments(session, moment.date()):
        tournament = session.get(Tournament, tournament_id)
        if tournament is None:
            continue
        slug = tournament.slug
        try:
            _finish(session, slug, prune_tournament(session, tournament, moment))
        except Exception:
            session.rollback()
            logger.exception("retention failed for %s", slug)
