"""The elimination's shape (spec floor-bracket). No database."""

import re
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.floor.engine.bracket import first_round, seed_order, seed_teams, team_figure

TEMPLATES = Path(__file__).parents[2] / "app" / "floor" / "typst"


def template_order(size: int) -> list[int]:
    source = (TEMPLATES / f"elimination_{size}.typ").read_text()
    if size == 64:
        halves = [
            re.search(rf"#let seed_order_{half} = \((.*?)\)", source, re.S)
            for half in ("top", "bot")
        ]
        return [int(n) for m in halves if m for n in re.findall(r"\d+", m.group(1))]
    found = re.search(r"#let seed_order = \((.*?)\)", source, re.S)
    assert found is not None
    return [int(n) for n in re.findall(r"\d+", found.group(1))]


@pytest.mark.parametrize("size", [8, 16, 32, 64])
def test_the_order_matches_the_adopted_templates(size):
    assert seed_order(size) == template_order(size)


def test_twenty_advance_into_thirty_two():
    slots = first_round(32, 20)
    order = seed_order(32)

    byes = {order[s.position ^ 1] for s in slots if s.seed is None}
    assert byes == set(range(1, 13))
    assert order.index(1) < 16 <= order.index(2)


@given(power=st.integers(1, 6), data=st.data())
def test_seeds_one_and_two_split_and_the_byes_go_to_the_top(power, data):
    size = 2**power
    advancing = data.draw(st.integers(size // 2 + 1, size)) if size > 2 else 2
    order = seed_order(size)
    slots = first_round(size, advancing)

    assert (order.index(1) < size // 2) != (order.index(2) < size // 2)
    byes = sorted(order[s.position ^ 1] for s in slots if s.seed is None)
    assert byes == list(range(1, size - advancing + 1))


def test_teams_are_seeded_by_their_best_members():
    draci = team_figure("Draci", [2, 4, 9, 20, 31], 3)
    vlci = team_figure("Vlci", [3, 5, 6], 3)
    assert draci is not None and vlci is not None

    assert draci.figure == 5.0
    assert round(vlci.figure, 2) == 4.67
    assert seed_teams([draci, vlci]) == ["Vlci", "Draci"]


def test_a_team_short_of_k_placed_members_has_no_figure():
    assert team_figure("Short", [1, 2], 3) is None
