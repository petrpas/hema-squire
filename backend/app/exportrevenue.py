"""The Export phase's revenue: what each thing the tournament sells has brought
in and has still to bring, and how that agrees with the payment journal (spec
export-revenue).

One computation, read by the console's Revenue tab and by the Sheets export's
Revenue worksheet alike. Lines are returned structured — which discipline,
item or discount, at which price — and the labels are composed in the reader's
language, as `exportsummary` does it.

The lines count over the replayed rows, as Summary does, so the two tabs never
disagree about who is in; each row is then priced through the registration
behind it (`pricing.registration_breakdown`). Paid is the registration's
settled state. A deposit or a partial payment is not spread over items: the
reconciliation states it instead, beside every other credit the journal holds.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app import exporttables, pricing
from app.models import (
    Discipline,
    DisciplineKind,
    ExtraItem,
    Registration,
    RegistrationDiscipline,
    RegistrationExtra,
    RegistrationState,
    Team,
    Tournament,
)
from app.rules import Row

# kinds of a priced block's line
ITEM = "item"
# a legacy tournament's flat rental or afterparty fee, which bills no item and
# is named by its block
FEE = "fee"
DISCOUNT = "discount"
TOTAL = "total"
GRAND_TOTAL = "grand_total"

# the block of entry fees: individual disciplines, then team disciplines
ENTRY = ""

# kinds of a reconciliation line, in the order the table states them (design
# export-revenue D7)
PAID_BY_ITEMS = "paid_by_items"
CREDITED_SETTLED = "credited_settled"
DIFFERENCE = "difference"
WAIVED = "waived"
WAIVED_CREDITED = "waived_credited"
DEPOSITS = "deposits"
QUEUE = "queue"
CANCELLED = "cancelled"
DELETED = "deleted"
UNISSUED = "unissued"
JOURNAL = "journal"

LANES = ("local", "eur")


@dataclass(frozen=True)
class RevenueLine:
    """One line of a priced block, in whole local-currency units.

    `name` is the organizer's: the discipline's, the item's or the discount's,
    and empty on a total or a legacy fee line. `price` is the unit price; on a
    discount, its configured effect with a minus — an amount, or a percentage
    where `percent` says so — and None on a total. `paid` and `to_pay` are
    negative on a discount.
    """

    kind: str
    name: str
    price: int | float | None
    paid_count: int
    count: int
    paid: int
    to_pay: int
    percent: bool = False


@dataclass(frozen=True)
class RevenueBlock:
    """One table: the entry fees under `ENTRY`, or one category under its
    value. Its last line is its total."""

    key: str
    lines: list[RevenueLine]


@dataclass(frozen=True)
class ReconciliationLine:
    """One line of the reconciliation, in cents of its lane's currency.

    `lane` is None on a line stating a count alone. `count` is the number of
    registrations or rows the line speaks of, where it speaks of any."""

    kind: str
    lane: str | None
    amount_cents: int | None
    count: int | None = None


@dataclass(frozen=True)
class Revenue:
    blocks: list[RevenueBlock]
    total: RevenueLine
    reconciliation: list[ReconciliationLine]


@dataclass
class _Tally:
    """Pieces or registrations under one key, split by settled."""

    paid_count: int = 0
    count: int = 0
    paid: int = 0
    to_pay: int = 0

    def add(self, settled: bool, pieces: int, amount: int) -> None:
        self.count += pieces
        if settled:
            self.paid_count += pieces
            self.paid += amount
        else:
            self.to_pay += amount


@dataclass
class _Block:
    # (subject, unit price) → tally, for the priced pieces
    pieces: dict[tuple[str, int], _Tally] = field(default_factory=dict)
    # discount index → tally of the registrations it deducted from here
    discounts: dict[int, _Tally] = field(default_factory=dict)
    holders: _Tally = field(default_factory=_Tally)


def _subject_key(piece: pricing.PricedPiece) -> str:
    if isinstance(piece.subject, Discipline):
        return f"discipline:{piece.subject.slug}"
    if isinstance(piece.subject, ExtraItem):
        return f"item:{piece.subject.id}"
    return f"fee:{piece.category}"


def _discipline_order(tournament: Tournament) -> list[Discipline]:
    """Individual disciplines in the tournament's order, then its team ones."""
    individual = exporttables.individual_disciplines(tournament)
    teams = [d for d in tournament.disciplines if d.kind is DisciplineKind.TEAM]
    return [*individual, *teams]


def _block_keys(tournament: Tournament, blocks: dict[str, _Block]) -> list[str]:
    """Entry fees, then the offered categories in the band's order. A legacy
    tournament offers no items, and its flat-fee rental and afterparty take
    the place of their categories where anybody holds one."""
    offered = [category.value for category in exporttables.offered_categories(tournament)]
    legacy = [
        key
        for key in (pricing.LEGACY_RENTAL, pricing.LEGACY_AFTERPARTY)
        if key in blocks and key not in offered
    ]
    return [ENTRY, *offered, *legacy]


