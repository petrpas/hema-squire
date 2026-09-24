"""Where a registration's individual placements stand: seated, or queued.

One function, called by every road that places a registration — the fencer's own
submission, their amendment, and an organizer's hand entry — so the rule is
stated once (design participation-condition D2).

Without a participation condition each discipline is placed against its own
capacity. With one, the condition is met or it is not: met, its disciplines are
seated together and the rest placed on their own; not met, every placement waits,
because a fencer who attends only if they get every discipline of the condition
holds no seat anywhere while any of them is full (spec registration,
Participation condition).
"""

from collections.abc import Iterable

from app.models import RegistrationDiscipline


def condition_unmet(entries: Iterable[RegistrationDiscipline], full: set[str]) -> bool:
    """Whether a discipline of the registration's condition has no free place."""
    return any(entry.conditional and entry.discipline.slug in full for entry in entries)


def place(entries: list[RegistrationDiscipline], full: set[str]) -> None:
    """Set `is_substitute` on a registration's individual entries.

    `full` names the disciplines with no free place for this registration —
    every discipline once seating has settled (`availability.queued_on_entry`).
    A condition that cannot be met queues every entry, inside it and outside it;
    otherwise each entry is queued exactly when its own discipline is full, which
    for a met condition seats its disciplines together."""
    if condition_unmet(entries, full):
        for entry in entries:
            entry.is_substitute = True
        return
    for entry in entries:
        entry.is_substitute = entry.discipline.slug in full
