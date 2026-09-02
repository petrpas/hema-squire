"""Turning a fencer list into registrations that can be paid for.

An imported row and a hand-entered row state who is competing. They carry no
variable symbol, no price and no balance, which is right for the moment they
arrive — a row a merge may collapse must not spend an identifier first — and
leaves a tournament whose fencers were imported unable to take a payment at all:
matching resolves through `Registration.vs`, and there is none.

This is the later, explicit moment at which the organizer says the roster is
settled and should be billable (spec `imported-registrations`). It creates the
fencer records and registrations the rows imply, prices each at the row's own
registration moment, and issues a variable symbol — after which everything
downstream of a match works on these fencers exactly as it does on fencers who
registered in the application.

Two properties matter more than the rest:

- **Nothing here sends mail.** The rows describe people who registered elsewhere,
  often long ago and often already paid. The registrations are created with
  their lifecycle clocks dormant, and no confirmation, invitation or reminder is
  ever sent for one.
- **Running it again changes nothing it already did.** The pass selects rows
  without a registration, so a rerun issues only what is new.
"""

import datetime
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import pricing, rownumbers, sheet
from app.models import (
    Discipline,
    DisciplineKind,
    Fencer,
    Registration,
    RegistrationDiscipline,
    RegistrationState,
    Tournament,
)

# why a row could not be issued a registration. Stated rather than silently
# skipped: a row the organizer expected to see billed and does not is a question
# they must be able to answer without reading the table twice.
NO_DISCIPLINE = "no_discipline"
NO_EMAIL = "no_email"
NO_NAME = "no_name"
# another row already claimed this e-mail address. `Fencer.email` is the account
# identity and is unique across the deployment, and a fencer registers once per
# tournament, so two rows sharing an address resolve to one fencer and only the
# first can be issued a registration.
#
# Not always a duplicate: on a real roster it is usually one person entering
# several others — a club representative, or a parent — and the pilot has one
# address covering three different fencers. The organizer has to give the others
# their own address before they can be billed, so the reason names the address
# rather than claiming the row is a duplicate.
EMAIL_TAKEN = "email_taken"


@dataclass
class Skipped:
    row_id: str
    name: str | None
    reason: str


@dataclass
class IssueReport:
    issued: int = 0
    already: int = 0
    skipped: list[Skipped] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "issued": self.issued,
            "already": self.already,
            "skipped": [
                {"row_id": s.row_id, "name": s.name, "reason": s.reason}
                for s in self.skipped
            ],
        }


def _registration_time(row: dict) -> datetime.datetime:
    """The moment the row says the fencer registered, which is the date its
    price is read at (spec, "What an issued registration is worth").

    A row whose moment is missing or unreadable falls back to now. That is the
    conservative reading: it prices at today's fees rather than inventing a date
    that might silently apply an early-bird discount nobody earned.
    """
    raw = row.get("registered_at")
    if isinstance(raw, str) and raw:
        try:
            parsed = datetime.datetime.fromisoformat(raw)
        except ValueError:
            parsed = None
        if parsed is not None:
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=datetime.UTC)
            return parsed
    return datetime.datetime.now(datetime.UTC)


def _hr_id_to_carry(row: dict) -> int | None:
    """The row's HEMA Ratings id, but only where a human reached that verdict.

    A `proposed` match is the evidence register's reading, not a decision, and
    binding one here would claim a profile on the fencer's behalf that nobody
    confirmed — the same reason self-service signup binds only on an explicit
    ownership confirmation (spec `fencer-accounts`).
    """
    if row.get("match_verdict") != "confirmed":
        return None
    hr_id = row.get("hr_id")
    return hr_id if isinstance(hr_id, int) else None


def _individual_disciplines(tournament: Tournament, row: dict) -> list[Discipline]:
    by_slug = {
        d.slug: d for d in tournament.disciplines if d.kind == DisciplineKind.INDIVIDUAL
    }
    return [by_slug[slug] for slug in row.get("disciplines") or [] if slug in by_slug]


def pending(session: Session, tournament: Tournament) -> list[dict]:
    """The fencer-list rows an issuing pass would act on: source rows that are
    still rows, and not deleted.

    A row that has been issued a registration is no longer in this list, because
    the registration stands in its place under the row's own id — which is what
    makes the count the organizer confirms and the work the pass does the same
    number (`sheet.base_rows`).
    """
    return [
        row
        for row in sheet.source_rows(session, tournament)
        if not row.get("_deleted")
    ]


