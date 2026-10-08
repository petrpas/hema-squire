"""The Export revenue: how each line is priced and counted, where a discount
stands, the totals, and the reconciliation against the journal (spec
export-revenue)."""

from collections.abc import Sequence
from datetime import UTC, date, datetime

from app import exportrevenue, pricing
from app.exportrevenue import RevenueLine
from app.models import (
    CreditOrigin,
    CreditSource,
    Currency,
    Discipline,
    DisciplineKind,
    ExtraCategory,
    ExtraItem,
    PaymentCredit,
    PaymentWaiver,
    Registration,
    RegistrationDiscipline,
    RegistrationExtra,
    RegistrationState,
    Team,
    Tournament,
)

EARLY = datetime(2026, 4, 1, 12, 0, tzinfo=UTC)
LATE = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)


def make_tournament(**kwargs) -> Tournament:
    defaults = dict(
        slug="t",
        display_name="T",
        date=date(2026, 10, 3),
        discounts=[],
        extra_items=[],
        disciplines=[],
        organizers=[],
        vs_year=2026,
        vs_series=1,
        local_currency=Currency.CZK,
        eur_payments_enabled=False,
        amount_tolerance_percent=0,
        weapon_rental_fee=0,
        afterparty_fee=0,
    )
    return Tournament(**{**defaults, **kwargs})


def discipline(
    tournament: Tournament,
    slug: str,
    fee: int,
    kind: DisciplineKind = DisciplineKind.INDIVIDUAL,
    **kwargs,
) -> Discipline:
    made = Discipline(
        kind=kind,
        tournament=tournament,
        slug=slug,
        name=slug,
        weapon=slug,
        gender="",
        material="",
        capacity=99,
        fee=fee,
        **kwargs,
    )
    return made


def item(tournament: Tournament, item_id: int, name: str, category: ExtraCategory, price: int):
    return ExtraItem(
        id=item_id, tournament=tournament, name=name, category=category, price=price, max_qty=9
    )


_ids = iter(range(1, 10_000))


def register(
    tournament: Tournament,
    seated: Sequence[Discipline] = (),
    queued: Sequence[Discipline] = (),
    extras: Sequence[tuple[ExtraItem, int]] = (),
    teams: Sequence[Discipline] = (),
    credits: Sequence[tuple[int, Currency]] = (),
    waived: bool = False,
    state: RegistrationState = RegistrationState.RESERVED,
    at: datetime = LATE,
) -> Registration:
    registration = Registration(
        id=next(_ids),
        tournament=tournament,
        registered_at=at,
        state=state,
        entries=[RegistrationDiscipline(discipline=d, is_substitute=False) for d in seated]
        + [RegistrationDiscipline(discipline=d, is_substitute=True) for d in queued],
        extra_selections=[RegistrationExtra(item=i, qty=qty) for i, qty in extras],
        teams=[Team(discipline=d, waitlisted=False, name="team") for d in teams],
        weapon_rentals=[],
        credits=[
            PaymentCredit(
                amount_cents=cents,
                currency=currency,
                value_date=date(2026, 6, 2),
                source_kind=CreditSource.MANUAL_PAYMENT,
                source_id=next(_ids),
                origin=CreditOrigin.RECORDED,
            )
            for cents, currency in credits
        ],
        waivers=[PaymentWaiver(granted_by="organizer")] if waived else [],
    )
    pricing.reprice(registration, tournament)
    return registration


def paying(tournament: Tournament, **kwargs) -> Registration:
    """A registration credited exactly its total, so settled."""
    registration = register(tournament, **kwargs)
    return with_credit(registration, registration.total_amount * 100)


def with_credit(
    registration: Registration, cents: int, currency: Currency = Currency.CZK
) -> Registration:
    registration.credits.append(
        PaymentCredit(
            amount_cents=cents,
            currency=currency,
            value_date=date(2026, 6, 2),
            source_kind=CreditSource.MANUAL_PAYMENT,
            source_id=next(_ids),
            origin=CreditOrigin.RECORDED,
        )
    )
    return registration


