"""Account deletion and identity erasure (spec `account-deletion`).

A deletion is asked for with the password, waits seven days and then turns
the account into the credential-less fencer record the schema already knows
(design D1): no address, no password, no sessions, no audit trail. What stays
is what a held roster needs — the name, HR ID, club and nationality — and
only where a held roster lists the person (design D2). Every copy of the
account's addresses that can be found by its exact value is removed (design
D5); a name-only copy is the Admin's to erase, with a person deciding (D7).

Everything one execution does happens in the caller's transaction, so an
account is either wholly deleted or untouched. The erasure log records that
it happened, without anything that says who, so a restore can do it again
(design D8)."""

import logging
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Literal

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.auth import is_deployment_owner, verify_password
from app.availability import live_registration
from app.config import settings
from app.emails import mail_language
from app.i18n import format_date, format_money, t
from app.mail import Mailer, build_message
from app.models import (
    AccountErasure,
    Fencer,
    FencerProfileAudit,
    ImportDecision,
    ImportedRow,
    ManualPayment,
    ManualRow,
    OrganizerRequest,
    OutgoingMail,
    PasswordReset,
    PaymentCredit,
    PaymentEvent,
    PaymentWaiver,
    Registration,
    Role,
    Rule,
    RuleJournalEntry,
    Tournament,
    TournamentOrganizer,
)

logger = logging.getLogger(__name__)

GRACE = timedelta(days=7)

# What a record reads as once nothing justifies keeping its name (design D2).
# Stored, so every surface that prints a fencer's name prints this without
# knowing about deletion; the admin list translates it by the record's
# `deleted_at`.
DELETED_LABEL = "Smazaný účet"

ACCOUNT = "account"
IDENTITY = "identity"

# the fields a held roster shows of a person, and the only ones a rule may
# correct about them
IDENTITY_FIELDS = ("name", "hr_id", "club", "nationality")


def _today() -> date:
    """The boundary between held and not yet held: the public list's, in UTC
    (spec `day-boundaries`). A tournament dated today is not yet held."""
    return datetime.now(UTC).date()


# ------------------------------------------------------------------ impact


BlockerKind = Literal["owner", "last_admin", "deployment_owner"]


@dataclass(frozen=True)
class Blocker:
    """Why a deletion cannot go ahead: what the account still answers for."""

    kind: BlockerKind
    tournaments: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Cancelled:
    """A registration execution will cancel, and what was credited on it."""

    tournament: str
    tournament_date: date
    vs: int | None
    credited: list[tuple[int, str]]


@dataclass(frozen=True)
class Impact:
    cancelled: list[Cancelled]
    held_rosters: int
    blockers: list[Blocker]


def blockers(session: Session, fencer: Fencer) -> list[Blocker]:
    """What the account must hand over before it can go (spec, Deletion is
    refused while the account holds responsibility)."""
    found: list[Blocker] = []
    if is_deployment_owner(fencer):
        found.append(Blocker("deployment_owner"))
    owned = session.scalars(
        select(Tournament.display_name)
        .where(Tournament.owner_id == fencer.id, Tournament.cancelled_at.is_(None))
        .order_by(Tournament.date)
    ).all()
    if owned:
        found.append(Blocker("owner", list(owned)))
    if fencer.role is Role.ADMIN:
        others = session.scalar(
            select(func.count())
            .select_from(Fencer)
            .where(Fencer.role == Role.ADMIN, Fencer.id != fencer.id, Fencer.deleted_at.is_(None))
        )
        if not others:
            found.append(Blocker("last_admin"))
    return found


def _future_registrations(session: Session, fencer: Fencer) -> list[Registration]:
    return list(
        session.scalars(
            select(Registration)
            .join(Tournament, Tournament.id == Registration.tournament_id)
            .where(
                Registration.fencer_id == fencer.id,
                Tournament.date >= _today(),
                live_registration(),
            )
            .options(selectinload(Registration.credits), selectinload(Registration.tournament))
            .order_by(Tournament.date, Registration.id)
        ).all()
    )