def _subjects(tournament: Tournament, key: str) -> list[tuple[str, str, int, str]]:
    """What a block offers, in its order: (subject key, name, regular price,
    line kind). The regular price is where a line nobody bought stands."""
    if key == ENTRY:
        return [
            (f"discipline:{d.slug}", d.name or d.slug, d.fee or 0, ITEM)
            for d in _discipline_order(tournament)
        ]
    items = sorted(tournament.extra_items, key=lambda item: item.id)
    subjects = [
        (f"item:{item.id}", item.name, item.price or 0, ITEM)
        for item in items
        if item.category.value == key
    ]
    if not subjects:
        # a legacy flat fee: one subject, named by its block
        subjects = [(f"fee:{key}", "", 0, FEE)]
    return subjects


def _effect_price(effect: dict) -> tuple[int | float, bool]:
    """A discount's configured effect, with its minus."""
    value = effect.get("value") or 0
    if effect.get("kind") == "percent":
        return -value, True
    return -int(value), False


def _lines(tournament: Tournament, key: str, block: _Block) -> list[RevenueLine]:
    lines: list[RevenueLine] = []
    for subject, name, regular, kind in _subjects(tournament, key):
        prices = sorted((price for (held, price) in block.pieces if held == subject), reverse=True)
        if not prices:
            if kind == FEE:
                continue
            lines.append(RevenueLine(kind, name, regular, 0, 0, 0, 0))
            continue
        for price in prices:
            tally = block.pieces[(subject, price)]
            lines.append(
                RevenueLine(
                    kind, name, price, tally.paid_count, tally.count, tally.paid, tally.to_pay
                )
            )
    discounts = tournament.discounts or []
    for index in sorted(block.discounts):
        if index >= len(discounts):
            continue
        tally = block.discounts[index]
        price, percent = _effect_price(discounts[index].get("effect", {}))
        lines.append(
            RevenueLine(
                DISCOUNT,
                discounts[index].get("name", ""),
                price,
                tally.paid_count,
                tally.count,
                -tally.paid,
                -tally.to_pay,
                percent,
            )
        )
    holders = block.holders
    lines.append(
        RevenueLine(
            TOTAL,
            "",
            None,
            holders.paid_count,
            holders.count,
            sum(line.paid for line in lines),
            sum(line.to_pay for line in lines),
        )
    )
    return lines


def _counted(
    rows: list[Row], registrations: dict[int, Registration]
) -> tuple[list[Registration], int]:
    """The registrations whose pieces stand on a line, in row order, and how
    many live rows have no registration behind them.

    A row a deletion took out counts on no line, and neither does a waived
    registration (no money came, none is owed), a cancelled or expired one, or
    one waiting wholly in the queue, which `pricing` bills nothing."""
    counted: list[Registration] = []
    unissued = 0
    for row in rows:
        if row.get("_deleted"):
            continue
        registration_id = row.get("registration_id")
        if not isinstance(registration_id, int):
            unissued += 1
            continue
        registration = registrations.get(registration_id)
        if registration is None or _outside_lines(registration):
            continue
        counted.append(registration)
    return counted, unissued


def _lifecycle_ended(registration: Registration) -> bool:
    return registration.state in (RegistrationState.CANCELLED, RegistrationState.EXPIRED)


def _outside_lines(registration: Registration) -> bool:
    return _lifecycle_ended(registration) or registration.waived or registration.waiting_in_queue


def _priced(
    tournament: Tournament, registrations: Iterable[Registration]
) -> tuple[dict[str, _Block], _Tally]:
    blocks: dict[str, _Block] = {}
    everyone = _Tally()
    for registration in registrations:
        breakdown = pricing.registration_breakdown(registration, tournament)
        if not breakdown.pieces:
            continue
        settled = registration.settled
        everyone.add(settled, 1, 0)
        held: set[str] = set()
        for piece in breakdown.pieces:
            key = ENTRY if piece.category == pricing.DISCIPLINE_CATEGORY else piece.category
            block = blocks.setdefault(key, _Block())
            tally = block.pieces.setdefault((_subject_key(piece), piece.unit_price), _Tally())
            tally.add(settled, piece.qty, piece.unit_price * piece.qty)
            if piece.qty > 0 and key not in held:
                held.add(key)
                block.holders.add(settled, 1, 0)
        for deduction in breakdown.deductions:
            key = ENTRY if deduction.category == pricing.DISCIPLINE_CATEGORY else deduction.category
            block = blocks.setdefault(key, _Block())
            block.discounts.setdefault(deduction.position, _Tally()).add(
                settled, 1, deduction.deducted
            )
    return blocks, everyone


