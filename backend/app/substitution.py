"""A seat changing hands.

The substitution itself, reached from beside its rule the way an amendment is.
`rules.py` holds the kind, its validation and the projection it writes;
`routers/rules_api.py` holds the HTTP concerns and the two messages. What is
here is the part that touches the database: which fencer record the seat lands
on, and the reassignment.

The whole design is that **the seat does not move**. Its number, its
registration moment and hence its order, its place above or below the line, its
variable symbol, its totals, its entries and its journal are properties of the
registration and of the row id, not of the person — so the substitute inherits
them by nothing being done to them. What changes is one foreign key and,
sometimes, one address (spec `fencer-substitution`).
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import amendment, rules
from app.hr_index import HRIndex, country_code, evidence_fields, name_key
from app.models import Fencer, Registration, RegistrationState, Rule, Tournament


@dataclass
class Identity:
    """Who a row is about, as a substitution states it.

    The same shape whether it is the substitute arriving or the fencer being
    replaced, because a withdrawal has to be able to put one back where the
    other stands (design D2)."""

    name: str
    hr_id: int | None
    nationality: str | None
    club: str | None
    email: str | None
    fencer_id: int | None = None

    def as_payload(self) -> dict:
        return {
            "name": self.name,
            "hr_id": self.hr_id,
            "nationality": self.nationality,
            "club": self.club,
            "email": self.email,
            "fencer_id": self.fencer_id,
        }


def identity_from_payload(payload: dict) -> Identity:
    return Identity(
        name=payload.get("name") or "",
        hr_id=payload.get("hr_id"),
        # the dialog hands over the index's English spelling where a profile
        # was picked; the list speaks ISO codes
        nationality=country_code(payload.get("nationality")) or payload.get("nationality"),
        club=payload.get("club"),
        email=payload.get("email"),
        fencer_id=payload.get("fencer_id"),
    )


def previous_identity(registration: Registration | None, row: dict) -> Identity:
    """The identity a substitution replaces, recorded in its payload.

    Read here and stored rather than re-derived at withdrawal: after a second
    substitution the row no longer knows who the first one displaced, and after
    an index refresh a profile may have moved under it."""
    if registration is not None:
        fencer = registration.fencer
        return Identity(
            name=fencer.display_name,
            hr_id=fencer.hr_id,
            nationality=fencer.nationality,
            club=fencer.club,
            email=registration.contact_email or fencer.email,
            fencer_id=fencer.id,
        )
    return Identity(
        name=row.get("name") or "",
        hr_id=row.get("hr_id"),
        nationality=row.get("nationality"),
        club=row.get("club"),
        email=row.get("email"),
    )


def _names_the_same(one: Identity, other: Identity) -> bool:
    return name_key(one.name) == name_key(other.name)


def _names_the_same_person(record: Fencer, name: str) -> bool:
    """Whether an address's record is the person the organizer just named.

    An address is an identity only so far. On a roster entered by a parent or a
    club representative it names the payer, and handing them the seat would
    enrol one person under another's name — the comparison, and the reason for
    it, are `issuing._resolve_fencer`'s (spec `fencer-substitution`, "The
    address decides which account holds the seat")."""
    return name_key(record.display_name) == name_key(name)


def resolve_substitute(
    session: Session,
    tournament: Tournament,
    identity: Identity,
    replaced: Fencer | None,
) -> tuple[Fencer, str | None]:
    """The fencer record the seat lands on, and the address the seat keeps.

    Four outcomes, in order (design D4):

    - the address names an existing account of the same name, and it is not the
      replaced fencer's → that account takes the seat and the seat keeps no
      address of its own;
    - the address is the replaced fencer's own, kept or typed out again → an
      account-less record, and the address becomes the seat's contact. Keeping
      an address must not hand the seat back to the account that address belongs
      to, which is the whole point of keeping it;
    - the address belongs to an account carrying a different name → an
      account-less record, the address the seat's contact, the other account
      untouched;
    - the address belongs to nobody → a record carrying it, which the substitute
      can later claim by the ordinary signup path, as an issued row's can.
    """
    email = (identity.email or "").strip().lower() or None
    if email is not None:
        wearer = session.scalar(select(Fencer).where(Fencer.email == email))
        if wearer is not None:
            if (replaced is None or wearer.id != replaced.id) and _names_the_same_person(
                wearer, identity.name
            ):
                _refuse_if_already_entered(session, tournament, wearer)
                return wearer, None
            # the replaced fencer's own record, or a stranger's: either way the
            # address cannot be written onto a second record — `fencers.email`
            # is unique — and belongs to the seat instead
            return _fresh_record(session, identity, email=None), email
    return _fresh_record(session, identity, email=email), None


