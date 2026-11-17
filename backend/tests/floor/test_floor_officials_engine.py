"""Referees on blocks (spec floor-officials). No database."""

from hypothesis import given, settings
from hypothesis import strategies as st

from app.floor.engine.model import Activity
from app.floor.engine.officials import REFEREE, Block, Official, Pin, assign, blocks, hard_ok


def activity(
    id: str, piste: int, start: int, end: int, discipline: int = 1, kind: str = "pool"
) -> Activity:
    return Activity(
        id=id,
        discipline=discipline,
        kind="pool" if kind == "pool" else "bout",
        ordinal=1,
        round=0 if kind == "pool" else 1,
        piste=piste,
        day=0,
        start=start,
        end=end,
    )


def official(
    id: int,
    *,
    club: str | None = None,
    blocked=(),
    days=(0,),
    disciplines=(1,),
    reserve=(),
    main: bool = True,
):
    return Official(
        id=id,
        disciplines=frozenset(disciplines) | frozenset(reserve),
        days=frozenset(days),
        reserve=frozenset(reserve),
        main=main,
        club=club,
        blocked=tuple(blocked),
    )


def block(key: str, start: int, end: int, *, piste: int = 1, clubs=(), needs: int = 1) -> Block:
    return Block(
        key=key,
        discipline=1,
        piste=piste,
        day=0,
        start=start,
        end=end,
        needs=needs,
        activities=(key,),
        clubs=frozenset(clubs),
    )


def test_a_wave_is_one_block():
    found = blocks(
        [
            activity("LS:pool:1", 2, 600, 645),
            activity("LS:pool:5", 2, 650, 695),
            activity("LS:pool:2", 3, 600, 645),
        ],
        pause={1: 5},
        needs={(1, "pool"): 1, (1, "elim"): 2},
    )

    assert [b.activities for b in found] == [("LS:pool:1", "LS:pool:5"), ("LS:pool:2",)]


def test_the_stage_sets_the_count():
    found = blocks(
        [activity("LS:pool:1", 1, 600, 645), activity("LS:r1:1", 1, 650, 656, kind="bout")],
        pause={1: 10},
        needs={(1, "pool"): 1, (1, "elim"): 2},
    )

    assert [(b.stage, b.needs) for b in found] == [("pool", 1), ("elim", 2)]


def test_an_official_who_fences_is_kept_off_during_their_pool():
    jan = official(1, blocked=[(0, 600, 645)])
    eva = official(2)

    result = assign([block("b", 610, 640)], [jan, eva], [])

    assert [s.official for s in result.seats] == [2]


def test_an_unfillable_place_is_stated():
    result = assign([block("b", 600, 700, needs=2)], [official(1)], [])

    assert [(s.slot, s.official) for s in result.unfilled] == [(1, None)]


def test_a_club_conflict_is_avoided_when_possible():
    result = assign(
        [block("b", 600, 700, clubs=["Rotyka"])],
        [official(1, club="Rotyka"), official(2, club="Brno")],
        [],
    )

    assert [s.official for s in result.seats] == [2]
    assert result.conflicts == ()


def test_a_pin_holds():
    result = assign(
        [block("final", 900, 960)], [official(1), official(2)], [Pin("final", REFEREE, 0, 2)]
    )

    (seat,) = result.seats
    assert (seat.official, seat.pinned) == (2, True)


def test_one_main_referee_leads_the_piste():
    petr = official(1, main=False)
    eva = official(2)

    result = assign([block("b", 600, 700, needs=2)], [petr, eva], [])

    assert [(s.slot, s.official) for s in result.seats] == [(0, 2), (1, 1)]
    assert result.without_main == ()


def test_no_main_referee_is_tolerated():
    result = assign([block("b", 600, 700)], [official(1, main=False)], [])

    assert [s.official for s in result.seats] == [1]
    assert result.unfilled == ()
    assert result.without_main == ("b",)


def test_a_reserve_fills_a_gap_only():
    regular = official(1)
    eva = official(2, disciplines=(), reserve=(1,))

    alone = assign([block("b", 600, 700)], [regular, eva], [])
    two = assign([block("b", 600, 700, needs=2)], [regular, eva], [])

    assert [s.official for s in alone.seats] == [1]
    assert sorted(s.official for s in two.seats if s.official is not None) == [1, 2]


def test_a_regular_non_main_comes_before_a_reserve_main():
    other = official(1, main=False)
    reserve_main = official(2, disciplines=(), reserve=(1,))

    result = assign([block("b", 600, 700)], [other, reserve_main], [])

    assert [s.official for s in result.seats] == [1]
    assert result.without_main == ("b",)


@settings(max_examples=20)
@given(
    spans=st.lists(
        st.tuples(st.integers(1, 4), st.integers(0, 600), st.integers(15, 120)),
        min_size=1,
        max_size=10,
    ),
    people=st.lists(
        st.tuples(st.booleans(), st.sampled_from([None, "A", "B"]), st.booleans(), st.booleans()),
        min_size=1,
        max_size=6,
    ),
)
def test_no_hard_constraint_is_ever_broken_and_the_result_is_deterministic(spans, people):
    block_list = [
        block(f"b{i}", start, start + length, piste=piste, needs=2, clubs=["A"])
        for i, (piste, start, length) in enumerate(spans)
    ]
    officials = [
        official(
            i + 1,
            club=club,
            blocked=[(0, 300, 360)] if fences else [],
            main=main,
            disciplines=() if reserve else (1,),
            reserve=(1,) if reserve else (),
        )
        for i, (main, club, fences, reserve) in enumerate(people)
    ]

    first = assign(block_list, officials, [])
    again = assign(block_list, officials, [])

    assert first == again
    by_key = {b.key: b for b in block_list}
    by_id = {o.id: o for o in officials}
    for seat in first.seats:
        if seat.official is None:
            continue
        others = [
            by_key[s.block]
            for s in first.seats
            if s.official == seat.official and s.block != seat.block
        ]
        assert hard_ok(by_id[seat.official], by_key[seat.block], seat.role, others) is None
    for key in first.without_main:
        seated = [s.official for s in first.seats if s.block == key and s.official is not None]
        assert seated and not any(by_id[i].main for i in seated)
