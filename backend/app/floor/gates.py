"""What reopening a gate discards, and what refuses it (design
add-floor-checkin D4).

A registry, so that floor modules meet here rather than importing one
another: `floor-pools` registers its draw as discarded by reopening check-in,
and its recorded bouts as refusing it. Check-in asks this module and never
imports the pools.
"""

from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy.orm import Session

# (session, tournament id, discipline id) → what would be discarded, as codes
Describe = Callable[[Session, int, int], list[str]]
# (session, tournament id, discipline id) → None; discards it
Discard = Callable[[Session, int, int], None]
# (session, tournament id, discipline id) → what refuses reopening, as codes
Refuse = Callable[[Session, int, int], list[str]]


@dataclass(frozen=True)
class Hook:
    describe: Describe
    discard: Discard
    refuse: Refuse


_hooks: dict[str, list[Hook]] = {}


def register(gate: str, hook: Hook) -> None:
    """`gate` is a gate's name, such as "checkin"."""
    _hooks.setdefault(gate, []).append(hook)


def invalidated(session: Session, gate: str, tid: int, discipline: int) -> list[str]:
    return [
        code for hook in _hooks.get(gate, []) for code in hook.describe(session, tid, discipline)
    ]


def refusals(session: Session, gate: str, tid: int, discipline: int) -> list[str]:
    return [code for hook in _hooks.get(gate, []) for code in hook.refuse(session, tid, discipline)]


def discard(session: Session, gate: str, tid: int, discipline: int) -> None:
    for hook in _hooks.get(gate, []):
        hook.discard(session, tid, discipline)
