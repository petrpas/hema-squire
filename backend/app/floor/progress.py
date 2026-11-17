"""What has started on the floor, for re-planning (design add-floor-planner
D7).

A registry: each later floor change that records progress — pools, the
bracket — registers a source here, and `started` asks them all. Nothing
registers in `add-floor-planner`, so re-planning freezes nothing yet. Modules
meet here rather than importing one another.
"""

from collections.abc import Callable
from datetime import datetime

from sqlalchemy.orm import Session

# (session, tournament id, now) → activity ids that have started
Source = Callable[[Session, int, datetime], set[str]]

_sources: list[Source] = []


def register(source: Source) -> None:
    _sources.append(source)


def started(session: Session, tournament_id: int, now: datetime) -> set[str]:
    found: set[str] = set()
    for source in _sources:
        found |= source(session, tournament_id, now)
    return found


# (session, tournament id, discipline id) → minutes behind the published plan
# (positive) or ahead, None where nothing has started
Slip = Callable[[Session, int, int], int | None]

_slips: list[Slip] = []


def register_slip(source: Slip) -> None:
    _slips.append(source)


def slip(session: Session, tournament_id: int, discipline_id: int) -> int | None:
    """The latest any registered step reports, for the `today` matrix."""
    found = [s(session, tournament_id, discipline_id) for s in _slips]
    known = [value for value in found if value is not None]
    return known[-1] if known else None
