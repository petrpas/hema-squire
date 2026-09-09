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

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import pricing, rownumbers, sheet
from app.hr_index import name_key
from app.models import (
    Discipline,
    DisciplineKind,
    ExtraCategory,
    ExtraItem,
    Fencer,
    Registration,
    RegistrationDiscipline,
    RegistrationExtra,
    RegistrationsKeptBy,
    RegistrationState,
    Tournament,
)

# why a row could not be issued a registration. Stated rather than silently
# skipped: a row the organizer expected to see billed and does not is a question
# they must be able to answer without reading the table twice.
#
# Both describe the row rather than Squire's bookkeeping, and that is the test a
# reason has to pass. Two that failed it were removed: a row carrying no e-mail
# address, and a row repeating one another row had used. Neither is a defect in
# the row — a roster is routinely entered by one person for several, and the
# address is that person's — and refusing them left fencers unbillable with no
# remedy the organizer could reach (spec `fencer-accounts`, "A fencer record may
# exist without an account").
NO_DISCIPLINE = "no_discipline"
NO_NAME = "no_name"


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
                {"row_id": s.row_id, "name": s.name, "reason": s.reason} for s in self.skipped
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
    by_slug = {d.slug: d for d in tournament.disciplines if d.kind == DisciplineKind.INDIVIDUAL}
    return [by_slug[slug] for slug in row.get("disciplines") or [] if slug in by_slug]


def pending(session: Session, tournament: Tournament) -> list[dict]:
    """The fencer-list rows an issuing pass would act on: source rows that are
    still rows, and not deleted.

    A row that has been issued a registration is no longer in this list, because
    the registration stands in its place under the row's own id — which is what
    makes the count the organizer confirms and the work the pass does the same
    number (`sheet.base_rows`).
    """
    return [row for row in sheet.source_rows(session, tournament) if not row.get("_deleted")]


def _address(row: dict) -> str:
    return (row.get("email") or "").strip().lower()


def _resolve_fencer(session: Session, row: dict, claimed: set[str]) -> Fencer:
    """The fencer this row is about, created if no record exists yet.

    An existing record is reused and never overwritten: it may belong to someone
    who has an account, and their own name, club and HEMA Ratings binding are
    theirs, not the roster's. A created record holds no password, so it is a
    fencer of the tournament rather than an account — and nothing here mails it
    (spec `fencer-accounts`, "A fencer record may exist without an account").

    **An address is claimed by at most one record.** A row carrying none, and a
    row repeating one this pass has already used, both get a record with no
    address at all. Two rows sharing an address are not one person entered twice
    — deduplication has already had its say — but one person's address written
    against another, which is what a parent or a club representative entering a
    family does. Asserting it as the second person's would be a claim nobody
    made, and it is not needed: nothing writes to a record enrolled this way.

    Which row keeps it is the order the rows are issued in, which is
    registration order. Arbitrary between siblings, and it does not matter: the
    address stays visible on both rows of the fencer list, where it was written.
    """
    email = _address(row)
    name = (row.get("name") or "").strip()
    if email and email not in claimed:
        existing = session.query(Fencer).filter(Fencer.email == email).one_or_none()
        claimed.add(email)
        # An address is reused as an identity only where it names the same
        # person. On a roster entered by a parent or a club representative it
        # names the payer, and binding the row to their record would enrol one
        # person under another's name — the pilot's own shape: two brothers and
        # their father's address, where the father is himself a fencer.
        #
        # Compared with the fighters index's own key, which disregards
        # diacritics, case and word order and is not a subset test, so
        # "Novák Jan" is Jan Novák and "Jan Petr Novák" is not.
        if existing is not None and name_key(existing.display_name) == name_key(name):
            return existing
        if existing is not None:
            email = None
    else:
        email = None
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


# a row whose person is already registered on this tournament. Not a skip: the
# row states somebody the tournament already holds a registration for, so there
# is nothing to issue and nothing wrong with the row. Reported as one the pass
# left alone.
ALREADY = "already"