def _held_tournament_count(session: Session, fencer: Fencer) -> int:
    return (
        session.scalar(
            select(func.count(func.distinct(Registration.tournament_id)))
            .join(Tournament, Tournament.id == Registration.tournament_id)
            .where(
                Registration.fencer_id == fencer.id,
                Tournament.date < _today(),
                live_registration(),
            )
        )
        or 0
    )


def _credited(registration: Registration) -> list[tuple[int, str]]:
    """Live credits by currency, in the order the currencies first arrived."""
    totals: dict[str, int] = {}
    for credit in sorted(registration.credits, key=lambda credit: credit.id):
        if credit.reversed_at is None:
            currency = credit.currency.value
            totals[currency] = totals.get(currency, 0) + credit.amount_cents
    return [(cents, currency) for currency, cents in totals.items() if cents]


def impact(session: Session, fencer: Fencer) -> Impact:
    """What a deletion would do, stated before anyone commits to it."""
    return Impact(
        cancelled=[
            Cancelled(
                tournament=registration.tournament.display_name,
                tournament_date=registration.tournament.date,
                vs=registration.vs,
                credited=_credited(registration),
            )
            for registration in _future_registrations(session, fencer)
        ],
        held_rosters=_held_tournament_count(session, fencer),
        blockers=blockers(session, fencer),
    )


# ----------------------------------------------------------- request, withdraw


def effective_on(fencer: Fencer) -> datetime | None:
    """When a pending deletion executes; None without one."""
    requested = fencer.deletion_requested_at
    if requested is None:
        return None
    if requested.tzinfo is None:  # SQLite hands timestamps back naive, in UTC
        requested = requested.replace(tzinfo=UTC)
    return requested + GRACE


def request_deletion(session: Session, fencer: Fencer, password: str, mailer: Mailer) -> None:
    """Record a deletion request confirmed by the password, and say when it
    takes effect. Refused outright while the account answers for something."""
    if fencer.password_hash is None or not verify_password(password, fencer.password_hash):
        raise HTTPException(status_code=403, detail="wrong_password")
    if blockers(session, fencer):
        raise HTTPException(status_code=409, detail="deletion_blocked")
    fencer.deletion_requested_at = datetime.now(UTC)
    when = effective_on(fencer)
    if fencer.email is not None and when is not None:
        lang = fencer.language
        mailer.send(
            build_message(
                fencer.email,
                settings.email_sender,
                t("email.accountDeletion.requested.subject", lang),
                t(
                    "email.accountDeletion.requested.body",
                    lang,
                    name=fencer.display_name,
                    date=format_date(when.date(), lang),
                ),
            )
        )


def withdraw_deletion(fencer: Fencer, mailer: Mailer) -> None:
    """Take a pending request back. Nothing else was touched, so nothing else
    needs undoing."""
    if fencer.deletion_requested_at is None:
        raise HTTPException(status_code=409, detail="no_deletion_pending")
    fencer.deletion_requested_at = None
    if fencer.email is not None:
        lang = fencer.language
        mailer.send(
            build_message(
                fencer.email,
                settings.email_sender,
                t("email.accountDeletion.withdrawn.subject", lang),
                t("email.accountDeletion.withdrawn.body", lang, name=fencer.display_name),
            )
        )


# ----------------------------------------------------------------- execution


def _addresses(session: Session, fencer: Fencer) -> set[str]:
    """Every address the account has held: the current one and each the audit
    trail saw it change from or to. Read before the trail is deleted."""
    found = {fencer.email} if fencer.email else set()
    for old, new in session.execute(
        select(FencerProfileAudit.old_value, FencerProfileAudit.new_value).where(
            FencerProfileAudit.fencer_id == fencer.id, FencerProfileAudit.field == "email"
        )
    ).tuples():
        found.update(value for value in (old, new) if value)
    return {address.strip().casefold() for address in found}


def _is_address(value: object, addresses: set[str]) -> bool:
    return isinstance(value, str) and value.strip().casefold() in addresses


