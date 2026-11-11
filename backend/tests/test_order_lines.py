"""What an order is made of, as the Payments registration table unfolds it
(spec payments-console, Every order unfolds into its priced lines / Queued
placements are shown and not counted)."""

from app import pricing
from app.models import DisciplineKind, DiscountCode, ExtraCategory
from tests.test_export_revenue import (
    both_disciplines,
    discipline,
    item,
    make_tournament,
    register,
)


def counted(lines: list[pricing.OrderLine]) -> int:
    return sum(line.amount for line in lines if not line.queued)


def test_a_mixed_order_sums_to_its_total_and_names_each_team():
    tournament = make_tournament(discounts=[both_disciplines(300)])
    longsword = discipline(tournament, "ls", 800)
    sabre = discipline(tournament, "sabre", 700)
    teams = discipline(tournament, "team-sabre", 1200, kind=DisciplineKind.TEAM)
    mask = item(tournament, 1, "Mask", ExtraCategory.RENTAL, 150)
    tournament.extra_items = [mask]
    registration = register(
        tournament, seated=[longsword, sabre], teams=[teams, teams], extras=[(mask, 3)]
    )
    registration.teams[0].name = "Hema Praha A"
    registration.teams[1].name = "Hema Praha B"

    lines = pricing.registration_lines(registration, tournament)

    assert [(line.kind, line.label, line.amount) for line in lines] == [
        ("team", "Hema Praha A", 1200),
        ("team", "Hema Praha B", 1200),
        ("discipline", None, 800),
        ("discipline", None, 700),
        ("item", "Mask", 450),
        ("discount", "Both disciplines", -300),
    ]
    assert counted(lines) == registration.total_amount


def test_queued_placements_stand_beside_the_total_and_outside_it():
    tournament = make_tournament()
    longsword = discipline(tournament, "ls", 800)
    sabre = discipline(tournament, "sabre", 700)
    teams = discipline(tournament, "team-sabre", 1200, kind=DisciplineKind.TEAM)
    registration = register(tournament, seated=[longsword], queued=[sabre], teams=[teams, teams])
    registration.teams[1].waitlisted = True
    pricing.reprice(registration, tournament)

    lines = pricing.registration_lines(registration, tournament)

    assert [(line.kind, line.queued) for line in lines] == [
        ("team", False),
        ("team", True),
        ("discipline", False),
        ("discipline", True),
    ]
    assert counted(lines) == registration.total_amount == 2000


def test_a_wholly_queued_order_bills_nothing_its_extras_included():
    tournament = make_tournament()
    sabre = discipline(tournament, "sabre", 700)
    mask = item(tournament, 1, "Mask", ExtraCategory.RENTAL, 150)
    tournament.extra_items = [mask]
    registration = register(tournament, queued=[sabre], extras=[(mask, 1)])

    lines = pricing.registration_lines(registration, tournament)

    assert all(line.queued for line in lines)
    assert counted(lines) == registration.total_amount == 0


def test_a_code_is_a_line_of_its_own():
    tournament = make_tournament()
    longsword = discipline(tournament, "ls", 1000)
    code = DiscountCode(
        id=3, code="trener", name="Trenéři", effect={"kind": "fixed", "value": 200}, scope=[]
    )
    tournament.discount_codes.append(code)
    registration = register(tournament, seated=[longsword])
    registration.discount_code = code
    pricing.reprice(registration, tournament)

    lines = pricing.registration_lines(registration, tournament)

    assert (lines[-1].kind, lines[-1].label, lines[-1].amount) == ("code", "Trenéři", -200)
    assert counted(lines) == registration.total_amount == 800


def test_a_legacy_tournament_states_its_flat_fees():
    tournament = make_tournament(weapon_rental_fee=100, afterparty_fee=300)
    longsword = discipline(tournament, "ls", 800)
    registration = register(tournament, seated=[longsword])
    registration.weapon_rentals = ["ls", "sabre"]
    registration.afterparty = True
    pricing.reprice(registration, tournament)

    lines = pricing.registration_lines(registration, tournament)

    assert [(line.kind, line.qty, line.amount) for line in lines] == [
        ("discipline", 1, 800),
        (pricing.LEGACY_RENTAL, 2, 200),
        (pricing.LEGACY_AFTERPARTY, 1, 300),
    ]
    assert counted(lines) == registration.total_amount


def test_a_price_changed_after_issuing_shows_against_the_stored_total():
    tournament = make_tournament()
    mask = item(tournament, 1, "Mask", ExtraCategory.RENTAL, 150)
    tournament.extra_items = [mask]
    longsword = discipline(tournament, "ls", 800)
    registration = register(tournament, seated=[longsword], extras=[(mask, 3)])
    mask.price = 200

    lines = pricing.registration_lines(registration, tournament)

    assert registration.total_amount == 1250
    assert counted(lines) - registration.total_amount == 150