def _issue_one(
    session: Session, tournament: Tournament, row: dict, next_vs, claimed: set[str]
) -> Registration | str:
    """One row's registration, or the reason it could not have one."""
    if not (row.get("name") or "").strip():
        return NO_NAME
    disciplines = _individual_disciplines(tournament, row)
    if not disciplines:
        # a registration with no entries would total zero, read as settled, and
        # quietly absorb a payment (design Decision 6)
        return NO_DISCIPLINE
    fencer = _resolve_fencer(session, row, claimed)
    session.flush()
    if fencer.id is not None:
        existing = session.scalar(
            select(Registration).where(
                Registration.tournament_id == tournament.id,
                Registration.fencer_id == fencer.id,
            )
        )
        if existing is not None:
            # a registration is unique per (tournament, fencer), so this row's
            # person is already on the tournament — reached where the row's
            # address belongs to somebody who registered in the application.
            # Asked before inserting rather than caught after: the same
            # IntegrityError would otherwise be indistinguishable from a VS
            # collision, and the retry below would spend five variable symbols
            # discovering that this row has nothing to issue
            return ALREADY

    squire_keeps = tournament.registrations_kept_by is RegistrationsKeptBy.SQUIRE
    for attempt in range(5):
        registration = Registration(
            tournament=tournament,
            fencer=fencer,
            source_row_id=row["id"],
            state=RegistrationState.RESERVED,
            registered_at=_registration_time(row),
            # A variable symbol is a shortcut: quoted on a payment, it finds
            # the registration without anybody reading the message. Squire tells
            # a fencer to quote one — and on a tournament whose registrations
            # the organizer keeps it has told them nothing, because they
            # registered through the organizer's own form and paid against
            # whatever that form said. A symbol minted here would appear on no
            # statement and shorten nothing, while consuming a number from a
            # sequence that is unique across the deployment and never reused
            # (spec, "A variable symbol is issued only where Squire keeps the
            # registrations"). Such a payment is resolved from the payer's own
            # words instead (`name-assisted-matching`).
            vs=next_vs(session, tournament) if squire_keeps else None,
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
            # the backstop that turns a counter race into a retry. With no
            # symbol allocated there is nothing to collide, so a failure here
            # is something else and retrying would only hide it
            session.rollback()
            if attempt == 4 or not squire_keeps:
                raise
    else:  # pragma: no cover - the loop always breaks or raises
        raise RuntimeError("vs allocation exhausted its retries")

    _select_extras(tournament, registration, row)
    # priced from what the row itself holds, at the row's own moment: the same
    # call an in-app registration is priced by, which reads
    # `registration.registered_at` — so early-bird applies as it did the day the
    # fencer signed up, and the total is then frozen like any other
    totals = pricing.registration_total(registration, tournament)
    registration.total_amount = totals.local
    registration.total_eur = totals.eur
    return registration


def _select_extras(tournament: Tournament, registration: Registration, row: dict) -> None:
    """Turn what the row borrows and answers into the item selections the
    tournament prices by.

    A row states its rentals as names and its afterparty as a yes, which is the
    older shape and the only one a fencer list can carry. A tournament that
    prices by items bills neither: `pricing.selection_total` reads the item
    selections there and the legacy fields only on a tournament that has no
    items at all. Issuing wrote the row's answers into the legacy fields alone,
    so every rental on such a tournament was issued free — on the pilot, 32
    borrowed weapons across 19 registrations, 1 600 Kč nowhere in any total.

    The legacy fields stay written beside the selections. They are what the
    fencer list and the confirmation mail read the row's answers from, and a
    name this tournament lends nothing by keeps its place there — stated by the
    row, priced by nothing, which is what `unpriced_rentals` names.

    An afterparty is taken up only where exactly one item offers one. Where
    several do, the row's bare yes does not say which, and guessing would bill
    somebody for an evening they did not pick.
    """
    if not pricing.uses_itemized_pricing(tournament):
        return
    by_name: dict[str, ExtraItem] = {
        item.name: item for item in tournament.extra_items if item.category == ExtraCategory.RENTAL
    }
    # one of each, however often a row names it: a fencer borrows a sabre, not
    # two, and the importer is asked to state each item once for that reason
    for name in dict.fromkeys(row.get("weapon_rentals") or []):
        item = by_name.get(name)
        if item is not None:
            registration.extra_selections.append(RegistrationExtra(item=item, qty=1))
    if row.get("afterparty"):
        offered = [
            item for item in tournament.extra_items if item.category == ExtraCategory.AFTERPARTY
        ]
        if len(offered) == 1:
            registration.extra_selections.append(RegistrationExtra(item=offered[0], qty=1))


def would_skip(session: Session, tournament: Tournament) -> list[Skipped]:
    """The rows an issuing pass would refuse, and why — without writing.

    A dry run, because the answer is needed where nobody is issuing anything: a
    fencer missing from a list the organizer expected them on is a question, and
    "not on this tournament" and "here, but not billable" are different answers
    with different remedies.

    Only the row's own contents decide, so this needs no simulation of the pass:
    a name and at least one discipline, and nothing about the address. A row
    whose person is already registered is not refused either — it is left alone,
    which is not a thing to warn about (spec `imported-registrations`, "What a
    row must have to be issued").
    """
    skipped = []
    for row in pending(session, tournament):
        if not (row.get("name") or "").strip():
            reason = NO_NAME
        elif not _individual_disciplines(tournament, row):
            reason = NO_DISCIPLINE
        else:
            continue
        skipped.append(Skipped(row["id"], row.get("name"), reason))
    return skipped


def issue(session: Session, tournament: Tournament, next_vs) -> IssueReport:
    """Issue registrations for every fencer-list row that has none.

    `next_vs` is injected rather than imported so this module does not depend on
    the router that owns the allocator; there is still only one allocator.
    """
    report = IssueReport()
    # counted before the pass, so what it reports is what it left alone rather
    # than what it has just created. A row that has been issued a registration
    # leaves `source_rows` — the registration stands in its place — so the
    # registrations carrying a row's id are exactly the rows already done
    report.already = (
        session.scalar(
            select(func.count())
            .select_from(Registration)
            .where(
                Registration.tournament_id == tournament.id,
                Registration.source_row_id.is_not(None),
            )
        )
        or 0
    )
    claimed: set[str] = set()
    for row in pending(session, tournament):
        outcome = _issue_one(session, tournament, row, next_vs, claimed)
        if outcome == ALREADY:
            report.already += 1
            continue
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