def _value_cents(tournament: Tournament, registrations: Iterable[Registration]) -> int:
    """What the registrations' selections are worth at their prices, net of
    their discounts — the lines they would stand on, were they counted."""
    total = 0
    for registration in registrations:
        breakdown = pricing.registration_breakdown(registration, tournament)
        total += sum(piece.unit_price * piece.qty for piece in breakdown.pieces)
        total -= sum(deduction.deducted for deduction in breakdown.deductions)
    return total * 100


def _credited(registrations: Iterable[Registration], lane: str) -> int:
    return sum(registration.credited_in(lane) for registration in registrations)


def _reconciliation(
    tournament: Tournament,
    rows: list[Row],
    registrations: list[Registration],
    counted: list[Registration],
    unissued: int,
    paid_by_items: int,
) -> list[ReconciliationLine]:
    """The paid figure set beside the journal (design export-revenue D7).

    Every registration of the tournament with a credit falls in exactly one
    bucket, the first that holds it — a lifecycle that ended, a row a deletion
    took out, a waiver, the queue, then settled or not — so that the buckets
    sum to the journal in each lane."""
    lanes = [lane for lane in LANES if lane == "local" or tournament.shows_eur]
    on_live_row = {row.get("registration_id") for row in rows if not row.get("_deleted")}
    counted_ids = {registration.id for registration in counted}
    ended: list[Registration] = []
    deleted: list[Registration] = []
    waived: list[Registration] = []
    queued: list[Registration] = []
    settled: list[Registration] = []
    unsettled: list[Registration] = []
    for registration in registrations:
        if _lifecycle_ended(registration):
            ended.append(registration)
        elif registration.id not in on_live_row:
            deleted.append(registration)
        elif registration.waived:
            waived.append(registration)
        elif registration.waiting_in_queue:
            queued.append(registration)
        elif registration.settled and registration.id in counted_ids:
            settled.append(registration)
        else:
            unsettled.append(registration)

    def per_lane(kind: str, group: list[Registration], count: int | None = None):
        return [ReconciliationLine(kind, lane, _credited(group, lane), count) for lane in lanes]

    lines = [ReconciliationLine(PAID_BY_ITEMS, "local", paid_by_items * 100)]
    lines += per_lane(CREDITED_SETTLED, settled)
    lines.append(
        # what arrived less what the items cost: a shortfall reads negative,
        # as money missing does (owner decision, 2026-10-08)
        ReconciliationLine(DIFFERENCE, "local", _credited(settled, "local") - paid_by_items * 100)
    )
    lines.append(ReconciliationLine(WAIVED, "local", _value_cents(tournament, waived), len(waived)))
    lines += per_lane(WAIVED_CREDITED, waived)
    lines += per_lane(DEPOSITS, unsettled)
    lines += per_lane(QUEUE, queued)
    lines += per_lane(CANCELLED, ended)
    # a row deleted on the fencer list leaves its registration and its money
    # standing; stated only where it holds some, since the console has no
    # other place that says where that money went
    if any(_credited(deleted, lane) for lane in lanes):
        lines += per_lane(DELETED, deleted, len(deleted))
    lines.append(ReconciliationLine(UNISSUED, None, None, unissued))
    lines += per_lane(JOURNAL, registrations)
    return lines


def revenue(tournament: Tournament, rows: list[Row], registrations: list[Registration]) -> Revenue:
    """The Revenue tab of the replayed fencer table.

    `registrations` is every registration of the tournament, cancelled ones
    included, with their credits: the lines read those behind live rows, and
    the reconciliation reads them all, since the journal holds money on
    registrations no row shows any more.
    """
    by_id = {registration.id: registration for registration in registrations}
    counted, unissued = _counted(rows, by_id)
    priced, everyone = _priced(tournament, counted)
    blocks = [
        RevenueBlock(key, _lines(tournament, key, priced.get(key, _Block())))
        for key in _block_keys(tournament, priced)
    ]
    totals = [block.lines[-1] for block in blocks]
    total = RevenueLine(
        GRAND_TOTAL,
        "",
        None,
        everyone.paid_count,
        everyone.count,
        sum(line.paid for line in totals),
        sum(line.to_pay for line in totals),
    )
    reconciliation = _reconciliation(tournament, rows, registrations, counted, unissued, total.paid)
    return Revenue(blocks, total, reconciliation)


def tournament_registrations(session: Session, tournament: Tournament) -> list[Registration]:
    """Every registration of the tournament, cancelled ones included, with
    what pricing and the journal read of each loaded in one pass."""
    return list(
        session.scalars(
            select(Registration)
            .where(Registration.tournament_id == tournament.id)
            .options(
                selectinload(Registration.entries).selectinload(RegistrationDiscipline.discipline),
                selectinload(Registration.teams).selectinload(Team.discipline),
                selectinload(Registration.extra_selections).selectinload(RegistrationExtra.item),
                selectinload(Registration.credits),
                selectinload(Registration.waivers),
            )
            .order_by(Registration.registered_at)
        ).all()
    )