def _redact(value: object, addresses: set[str]) -> tuple[object, bool]:
    """A JSON value with every string that is wholly one of the addresses
    replaced by null, and whether anything was. Exact values only: an address
    inside a sentence is not found, by design (D5)."""
    if _is_address(value, addresses):
        return None, True
    if isinstance(value, dict):
        changed = False
        out: dict[object, object] = {}
        for key, item in value.items():
            out[key], hit = _redact(item, addresses)
            changed = changed or hit
        return out, changed
    if isinstance(value, list):
        changed = False
        items: list[object] = []
        for item in value:
            new, hit = _redact(item, addresses)
            items.append(new)
            changed = changed or hit
        return items, changed
    return value, False


def _strip_labels(text: str, addresses: set[str]) -> str:
    """`Name <address>` becomes `Name`: the journal keeps who did it, and only
    the address goes."""
    for address in addresses:
        text = re.sub(r"\s*<" + re.escape(address) + ">", "", text, flags=re.IGNORECASE)
    return text


def _redact_copies(session: Session, fencer: Fencer, addresses: set[str]) -> None:
    """Remove the addresses from every place they can be found by value
    (design D5). Another person's seat that uses one of them as its contact
    address keeps it: it is that seat's working contact."""
    if not addresses:
        return
    for model, column in (
        (ImportedRow, "raw"),
        (Rule, "payload"),
        (RuleJournalEntry, "content"),
        (ImportDecision, "payload"),
    ):
        for row in session.scalars(select(model)):
            new, changed = _redact(getattr(row, column), addresses)
            if changed:
                setattr(row, column, new)
    for manual in session.scalars(select(ManualRow).where(ManualRow.email.is_not(None))):
        if _is_address(manual.email, addresses):
            manual.email = None
    for payment in session.scalars(select(ManualPayment)):
        payment.recorded_by = _strip_labels(payment.recorded_by, addresses)
    for credit in session.scalars(
        select(PaymentCredit).where(PaymentCredit.reversed_by.is_not(None))
    ):
        if credit.reversed_by is not None:
            credit.reversed_by = _strip_labels(credit.reversed_by, addresses)
    for waiver in session.scalars(select(PaymentWaiver)):
        waiver.granted_by = _strip_labels(waiver.granted_by, addresses)
        if waiver.revoked_by is not None:
            waiver.revoked_by = _strip_labels(waiver.revoked_by, addresses)
    for event in session.scalars(select(PaymentEvent).where(PaymentEvent.detail.is_not(None))):
        if event.detail is not None:
            event.detail = _strip_labels(event.detail, addresses)
    for registration in session.scalars(
        select(Registration).where(Registration.fencer_id == fencer.id)
    ):
        registration.notes = None
        registration.accommodation = None
        registration.contact_email = None
    # every message addressed to them, waiting, failed or sent: its body and
    # its delivery error carry the address too
    for mail in session.scalars(select(OutgoingMail)):
        if _is_address(mail.recipient, addresses):
            session.delete(mail)


def _notify_organizers(
    session: Session,
    cancelled: Iterable[tuple[Registration, list[tuple[int, str]]]],
    name: str,
    mailer: Mailer,
) -> None:
    """Tell each owner whose entry went, and what had been paid on it, so they
    can settle it outside Squire (spec, Registrations not yet held are
    cancelled and the organizer is told)."""
    for registration, credited in cancelled:
        tournament = registration.tournament
        owner = session.get(Fencer, tournament.owner_id) if tournament.owner_id else None
        if owner is None or owner.email is None:
            continue
        lang = mail_language(tournament, owner)
        paid = (
            ", ".join(
                format_money(Decimal(cents) / 100, currency, lang) for cents, currency in credited
            )
            if credited
            else t("email.accountDeletion.organizerNotice.nothingPaid", lang)
        )
        mailer.send(
            build_message(
                owner.email,
                settings.email_sender,
                t(
                    "email.accountDeletion.organizerNotice.subject",
                    lang,
                    tournament=tournament.display_name,
                ),
                t(
                    "email.accountDeletion.organizerNotice.body",
                    lang,
                    name=name,
                    tournament=tournament.display_name,
                    vs=registration.vs if registration.vs is not None else "—",
                    paid=paid,
                ),
            )
        )


def _blank_identity(fencer: Fencer) -> None:
    fencer.display_name = DELETED_LABEL
    fencer.hr_id = None
    fencer.club = None
    fencer.nationality = None


