"""Each step's state per discipline, for the `today` matrix (design
add-floor-checkin D5).

Steps in their column order. Each capability registers the state function of
its own step; a step nobody has registered reads "waiting". States are codes;
the console words them.
"""

from collections.abc import Callable

from sqlalchemy.orm import Session

STEPS = ("checkin", "pools", "bracket", "results")

# (session, tournament id, discipline id) → a state code
State = Callable[[Session, int, int], str]

_states: dict[str, State] = {}


def register(step: str, state: State) -> None:
    if step not in STEPS:
        raise ValueError(f"unknown step {step}")
    _states[step] = state


def states(session: Session, tid: int, discipline: int) -> dict[str, str]:
    return {
        step: _states[step](session, tid, discipline) if step in _states else "waiting"
        for step in STEPS
    }
