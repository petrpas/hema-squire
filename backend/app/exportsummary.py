"""The Export phase's summary: how many of each thing the tournament offers,
paid and unpaid (spec export-summary).

One computation, read by the console's Summary tab and by the Sheets export's
Summary worksheet alike, so the two never state different totals. A line is
returned structured — which discipline or item, which answer to its option —
rather than as a finished label, because the label is composed in the language
the reader asked for: the console's own, or English for what leaves it.

Lines are derived from the offer, not from what was chosen: an item nobody
chose still has its line at 0 and 0, and a category the tournament does not
offer has none.
"""

from collections import defaultdict
from dataclasses import dataclass

from app import exporttables
from app.models import ExtraItem, Tournament
from app.rules import Row

DISCIPLINE = "discipline"
QUEUE = "queue"
ITEM = "item"


@dataclass(frozen=True)
class SummaryLine:
    """One line of the summary.

    `name` is the discipline's or the item's own name, as the organizer wrote
    it. `option` is the answer an item line stands for, and None on a line for
    the whole item. `missing` marks the line counting selections that gave no
    answer to an item asking one. `category` is empty on a discipline's lines.
    """

    kind: str
    category: str
    name: str
    paid: int
    unpaid: int
    option: str | None = None
    missing: bool = False
    # the item a line counts, None on a discipline's lines: two items may
    # share a name, and a reader keying lines needs to tell them apart
    item_id: int | None = None


class _Tally:
    """Paid and unpaid counts under keys, remembering the order keys first
    arrived in — which is registration order, the order the rows come in."""

    def __init__(self) -> None:
        self.counts: dict[str, list[int]] = {}

    def add(self, key: str, paid: bool, amount: int = 1) -> None:
        pair = self.counts.setdefault(key, [0, 0])
        pair[0 if paid else 1] += amount

    def get(self, key: str) -> tuple[int, int]:
        paid, unpaid = self.counts.get(key, [0, 0])
        return paid, unpaid


def _discipline_lines(tournament: Tournament, rows: list[Row]) -> list[SummaryLine]:
    """A discipline's seated fencers, then its queue where anybody is in it.

    Split as `exporttables.tab_counts` splits a discipline's tab, so the
    summary and the tab give one answer. A tournament whose conduct creates no
    substitute placements holds no `substitute_for`, and so no queue line.
    """
    lines: list[SummaryLine] = []
    for discipline in exporttables.individual_disciplines(tournament):
        name = discipline.name or discipline.slug
        seated = _Tally()
        queued = _Tally()
        for row in rows:
            paid = bool(row.get("paid"))
            if discipline.slug in (row.get("disciplines") or []):
                seated.add("", paid)
            elif discipline.slug in (row.get("substitute_for") or []):
                queued.add("", paid)
        lines.append(SummaryLine(DISCIPLINE, "", name, *seated.get("")))
        if queued.counts:
            lines.append(SummaryLine(QUEUE, "", name, *queued.get("")))
    return lines


def _fold(answer: str) -> str:
    return answer.strip().casefold()


def _item_lines(item: ExtraItem, selections: list[tuple[dict, bool]]) -> list[SummaryLine]:
    """An item's lines: one for the whole item where it asks no option, one per
    answer where it does (spec export-summary, An item counts pieces, broken
    down by its option). Each counts pieces — the selection's quantity."""
    category = item.category.value

    def line(paid: int, unpaid: int, option: str | None = None, missing: bool = False):
        return SummaryLine(ITEM, category, item.name, paid, unpaid, option, missing, item.id)

    if not item.takes_option:
        # an answer left over from before the option was removed counts for
        # the item all the same
        whole = _Tally()
        for selection, paid in selections:
            whole.add("", paid, selection.get("qty") or 1)
        return [line(*whole.get(""))]

    answers = _Tally()
    spelling: dict[str, str] = {}
    missing = _Tally()
    for selection, paid in selections:
        qty = selection.get("qty") or 1
        answer = (selection.get("option") or "").strip()
        if not answer:
            missing.add("", paid, qty)
            continue
        key = _fold(answer)
        spelling.setdefault(key, answer)
        answers.add(key, paid, qty)

    lines: list[SummaryLine] = []
    declared = [choice for choice in item.option_choices if isinstance(choice, str)]
    declared_keys = {_fold(choice) for choice in declared}
    for choice in declared:
        lines.append(line(*answers.get(_fold(choice)), option=choice))
    # a free-text answer, or one given before the choices were edited: in the
    # order answers first arrived, after whatever the organizer declared
    for key in answers.counts:
        if key not in declared_keys:
            lines.append(line(*answers.get(key), option=spelling[key]))
    if missing.counts:
        lines.append(line(*missing.get(""), missing=True))
    if not lines:
        # a free-text item nobody chose: still offered, so still stated
        lines.append(line(0, 0))
    return lines


def summary_lines(tournament: Tournament, rows: list[Row]) -> list[SummaryLine]:
    """The summary of the replayed fencer table: disciplines first, then every
    offered item, category by category in the band's order and in the order
    the tournament holds its items within one.

    Paid is the row's settled state, the same the paid column of every tab
    states: settlement belongs to the registration, so every entry and item of
    an unsettled one counts as unpaid. A row a deletion took out counts
    nowhere.
    """
    live = [row for row in rows if not row.get("_deleted")]
    lines = _discipline_lines(tournament, live)

    by_item: dict[int, list[tuple[dict, bool]]] = defaultdict(list)
    for row in live:
        paid = bool(row.get("paid"))
        for selections in (row.get("extras") or {}).values():
            for selection in selections:
                item_id = selection.get("item_id")
                if isinstance(item_id, int):
                    by_item[item_id].append((selection, paid))

    items = sorted(tournament.extra_items, key=lambda item: item.id)
    for category in exporttables.offered_categories(tournament):
        for item in items:
            if item.category is category:
                lines += _item_lines(item, by_item.get(item.id, []))
    return lines