def _resolve_fencer(session: Session, row: dict) -> Fencer | None:
    """The fencer this row is about, created if no record exists yet.

    An existing record is reused and never overwritten: it may belong to someone
    who has an account, and their own name, club and HEMA Ratings binding are
    theirs, not the roster's. A created record holds no password, so it is a
    fencer of the tournament rather than an account — and nothing here mails it
    (spec `fencer-accounts`, "A fencer record may exist without an account").
    """
    email = (row.get("email") or "").strip().lower()
    if not email:
        return None
    existing = session.query(Fencer).filter(Fencer.email == email).one_or_none()
    if existing is not None:
        return existing
    fencer = Fencer(
        email=email,
        password_hash=None,
        display_name=(row.get("name") or "").strip(),
        hr_id=_hr_id_to_carry(row),
        nationality=row.get("nationality"),
        club=row.get("club"),
        language=row.get("language") or "cs",
    )
    session.add(fencer)
    return fencer


def _issue_one(
    session: Session, tournament: Tournament, row: dict, next_vs
) -> Registration | str:
    """One row's registration, or the reason it could not have one."""
    if not (row.get("name") or "").strip():
        return NO_NAME
    disciplines = _individual_disciplines(tournament, row)
    if not disciplines:
        # a registration with no entries would total zero, read as settled, and
        # quietly absorb a payment (design Decision 6)
        return NO_DISCIPLINE
    fencer = _resolve_fencer(session, row)
    if fencer is None:
        # `Fencer.email` is the account identity and is not nullable, so a row
        # without one cannot become a registration until the organizer supplies
        # it in the table
        return NO_EMAIL
    session.flush()
    if fencer.id is not None:
        existing = session.scalar(
            select(Registration).where(
                Registration.tournament_id == tournament.id,
                Registration.fencer_id == fencer.id,
            )
        )
        if existing is not None:
            # asked before inserting rather than caught after: the same
            # IntegrityError would otherwise be indistinguishable from a VS
            # collision, and the retry below would spend five variable symbols
            # discovering that this row can never be issued
            return EMAIL_TAKEN

    for attempt in range(5):
        registration = Registration(
            tournament=tournament,
            fencer=fencer,
            source_row_id=row["id"],
            state=RegistrationState.RESERVED,
            registered_at=_registration_time(row),
            vs=next_vs(session, tournament),
            # the whole point of the mark: no window, no reminder, no expiry,
            # no demotion at the seating deadline (spec, "An issued
            # registration's clocks never start")
            clocks_dormant=True,
            expires_at=None,
            weapon_rentals=row.get("weapon_rentals") or [],
            afterparty=bool(row.get("afterparty")),
            aftersparring=bool(row.get("aftersparring")),
            accommodation=row.get("accommodation"),
            notes=row.get("notes"),
        )
        for discipline in disciplines:
            # Seated, whatever the discipline's capacity says. A roster is a
            # record of who competed, not a queue of applicants: the fencers on
            # it were admitted by whoever ran the event, often a season ago.
            # Placing the overflow below the line would queue people who already
            # fenced and — because a substitute placement is not billed — leave
            # them owing nothing at all (spec imported-registrations, "Capacity
            # does not apply to an issued registration").
            registration.entries.append(
                RegistrationDiscipline(discipline=discipline, is_substitute=False)
            )
        session.add(registration)
        try:
            session.flush()
            break
        except IntegrityError:
            # a VS collision retries with the next number, exactly as
            # `routers.registrations.register` does — the unique constraint is
            # the backstop that turns a counter race into a retry
            session.rollback()
            if attempt == 4:
                raise
    else:  # pragma: no cover - the loop always breaks or raises
        raise RuntimeError("vs allocation exhausted its retries")

    # priced from what the row itself holds, at the row's own moment: the same
    # call an in-app registration is priced by, which reads
    # `registration.registered_at` — so early-bird applies as it did the day the
    # fencer signed up, and the total is then frozen like any other
    totals = pricing.registration_total(registration, tournament)
    registration.total_amount = totals.local
    registration.total_eur = totals.eur
    return registration


def issue(session: Session, tournament: Tournament, next_vs) -> IssueReport:
    """Issue registrations for every fencer-list row that has none.

    `next_vs` is injected rather than imported so this module does not depend on
    the router that owns the allocator; there is still only one allocator.
    """
    report = IssueReport()
    for row in pending(session, tournament):
        outcome = _issue_one(session, tournament, row, next_vs)
        if isinstance(outcome, str):
            report.skipped.append(Skipped(row["id"], row.get("name"), outcome))
            continue
        report.issued += 1
    session.commit()
    # the registration stands in the row's place under the row's own id, so the
    # number that id already holds is the number it keeps; this allocates only
    # for rows that somehow never had one
    rownumbers.allocate(
        session,
        tournament,
        [row["id"] for row in sheet.source_rows(session, tournament)],
    )
    session.commit()
    return report
