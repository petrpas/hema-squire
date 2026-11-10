"""Applying a save to a team's roster, and recording what it did.

One module because two actors do the same thing: the entering fencer through
their own registration, the organizer through the console (design
roster-identity-and-history D6). Same diff, same log, different gate and a
different actor recorded.

Nothing here touches price, VS, mail, refund state or capacity. A team's fee is
per team and never multiplied by its roster, so there is no edit to a roster
that money could follow (spec team-disciplines, Roster editing changes no
money).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import rownumbers, setup
from app.hr_index import country_code
from app.models import (
    RosterChange,
    RosterChangeKind,
    Team,
    TeamMember,
    Tournament,
)
from app.schemas import RosterMemberIn

# the stored fields a change to which is worth an entry in the log; `ordinal`
# is deliberately absent — order carries no meaning, so a reorder changes
# nothing anybody could dispute (spec team-disciplines)
LOGGED_FIELDS = ("name", "hr_id", "club", "nationality")


def after_composition_deadline(tournament: Tournament, now: datetime | None = None) -> bool:
    """Whether a change made at `now` falls after the tournament's composition
    deadline. Stored on each entry rather than recomputed, since the deadline
    is a setting the organizer may move afterwards (design D3)."""
    deadline = tournament.team_composition_deadline
    if deadline is None:
        return False
    return setup.local_date(tournament, now or datetime.now(UTC)) > deadline


def _as_text(value: object) -> str | None:
    return None if value is None else str(value)


def _stated_nationality(stated: RosterMemberIn) -> str | None:
    """One vocabulary down the nationality column, as the identity columns of
    every table read it (spec team-disciplines, A roster member is a named
    person): the search result the client echoes back spells a country in the
    fighters index's own English, and this is the only place a member is
    written. A spelling no country can be read from stands as given."""
    return country_code(stated.nationality) or stated.nationality


def apply_roster_save(
    session: Session,
    tournament: Tournament,
    team: Team,
    stated: Sequence[RosterMemberIn],
    *,
    actor_fencer_id: int,
    by_organizer: bool,
) -> None:
    """Apply one whole-roster save as a difference against the roster stored.

    A member stated with its id is updated in place, one stated without an id
    is added, one the save does not state is marked removed, and a stated id
    belonging to a removed member restores it. Ordinals are rewritten from the
    order stated, and no member's identity depends on them (design D1).

    An id the save states that is not a member of this team is refused rather
    than ignored: the request is then not a statement about this roster, and
    ignoring it would silently add a member the sender meant to move.
    """
    # a team discipline always carries a maximum (`DisciplineIn` enforces it on
    # write); no maximum recorded is no maximum to exceed. The count is of the
    # roster the save states — a restored member is in it, so the same check
    # refuses a restore into a full roster
    team_max = team.discipline.team_max
    if team_max is not None and len(stated) > team_max:
        raise HTTPException(status_code=422, detail={"roster_over_maximum": team_max})

    stored = {
        member.id: member
        for member in session.scalars(select(TeamMember).where(TeamMember.team_id == team.id)).all()
    }
    seen: set[int] = set()
    for row in stated:
        if row.id is None:
            continue
        if row.id not in stored or row.id in seen:
            raise HTTPException(status_code=422, detail={"member_not_on_roster": row.id})
        seen.add(row.id)

    now = datetime.now(UTC)
    after_deadline = after_composition_deadline(tournament, now)

    def record(
        member: TeamMember,
        kind: RosterChangeKind,
        *,
        field: str | None = None,
        before: str | None = None,
        after: str | None = None,
    ) -> None:
        session.add(
            RosterChange(
                team_id=team.id,
                member_id=member.id,
                member_name=member.name,
                kind=kind,
                field=field,
                before=before,
                after=after,
                actor_fencer_id=actor_fencer_id,
                by_organizer=by_organizer,
                after_deadline=after_deadline,
            )
        )

    added: list[TeamMember] = []
    for ordinal, row in enumerate(stated):
        values = {
            "name": row.name,
            "hr_id": row.hr_id,
            "club": row.club,
            "nationality": _stated_nationality(row),
        }
        if row.id is None:
            member = TeamMember(team_id=team.id, ordinal=ordinal, **values)
            session.add(member)
            added.append(member)
            continue
        member = stored[row.id]
        restored = member.removed_at is not None
        if restored:
            member.removed_at = None
            member.removed_by_fencer_id = None
        changes = [
            (field, _as_text(getattr(member, field)), _as_text(values[field]))
            for field in LOGGED_FIELDS
            if getattr(member, field) != values[field]
        ]
        for field, value in values.items():
            setattr(member, field, value)
        member.ordinal = ordinal
        if restored:
            record(member, RosterChangeKind.RESTORED)
        for field, before, after in changes:
            record(member, RosterChangeKind.EDITED, field=field, before=before, after=after)

    for member in stored.values():
        if member.id in seen or member.removed_at is not None:
            continue
        member.removed_at = now
        member.removed_by_fencer_id = actor_fencer_id
        record(member, RosterChangeKind.REMOVED)

    if added:
        # the log points at a member by its identity, which a new row does not
        # have until it reaches the database
        session.flush()
        for member in added:
            record(member, RosterChangeKind.ADDED)
        # A member is a row of the fencer list and carries a fixed number,
        # allocated where the row is born — here, since this is the one place a
        # member is added (spec etl-console, Fixed fencer number). Removal
        # retires the number rather than releasing it, and a restore above
        # returns it: the id is the member's identity, so the number it already
        # holds is still its own and nothing is minted for it.
        rownumbers.allocate(session, tournament, [f"mem:{member.id}" for member in added])


def roster_log(session: Session, team: Team) -> list[RosterChange]:
    """The team's roster log, most recent first. Append-only: nothing edits or
    deletes an entry while the team exists."""
    return list(
        session.scalars(
            select(RosterChange)
            .where(RosterChange.team_id == team.id)
            .order_by(RosterChange.created_at.desc(), RosterChange.id.desc())
        ).all()
    )