def row(registration: Registration | None, deleted: bool = False) -> dict:
    return {
        "registration_id": None if registration is None else registration.id,
        "paid": registration is not None and registration.settled,
        "_deleted": deleted,
    }


def compute(tournament: Tournament, registrations: list[Registration], rows=None):
    rows = rows if rows is not None else [row(r) for r in registrations]
    return exportrevenue.revenue(tournament, rows, registrations)


def lines(revenue, key: str = exportrevenue.ENTRY) -> list[tuple]:
    block = next(block for block in revenue.blocks if block.key == key)
    return [_flat(line) for line in block.lines]


def _flat(line: RevenueLine) -> tuple:
    return (line.kind, line.name, line.price, line.paid_count, line.count, line.paid, line.to_pay)


def reconciliation(revenue) -> dict[tuple[str, str | None], int | None]:
    return {(line.kind, line.lane): line.amount_cents for line in revenue.reconciliation}


def test_a_line_is_price_times_count():
    tournament = make_tournament()
    sabre = discipline(tournament, "Sabre Open", 500)
    regs = [paying(tournament, seated=[sabre]) for _ in range(12)]
    regs += [register(tournament, seated=[sabre]) for _ in range(6)]

    assert lines(compute(tournament, regs))[0] == ("item", "Sabre Open", 500, 12, 18, 6000, 3000)


def test_two_prices_two_lines_the_higher_first():
    tournament = make_tournament(early_bird_until=date(2026, 5, 1))
    longsword = discipline(tournament, "Longsword", 750, fee_early=600)
    regs = [register(tournament, seated=[longsword], at=EARLY) for _ in range(10)]
    regs += [register(tournament, seated=[longsword], at=LATE) for _ in range(8)]

    assert lines(compute(tournament, regs))[:2] == [
        ("item", "Longsword", 750, 0, 8, 0, 6000),
        ("item", "Longsword", 600, 0, 10, 0, 6000),
    ]


def test_an_item_counts_pieces_not_people():
    tournament = make_tournament()
    sabre = discipline(tournament, "Sabre", 0)
    shirt = item(tournament, 1, "T-shirt", ExtraCategory.MERCH, 300)
    tournament.extra_items = [shirt]
    regs = [paying(tournament, seated=[sabre], extras=[(shirt, 2)])]

    assert lines(compute(tournament, regs), "merch")[0] == ("item", "T-shirt", 300, 2, 2, 600, 0)


def test_a_euro_payer_counts_at_the_crown_price():
    tournament = make_tournament(eur_payments_enabled=True)
    longsword = discipline(tournament, "Longsword", 750, fee_eur=30)
    euro = with_credit(register(tournament, seated=[longsword]), 3000, Currency.EUR)
    revenue = compute(tournament, [euro])

    assert lines(revenue)[0] == ("item", "Longsword", 750, 1, 1, 750, 0)
    assert reconciliation(revenue)[("credited_settled", "eur")] == 3000
    assert reconciliation(revenue)[("credited_settled", "local")] == 0


def test_a_deposit_is_not_apportioned():
    tournament = make_tournament()
    longsword = discipline(tournament, "Longsword", 800)
    deposit = with_credit(register(tournament, seated=[longsword]), 30000)
    revenue = compute(tournament, [deposit])

    assert lines(revenue)[0] == ("item", "Longsword", 800, 0, 1, 0, 800)
    assert reconciliation(revenue)[("deposits", "local")] == 30000


def test_a_waived_registration_is_on_no_line():
    tournament = make_tournament()
    sabre = discipline(tournament, "Sabre Open", 500)
    regs = [paying(tournament, seated=[sabre]), register(tournament, seated=[sabre], waived=True)]
    revenue = compute(tournament, regs)

    assert lines(revenue)[0] == ("item", "Sabre Open", 500, 1, 1, 500, 0)
    waived = next(line for line in revenue.reconciliation if line.kind == "waived")
    assert (waived.count, waived.amount_cents) == (1, 50000)


