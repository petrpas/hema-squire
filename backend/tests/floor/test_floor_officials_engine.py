"""Officials on blocks (spec floor-officials). No database."""

from hypothesis import given, settings
from hypothesis import strategies as st

from app.floor.engine.model import Activity
from app.floor.engine.officials import Block, Official, Pin, assign, blocks, hard_ok


def pool(id: str, piste: int, start: int, end: int, discipline: int = 1, day: int = 0) -> Activity:
    return Activity(
        id=id,
        discipline=discipline,
        kind="pool",
        ordinal=1,
        round=0,
        piste=piste,
        day=day,
        start=start,
        end=end,
    )


def official(
    id: int, *, roles=("referee",), club: str | None = None, blocked=(), days=(0,), disciplines=(1,)
):
    return Official(
        id=id,
        roles=frozenset(roles),
        disciplines=frozenset(disciplines),
        days=frozenset(days),
        club=club,
        blocked=tuple(blocked),
    )


def block(
    key: str, start: int, end: int, *, piste: int = 1, clubs=(), needs=(("referee", 1),)
) -> Block:
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
            pool("LS:pool:1", 2, 600, 645),
            pool("LS:pool:5", 2, 650, 695),
            pool("LS:pool:2", 3, 600, 645),
        ],
        overhead={1: 5},
        needs={1: (("referee", 1),)},
    )

    assert [b.activities for b in found] == [("LS:pool:1", "LS:pool:5"), ("LS:pool:2",)]


def test_an_official_who_fences_is_kept_off_during_their_pool():
    jan = official(1, blocked=[(0, 600, 645)])
    eva = official(2)

    result = assign([block("b", 610, 640)], [jan, eva], [])

    assert [s.official for s in result.seats] == [2]


def test_an_unfillable_role_is_stated():
    result = assign([block("b", 600, 700, needs=(("judge", 1),))], [official(1)], [])

    assert [(s.role, s.official) for s in result.unfilled] == [("judge", None)]


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
        [block("final", 900, 960)], [official(1), official(2)], [Pin("final", "referee", 0, 2)]
    )

    (seat,) = result.seats
    assert (seat.official, seat.pinned) == (2, True)


@settings(max_examples=20)
@given(
    spans=st.lists(
        st.tuples(st.integers(1, 4), st.integers(0, 600), st.integers(15, 120)),
        min_size=1,
        max_size=10,
    ),
    people=st.lists(
        st.tuples(
            st.sampled_from(["referee", "judge"]), st.sampled_from([None, "A", "B"]), st.booleans()
        ),
        min_size=1,
        max_size=6,
    ),
)
def test_no_hard_constraint_is_ever_broken_and_the_result_is_deterministic(spans, people):
    block_list = [
        block(
            f"b{i}",
            start,
            start + length,
            piste=piste,
            needs=(("referee", 1), ("judge", 1)),
            clubs=["A"],
        )
        for i, (piste, start, length) in enumerate(spans)
    ]
    officials = [
        official(i + 1, roles=(role,), club=club, blocked=[(0, 300, 360)] if fences else [])
        for i, (role, club, fences) in enumerate(people)
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
