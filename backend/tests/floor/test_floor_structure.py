"""Pool structure and the bracket (spec floor-planner, Pool structure follows
the format and the hard rule). No database."""

from hypothesis import given
from hypothesis import strategies as st

from app.floor.engine import structure
from app.floor.engine.variants import plan
from tests.floor.engine_fixtures import discipline, fmt, problem


def test_feasible_pool_counts():
    # N = 29 in 5–7: k = 5 gives 6 and 5; k = 4 gives 8 and 7; k = 6 gives 5 and 4
    assert structure.pool_counts(29, 5, 7) == (5,)
    assert structure.pool_sizes(29, 5) == (6, 6, 6, 6, 5)


def test_no_k_fits_is_reported_with_n_and_range():
    result = plan(problem(discipline(1, 4, format=fmt(5, 7))))

    assert result.variants == ()
    assert result.infeasible is not None
    assert (result.infeasible.reason, result.infeasible.subject) == ("structure", "1")
    assert result.infeasible.detail == "N=4 5-7"


def test_byes_fill_the_bracket():
    shape = structure.bracket(20)

    assert (shape.size, shape.byes) == (32, 12)
    # four bouts in the first round, then 16 left
    assert shape.rounds == (4, 8, 4, 2, 1)


@given(n=st.integers(1, 200), lo=st.integers(3, 10), hi=st.integers(3, 10))
def test_every_k_returned_is_in_range_and_sizes_differ_by_one(n, lo, hi):
    for k in structure.pool_counts(n, lo, hi):
        sizes = structure.pool_sizes(n, k)
        assert sum(sizes) == n
        assert max(sizes) - min(sizes) <= 1
        assert lo <= min(sizes) and max(sizes) <= hi


@given(n=st.integers(1, 200), lo=st.integers(3, 10), hi=st.integers(3, 10))
def test_no_k_left_out(n, lo, hi):
    found = set(structure.pool_counts(n, lo, hi))
    for k in range(1, n + 1):
        sizes = structure.pool_sizes(n, k)
        fits = lo <= min(sizes) and max(sizes) <= hi
        assert fits == (k in found)


@given(a=st.integers(2, 300))
def test_the_bracket_is_the_least_power_of_two_holding_a(a):
    shape = structure.bracket(a)

    assert shape.size >= a and shape.size // 2 < a
    assert shape.size & (shape.size - 1) == 0
    # every seed but the winner loses exactly one bout
    assert sum(shape.rounds) == a - 1