def test_the_queue_owes_nothing():
    tournament = make_tournament()
    sabre = discipline(tournament, "Sabre Open", 500)
    rental = item(tournament, 1, "Mask", ExtraCategory.RENTAL, 50)
    tournament.extra_items = [rental]
    queued = register(tournament, queued=[sabre], extras=[(rental, 1)])
    revenue = compute(tournament, [queued])

    assert lines(revenue)[0] == ("item", "Sabre Open", 500, 0, 0, 0, 0)
    assert lines(revenue, "rental")[0] == ("item", "Mask", 50, 0, 0, 0, 0)


def test_a_free_item_and_a_team_still_stand():
    tournament = make_tournament()
    sabre = discipline(tournament, "Sabre", 500)
    teams = discipline(tournament, "Team LS", 1500, kind=DisciplineKind.TEAM)
    party = item(tournament, 1, "Afterparty", ExtraCategory.AFTERPARTY, 0)
    tournament.extra_items = [party]
    regs = [register(tournament, seated=[sabre], teams=[teams], extras=[(party, 1)])]
    regs += [register(tournament, teams=[teams]) for _ in range(3)]
    revenue = compute(tournament, regs)

    assert [line[1:3] for line in lines(revenue)[:2]] == [("Sabre", 500), ("Team LS", 1500)]
    assert lines(revenue)[1][4] == 4
    assert lines(revenue, "afterparty")[0] == ("item", "Afterparty", 0, 0, 1, 0, 0)


def both_disciplines(value: int, scope=("discipline",)) -> dict:
    return {
        "name": "Both disciplines",
        "condition": {"kind": "discipline_count", "count": 2},
        "effect": {"kind": "fixed", "value": value},
        "scope": list(scope),
    }


def test_a_discount_stands_in_its_block_with_a_minus():
    tournament = make_tournament(discounts=[both_disciplines(400)])
    sabre = discipline(tournament, "Sabre", 500)
    longsword = discipline(tournament, "Longsword", 750)
    regs = [paying(tournament, seated=[sabre, longsword]) for _ in range(8)]
    regs += [register(tournament, seated=[sabre, longsword]) for _ in range(4)]

    assert lines(compute(tournament, regs))[2] == (
        "discount",
        "Both disciplines",
        -400,
        8,
        12,
        -3200,
        -1600,
    )


def test_a_discount_across_two_categories_takes_its_share_in_each():
    tournament = make_tournament(discounts=[both_disciplines(500, ("discipline", "rental"))])
    sabre = discipline(tournament, "Sabre", 200)
    longsword = discipline(tournament, "Longsword", 200)
    mask = item(tournament, 1, "Mask", ExtraCategory.RENTAL, 150)
    tournament.extra_items = [mask]
    revenue = compute(
        tournament, [register(tournament, seated=[sabre, longsword], extras=[(mask, 1)])]
    )

    assert lines(revenue)[2][0::6] == ("discount", -400)
    assert lines(revenue, "rental")[1][0::6] == ("discount", -100)


def test_a_discount_nobody_got_has_no_line():
    tournament = make_tournament(discounts=[both_disciplines(400)])
    sabre = discipline(tournament, "Sabre", 500)
    revenue = compute(tournament, [paying(tournament, seated=[sabre])])

    assert all(line.kind != "discount" for block in revenue.blocks for line in block.lines)


def test_block_and_grand_totals():
    tournament = make_tournament(discounts=[both_disciplines(400)])
    sabre = discipline(tournament, "Sabre", 500)
    longsword = discipline(tournament, "Longsword", 750)
    mask = item(tournament, 1, "Mask", ExtraCategory.RENTAL, 50)
    tournament.extra_items = [mask]
    regs = [
        paying(tournament, seated=[sabre, longsword], extras=[(mask, 2)]),
        paying(tournament, seated=[sabre]),
        register(tournament, seated=[longsword], extras=[(mask, 1)]),
    ]
    revenue = compute(tournament, regs)

    # 500 + 500 + 750 − 400 paid; 750 to pay; three registrations, two settled
    assert lines(revenue)[-1] == ("total", "", None, 2, 3, 1350, 750)
    # the rental block counts the two who hold a mask
    assert lines(revenue, "rental")[-1] == ("total", "", None, 1, 2, 100, 50)
    assert _flat(revenue.total) == ("grand_total", "", None, 2, 3, 1450, 800)