def _fresh_record(session: Session, identity: Identity, *, email: str | None) -> Fencer:
    fencer = Fencer(
        email=email,
        password_hash=None,
        display_name=identity.name,
        hr_id=identity.hr_id,
        nationality=identity.nationality,
        club=identity.club,
    )
    session.add(fencer)
    session.flush()
    return fencer


def _refuse_if_already_entered(session: Session, tournament: Tournament, fencer: Fencer) -> None:
    held = session.scalar(
        select(Registration).where(
            Registration.tournament_id == tournament.id,
            Registration.fencer_id == fencer.id,
            Registration.state != RegistrationState.CANCELLED,
        )
    )
    if held is not None:
        raise HTTPException(status_code=409, detail="substitute_already_registered")


@dataclass
class Prepared:
    """A substitution settled but not yet done.

    Everything that can be refused is refused while assembling this — the shape
    of what was typed, the substitute already being entered, the substitute
    being the fencer already on the row — so that the rule is never written for
    a substitution that then fails to apply."""

    substitute: Fencer
    contact: str | None
    previous: Identity
    registration: Registration | None

    def payload(self, stated: dict, index: HRIndex) -> dict:
        """What the rule records: what the organizer stated, the substitute's
        record, the profile the substitute is bound to, and the identity being
        replaced.

        The profile is looked up here and carried, as a match resolution's is,
        because replay has no index: a rule without it put a bound substitute
        on the phases that identify a row by its profile with nothing to say but
        dashes."""
        hr_id = stated.get("hr_id")
        return {
            **stated,
            **evidence_fields(index.get(hr_id) if hr_id is not None else None),
            "fencer_id": self.substitute.id,
            "previous": self.previous.as_payload(),
        }


def prepare(
    session: Session,
    tournament: Tournament,
    registration: Registration | None,
    row: dict,
    payload: dict,
) -> Prepared:
    """Settle who the seat is about to belong to, refusing before anything is
    written (spec `fencer-substitution`, "What a substitution may not be done
    to")."""
    rules.validate_substitution(tournament, payload)
    if row.get("_deleted"):
        raise HTTPException(status_code=409, detail="row_is_deleted")
    if row.get("_merged_into") is not None:
        raise HTTPException(status_code=409, detail="row_was_absorbed")

    identity = identity_from_payload(payload)
    previous = previous_identity(registration, row)
    # Naming the person already on the row is not a substitution. Asked of the
    # identity rather than of the record it resolves to, because a second record
    # wearing the same name and profile is the same person entered twice, and
    # the seat would then read as having changed hands when it had not.
    if _names_the_same(identity, previous) and identity.hr_id == previous.hr_id:
        raise HTTPException(status_code=409, detail="substitute_is_the_fencer_on_the_row")
    replaced = registration.fencer if registration is not None else None
    substitute, contact = resolve_substitute(session, tournament, identity, replaced)
    if replaced is not None and substitute.id == replaced.id:
        raise HTTPException(status_code=409, detail="substitute_is_the_fencer_on_the_row")
    return Prepared(
        substitute=substitute, contact=contact, previous=previous, registration=registration
    )


def commit(session: Session, prepared: Prepared) -> None:
    """Move the seat to the substitute. Nothing else is touched.

    Not a cancellation and a re-registration: that would mint a new variable
    symbol, restart the payment window, orphan every credit already matched
    against the old symbol and put the substitute at the end of the seating
    order — the opposite of what a substitution is for (design D1)."""
    registration = prepared.registration
    if registration is None:
        return
    registration.fencer_id = prepared.substitute.id
    registration.contact_email = prepared.contact
    session.flush()


def withdraw(session: Session, tournament: Tournament, rule: Rule) -> None:
    """Put the seat back where a withdrawn substitution took it from.

    The identity it returns to travels in the rule, so a seat substituted twice
    returns to whoever held it when *this* rule was made, and a profile that has
    moved in the index since does not move the answer with it.

    Nothing about the seat is undone, because nothing about it was done: the
    number, the symbol, the totals and the journal were never touched. The
    projection returns of its own accord, the rule no longer being replayed.
    """
    registration = amendment.registration_for_row(session, tournament, rule.target)
    if registration is None:
        return
    previous = identity_from_payload(rule.payload.get("previous") or {})
    if previous.fencer_id is None:
        return
    holder = session.get(Fencer, previous.fencer_id)
    if holder is None:
        return
    registration.fencer_id = holder.id
    # The seat needs an address of its own only where the account holding it
    # carries a different one, which is the state it was in before.
    registration.contact_email = None if holder.email == previous.email else previous.email
    session.flush()
