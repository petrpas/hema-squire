"""The Data sheet's overlay, pure (spec floor-data; design floor-data-sheet D1, D2)."""

from datetime import date

from hypothesis import given
from hypothesis import strategies as st

from app.floor.datasheet import AddedTeam, Edits, apply
from app.floor.roster import FloorDiscipline, IndividualEntry, Person, Roster, TeamEntry

DISCIPLINES = (
    FloorDiscipline(id=1, slug="LS", name="Longsword", kind="individual"),
    FloorDiscipline(id=2, slug="SB", name="Sabre", kind="individual"),
    FloorDiscipline(id=3, slug="TM", name="Teams", kind="team", team_min=1, team_max=3),
)
KEYS = [f"reg:{n}" for n in range(1, 7)]
ratings = st.one_of(st.none(), st.floats(min_value=0, max_value=3000, allow_nan=False))
ranks = st.one_of(st.none(), st.integers(min_value=1, max_value=5000))
hr_ids = st.one_of(st.none(), st.integers(min_value=1, max_value=20))


@st.composite
def rosters(draw) -> Roster:
    persons = tuple(
        Person(key=k, name=f"P{k}", club=None, nationality=None, hr_id=draw(hr_ids)) for k in KEYS
    )
    entries = draw(st.sets(st.tuples(st.sampled_from(KEYS), st.sampled_from(["LS", "SB"]))))
    members = draw(st.lists(st.sampled_from(KEYS), min_size=1, max_size=3, unique=True))
    return Roster(
        date=date(2026, 11, 17),
        timezone="Europe/Prague",
        disciplines=DISCIPLINES,
        persons=persons,
        individuals=tuple(
            IndividualEntry(
                person=p, discipline=d, rating=draw(ratings), rank=draw(ranks), paid=True
            )
            for p, d in sorted(entries)
        ),
        teams=(
            TeamEntry(
                key="team:1",
                discipline="TM",
                name="Draci",
                members=tuple(members),
                paid=True,
                ratings=tuple((draw(ratings), draw(ranks)) for _ in members),
            ),
        ),
    )


fetches = st.dictionaries(
    st.tuples(st.sampled_from([1, 2, 3]), st.integers(min_value=1, max_value=20)),
    st.tuples(ratings, ranks),
)


@given(rosters())
def test_no_edits_is_the_identity(base):
    assert apply(base, Edits()) == base


@given(rosters(), fetches, ratings)
def test_a_hand_edit_wins_over_a_fetch(base, fetched, typed):
    entry = base.individuals[0] if base.individuals else None
    if entry is None:
        return
    discipline = next(d.id for d in DISCIPLINES if d.slug == entry.discipline)
    subject = f"{entry.person}@{discipline}"
    out = apply(base, Edits(cells={(subject, "rating"): typed}, fetched=fetched))
    found = next(
        e for e in out.individuals if e.person == entry.person and e.discipline == entry.discipline
    )
    assert found.rating == typed


@given(rosters(), fetches)
def test_a_fetch_only_replaces_where_it_holds_a_figure(base, fetched):
    persons = {p.key: p for p in base.persons}
    out = apply(base, Edits(fetched=fetched))
    for before, after in zip(base.individuals, out.individuals, strict=True):
        discipline = next(d.id for d in DISCIPLINES if d.slug == before.discipline)
        hr = persons[before.person].hr_id
        figure = fetched.get((discipline, hr)) if hr is not None else None
        assert (after.rating, after.rank) == (figure or (before.rating, before.rank))


@given(rosters())
def test_keys_survive_and_additions_join(base):
    local = Person(key="local:1", name="Jana", club=None, nationality=None, hr_id=None)
    edits = Edits(
        cells={("reg:1", "club"): "Klub Y"},
        added=(("local:1", 2),),
        teams=(AddedTeam(key="floorteam:1", discipline_id=3, name="Brno B", members=("local:1",)),),
        locals=(local,),
    )
    out = apply(base, edits)
    assert {p.key for p in out.persons} == {p.key for p in base.persons} | {"local:1"}
    assert next(p for p in out.persons if p.key == "reg:1").club == "Klub Y"
    added = [e for e in out.individuals if e.person == "local:1"]
    assert [(e.discipline, e.paid) for e in added] == [("SB", False)]
    team = next(t for t in out.teams if t.key == "floorteam:1")
    assert (team.members, team.paid, team.ratings) == (("local:1",), False, ((None, None),))