def test_the_reconciliation_sums_to_the_journal_in_each_lane():
    tournament = make_tournament(eur_payments_enabled=True)
    sabre = discipline(tournament, "Sabre", 500, fee_eur=20)
    regs = [
        paying(tournament, seated=[sabre]),
        with_credit(register(tournament, seated=[sabre]), 2000, Currency.EUR),
        with_credit(register(tournament, seated=[sabre]), 10000),  # a deposit
        with_credit(register(tournament, seated=[sabre], waived=True), 20000),  # partial waiver
        with_credit(register(tournament, queued=[sabre]), 50000),  # a claim from the queue
        with_credit(register(tournament, seated=[sabre], state=RegistrationState.CANCELLED), 7000),
        with_credit(register(tournament, seated=[sabre]), 900, Currency.EUR),
    ]
    rows = [row(r) for r in regs if r.state is not RegistrationState.CANCELLED]
    rows.append(row(None))  # an imported row not yet issued
    revenue = compute(tournament, regs, rows)
    amounts = reconciliation(revenue)

    for lane in ("local", "eur"):
        parts = ("credited_settled", "waived_credited", "deposits", "queue", "cancelled")
        assert sum(amounts[(kind, lane)] or 0 for kind in parts) == amounts[("journal", lane)]
    assert amounts[("journal", "local")] == 50000 + 10000 + 20000 + 50000 + 7000
    assert amounts[("journal", "eur")] == 2000 + 900
    unissued = next(line for line in revenue.reconciliation if line.kind == "unissued")
    assert unissued.count == 1


def test_a_tolerated_shortfall_shows_in_the_difference():
    tournament = make_tournament(amount_tolerance_percent=10)
    longsword = discipline(tournament, "Longsword", 750)
    short = with_credit(register(tournament, seated=[longsword]), 70800)
    amounts = reconciliation(compute(tournament, [short]))

    assert amounts[("paid_by_items", "local")] == 75000
    assert amounts[("credited_settled", "local")] == 70800
    assert amounts[("difference", "local")] == -4200  # 42 Kč short


def test_the_account_agrees_and_the_difference_still_stands():
    tournament = make_tournament()
    sabre = discipline(tournament, "Sabre", 500)
    amounts = reconciliation(compute(tournament, [paying(tournament, seated=[sabre])]))

    assert amounts[("difference", "local")] == 0
    assert amounts[("journal", "local")] == amounts[("paid_by_items", "local")]


def test_a_forfeited_deposit_is_reconciled():
    tournament = make_tournament()
    sabre = discipline(tournament, "Sabre", 800)
    lapsed = with_credit(
        register(tournament, seated=[sabre], state=RegistrationState.EXPIRED), 30000
    )
    revenue = compute(tournament, [lapsed])
    amounts = reconciliation(revenue)

    assert lines(revenue)[0] == ("item", "Sabre", 800, 0, 0, 0, 0)
    assert amounts[("cancelled", "local")] == 30000
    assert amounts[("journal", "local")] == 30000


def test_money_on_a_deleted_row_is_stated_rather_than_lost():
    tournament = make_tournament()
    sabre = discipline(tournament, "Sabre", 500)
    gone = paying(tournament, seated=[sabre])
    revenue = compute(tournament, [gone], [row(gone, deleted=True)])
    amounts = reconciliation(revenue)

    assert lines(revenue)[0] == ("item", "Sabre", 500, 0, 0, 0, 0)
    assert amounts[("deleted", "local")] == 50000
    assert amounts[("journal", "local")] == 50000