def _apply(session: Session, fencer: Fencer) -> list[tuple[Registration, list[tuple[int, str]]]]:
    """What every execution does to the data, whoever runs it: cancel the
    entries not yet held, scrub the addresses and the login, keep the identity
    only where a held roster lists it, log the erasure. Returns the cancelled
    registrations with what was credited on each, for the organizers' notice."""
    # a registration router is where cancelling lives; importing it at module
    # level would make the routers and the scheduler import each other
    from app.routers.registrations import cancel

    now = datetime.now(UTC)
    addresses = _addresses(session, fencer)
    cancelled: list[tuple[Registration, list[tuple[int, str]]]] = []
    for registration in _future_registrations(session, fencer):
        cancelled.append((registration, _credited(registration)))
        cancel(registration, registration.tournament, now)
    keeps_name = _held_tournament_count(session, fencer) > 0

    _redact_copies(session, fencer, addresses)
    session.execute(delete(FencerProfileAudit).where(FencerProfileAudit.fencer_id == fencer.id))
    session.execute(delete(PasswordReset).where(PasswordReset.fencer_id == fencer.id))
    session.execute(delete(OrganizerRequest).where(OrganizerRequest.fencer_id == fencer.id))
    session.execute(delete(TournamentOrganizer).where(TournamentOrganizer.fencer_id == fencer.id))

    fencer.email = None
    fencer.password_hash = None
    fencer.language = "en"
    fencer.role = Role.FENCER
    fencer.sessions_valid_from = now
    fencer.organizer_terms_version = None
    fencer.organizer_terms_accepted_at = None
    fencer.deletion_requested_at = None
    fencer.deleted_at = now
    if not keeps_name:
        _blank_identity(fencer)
    session.add(AccountErasure(fencer_id=fencer.id, kind=ACCOUNT, created_at=now))
    return cancelled


def execute(session: Session, fencer: Fencer, mailer: Mailer) -> bool:
    """Carry out a requested deletion; False, touching nothing, where a blocker
    has arisen since the request (design D3). Idempotent: a record already
    deleted is left as it is. The caller commits."""
    if fencer.deleted_at is not None:
        return True
    if blockers(session, fencer):
        return False
    name = fencer.display_name
    final_address = fencer.email
    final_language = fencer.language
    cancelled = _apply(session, fencer)
    _notify_organizers(session, cancelled, name, mailer)
    # queued after the scrub, so its one outbox row carries the address until
    # the outbox's own period removes it (design D6)
    if final_address is not None:
        mailer.send(
            build_message(
                final_address,
                settings.email_sender,
                t("email.accountDeletion.completed.subject", final_language),
                t("email.accountDeletion.completed.body", final_language, name=name),
            )
        )
    return True


def due(session: Session) -> list[Fencer]:
    """Requests whose seven days have passed, oldest first."""
    cutoff = datetime.now(UTC) - GRACE
    return list(
        session.scalars(
            select(Fencer)
            .where(
                Fencer.deletion_requested_at.is_not(None),
                Fencer.deletion_requested_at <= cutoff,
                Fencer.deleted_at.is_(None),
            )
            .order_by(Fencer.deletion_requested_at)
        ).all()
    )


def run_pass(session: Session, mailer: Mailer) -> None:
    """The scheduler's deletion pass: each account in its own transaction, so
    one failure cannot strand the rest (design D3). A deferred request stays
    pending and shows among the Admin's tasks."""
    for fencer in due(session):
        try:
            if execute(session, fencer, mailer):
                session.commit()
            else:
                session.rollback()
        except Exception:
            session.rollback()
            logger.exception("account deletion failed for fencer %s", fencer.id)


# -------------------------------------------------------------- Admin erasure


def _row_ids(session: Session, fencer: Fencer) -> set[str]:
    """The ids the rows pipeline gives this record's registrations."""
    return {
        source or f"reg:{registration_id}"
        for registration_id, source in session.execute(
            select(Registration.id, Registration.source_row_id).where(
                Registration.fencer_id == fencer.id
            )
        ).tuples()
    }


def erase_identity(session: Session, fencer: Fencer) -> None:
    """Blank what a roster shows of a person, on any record (design D7): for an
    upheld objection, or a request from someone with no account. Rules that
    corrected those fields on the record's rows are withdrawn and their values
    redacted, with the journal's copies. Money is not touched. The caller
    commits."""
    now = datetime.now(UTC)
    targets = _row_ids(session, fencer)
    erased_rule_ids: set[int] = set()
    if targets:
        for rule in session.scalars(
            select(Rule).where(Rule.target.in_(targets), Rule.kind == "field_edit")
        ):
            if rule.payload.get("field") in IDENTITY_FIELDS:
                rule.payload = {**rule.payload, "value": None}
                if rule.deleted_at is None:
                    rule.deleted_at = now
                erased_rule_ids.add(rule.id)
    if erased_rule_ids:
        for entry in session.scalars(
            select(RuleJournalEntry).where(RuleJournalEntry.rule_id.in_(erased_rule_ids))
        ):
            payload = entry.content.get("payload") if isinstance(entry.content, dict) else None
            if isinstance(payload, dict):
                entry.content = {**entry.content, "payload": {**payload, "value": None}}
    _blank_identity(fencer)
    if fencer.deleted_at is None and fencer.email is None:
        fencer.deleted_at = now
    session.add(AccountErasure(fencer_id=fencer.id, kind=IDENTITY, created_at=now))


def reapply(session: Session, erasures: Iterable[tuple[int, str]]) -> int:
    """Erase again every record a later log lists (design D8): what a restore
    runs before the service reopens. A restore is not a request — whatever
    blocked the deletion then was settled once already — so nothing is asked
    and nothing is mailed; every message was sent the first time. Records
    already erased are left as they are; the count is of records changed."""
    changed = 0
    for fencer_id, kind in erasures:
        fencer = session.get(Fencer, fencer_id)
        if fencer is None:
            continue
        if kind == ACCOUNT and fencer.deleted_at is None:
            _apply(session, fencer)
            changed += 1
        elif kind == IDENTITY and (
            fencer.display_name != DELETED_LABEL or fencer.hr_id is not None
        ):
            erase_identity(session, fencer)
            changed += 1
    return changed


# ------------------------------------------------------------- classification

# Every text-bearing column, and what a deletion does to it (design D9). A new
# String, Text or JSON column fails `test_account_deletion_columns` until it is
# placed here, so the map cannot drift from the schema unseen.
#   removed  — cleared or deleted on execution
#   redacted — the account's addresses are taken out where found by value
#   kept     — stays, for the reason given
#   none     — holds nothing personal
COLUMN_HANDLING: dict[str, tuple[str, str]] = {
    "fencers.email": ("removed", "the login"),
    "fencers.password_hash": ("removed", "the login"),
    "fencers.display_name": ("kept", "only where a held roster lists the person (D2)"),
    "fencers.nationality": ("kept", "only where a held roster lists the person (D2)"),
    "fencers.club": ("kept", "only where a held roster lists the person (D2)"),
    "fencers.language": ("removed", "reset to the default"),
    "fencers.role": ("removed", "reset to fencer"),
    "fencers.organizer_terms_version": ("removed", "cleared"),
    "account_erasures.kind": ("none", "the log holds no personal data (D8)"),
    "hr_fighters.name": ("kept", "HEMA Ratings' public index, not the account"),
    "hr_fighters.name_folded": ("kept", "HEMA Ratings' public index"),
    "hr_fighters.nationality": ("kept", "HEMA Ratings' public index"),
    "hr_fighters.club": ("kept", "HEMA Ratings' public index"),
    "hr_index_refreshes.status": ("none", "operational"),
    "hr_index_refreshes.detail": ("none", "operational"),
    "outgoing_mail.recipient": ("removed", "messages to the account's addresses are deleted"),
    "outgoing_mail.subject": ("removed", "with the message"),
    "outgoing_mail.last_error": ("removed", "with the message; it may quote the recipient"),
    "pending_signups.email": ("kept", "not the account: an unfinished signup, gone at expiry"),
    "pending_signups.password_hash": ("kept", "an unfinished signup, gone at expiry"),
    "pending_signups.display_name": ("kept", "an unfinished signup, gone at expiry"),
    "pending_signups.nationality": ("kept", "an unfinished signup, gone at expiry"),
    "pending_signups.club": ("kept", "an unfinished signup, gone at expiry"),
    "pending_signups.language": ("kept", "an unfinished signup, gone at expiry"),
    "pending_signups.return_to": ("none", "a path of this application"),
    "pending_signups.key_hash": ("none", "a hash of a random key"),
    "fencer_profile_audit.field": ("removed", "the trail is deleted"),
    "fencer_profile_audit.old_value": ("removed", "the trail is deleted"),
    "fencer_profile_audit.new_value": ("removed", "the trail is deleted"),
    "organizer_requests.message": ("removed", "the request is deleted"),
    "organizer_requests.state": ("removed", "the request is deleted"),
    "password_resets.key_hash": ("removed", "the reset is deleted"),
    "tournaments.slug": ("none", "the event"),
    "tournaments.display_name": ("none", "the event"),
    "tournaments.subtitle": ("none", "the event"),
    "tournaments.logo_mime": ("none", "the event"),
    "tournaments.logo_tint": ("none", "the event"),
    "tournaments.cover_tint": ("none", "the event"),
    "tournaments.cover_photo_mime": ("none", "the event"),
    "tournaments.short_code": ("none", "the event"),
    "tournaments.language": ("none", "the event"),
    "tournaments.city": ("none", "the event"),
    "tournaments.address": ("none", "the venue"),
    "tournaments.description": ("none", "the organizer's prose"),
    "tournaments.qualification_criteria": ("none", "the organizer's prose"),
    "tournaments.registration_instructions": ("none", "the organizer's prose"),
    "tournaments.external_registration_url": ("none", "the event"),
    "tournaments.organizers": ("kept", "the organizers' public names, theirs to edit"),
    "tournaments.timezone": ("none", "the event"),
    "tournaments.registrations_kept_by": ("none", "the event"),
    "tournaments.payment_mode": ("none", "the event"),
    "tournaments.bank_account": ("kept", "the organizer's published account"),
    "tournaments.bank_account_holder": ("kept", "the organizer's published account"),
    "tournaments.local_currency": ("none", "the event"),
    "tournaments.fio_token": ("none", "a credential of the organizer's bank feed"),
    "tournaments.output_sheet_url": ("none", "the organizer's sheet"),
    "tournaments.hr_category_map": ("none", "configuration"),
    "tournaments.discounts": ("none", "configuration"),
    "disciplines.slug": ("none", "configuration"),
    "disciplines.name": ("none", "configuration"),
    "disciplines.weapon": ("none", "configuration"),
    "disciplines.gender": ("none", "configuration"),
    "disciplines.material": ("none", "configuration"),
    "disciplines.kind": ("none", "configuration"),
    "disciplines.schedule_when": ("none", "configuration"),
    "disciplines.schedule_where": ("none", "configuration"),
    "disciplines.ruleset": ("none", "configuration"),
    "discount_codes.code": ("none", "configuration"),
    "discount_codes.name": ("none", "configuration"),
    "discount_codes.effect": ("none", "configuration"),
    "discount_codes.scope": ("none", "configuration"),
    "extra_items.name": ("none", "configuration"),
    "extra_items.category": ("none", "configuration"),
    "extra_items.schedule_when": ("none", "configuration"),
    "extra_items.schedule_where": ("none", "configuration"),
    "extra_items.remark": ("none", "configuration"),
    "extra_items.option_label": ("none", "configuration"),
    "extra_items.option_choices": ("none", "configuration"),
    "import_batches.filename": ("none", "the organizer's file name"),
    "import_decisions.kind": ("none", "operational"),
    "import_decisions.key": ("none", "a hash of a row"),
    "import_decisions.payload": ("redacted", "a parsed row may hold the address"),
    "import_decisions.source": ("none", "operational"),
    "manual_rows.name": (
        "kept",
        "the organizer's row; a name-only copy is the Admin's to erase (D7)",
    ),
    "manual_rows.nationality": ("kept", "the organizer's row"),
    "manual_rows.club": ("kept", "the organizer's row"),
    "manual_rows.email": ("redacted", "cleared where it is one of the addresses"),
    "manual_rows.disciplines": ("none", "slugs"),
    "manual_rows.weapon_rentals": ("none", "item names"),
    "manual_rows.notes": ("kept", "the organizer's note; data-retention clears it in time"),
    "operations.kind": ("none", "operational"),
    "operations.status": ("none", "operational"),
    "operations.outcome": ("none", "counts and codes"),
    "rules.phase": ("none", "operational"),
    "rules.kind": ("none", "operational"),
    "rules.target": ("none", "a row id"),
    "rules.payload": ("redacted", "an organizer's correction may write the address"),
    "sheet_row_numbers.row_id": ("none", "a row id"),
    "hr_snapshot_ratings.discipline_code": ("none", "a category code"),
    "imported_rows.key": ("none", "a hash of a row"),
    "imported_rows.raw": ("redacted", "the imported table's cells"),
    "registrations.state": ("none", "lifecycle"),
    "registrations.source_row_id": ("none", "a row id"),
    "registrations.contact_email": (
        "removed",
        "on the account's own registrations; another seat's stays (D5)",
    ),
    "registrations.refund_state": ("none", "lifecycle"),
    "registrations.weapon_rentals": ("none", "item names"),
    "registrations.accommodation": ("removed", "on the account's own registrations"),
    "registrations.notes": ("removed", "on the account's own registrations"),
    "rule_journal.action": ("none", "operational"),
    "rule_journal.content": ("redacted", "a snapshot of a rule's payload"),
    "bank_transactions.external_id": ("none", "the bank's id"),
    "bank_transactions.source": ("none", "operational"),
    "bank_transactions.currency": ("none", "money"),
    "bank_transactions.message": (
        "kept",
        "the payer's data, the organizer's record; data-retention prunes it",
    ),
    "bank_transactions.payer_name": ("kept", "the payer's data; data-retention prunes it"),
    "bank_transactions.payer_account": ("kept", "the payer's data; data-retention prunes it"),
    "bank_transactions.named_person": ("kept", "the payer's data; data-retention prunes it"),
    "bank_transactions.user_identification": ("kept", "the payer's data; data-retention prunes it"),
    "bank_transactions.comment": ("kept", "the payer's data; data-retention prunes it"),
    "bank_transactions.specification": ("kept", "the payer's data; data-retention prunes it"),
    "bank_transactions.specific_symbol": ("none", "a payment symbol"),
    "bank_transactions.status": ("none", "operational"),
    "bank_transactions.status_reason": ("none", "operational"),
    "bank_transactions.rejected_fencer_ids": ("none", "ids"),
    "manual_payments.currency": ("none", "money"),
    "manual_payments.method": ("none", "money"),
    "manual_payments.note": ("kept", "the organizer's note on a payment"),
    "manual_payments.recorded_by": ("redacted", "the label keeps the name, loses the address"),
    "payment_credits.currency": ("none", "money"),
    "payment_credits.source_kind": ("none", "money"),
    "payment_credits.origin": ("none", "money"),
    "payment_credits.reversed_by": ("redacted", "the label keeps the name, loses the address"),
    "payment_credits.reversed_reason": ("kept", "the organizer's reason"),
    "payment_waivers.reason": ("kept", "the organizer's reason"),
    "payment_waivers.granted_by": ("redacted", "the label keeps the name, loses the address"),
    "payment_waivers.revoked_by": ("redacted", "the label keeps the name, loses the address"),
    "registration_extras.option_value": ("none", "a size or a choice"),
    "teams.name": ("none", "a team's name"),
    "payment_events.kind": ("none", "operational"),
    "payment_events.detail": ("redacted", "audit lines quote actor labels; the VS or name stays"),
    "team_members.name": ("kept", "another person, entered by the team's captain"),
    "team_members.club": ("kept", "another person"),
    "team_members.nationality": ("kept", "another person"),
    # the roster log quotes members as they stood; its actor is a fencer id,
    # read through display_name, which D2 already governs
    "roster_changes.member_name": ("kept", "another person, as the roster listed them"),
    "roster_changes.before": ("kept", "a member's field as the roster listed it"),
    "roster_changes.after": ("kept", "a member's field as the roster listed it"),
    "roster_changes.field": ("none", "a field's name"),
    "roster_changes.kind": ("none", "operational"),
}
