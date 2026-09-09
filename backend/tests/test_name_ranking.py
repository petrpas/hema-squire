"""Ranking the roster against the words a payer wrote (spec
name-assisted-matching, design Decisions 1–3).

The cases are the pilot's own: a statement of 43 payments against a roster of
54, in which not one payment carried a variable symbol. They are here as a table
because the design was decided by running against them, and a change that breaks
one of them has changed the design.

The two that must NOT be clear winners matter more than the rest. A payment
naming a surname two fencers share, and the roster's duplicate pair, both score
at the top and must both be handed to a person."""

import pytest

from app.nameranking import MIN_MARGIN, MIN_SCORE, clear_winner, normalise, rank, score

# the pilot roster, in the shape the resolver ranks: (fencer id, display name)
ROSTER = [
    (1, "Jan Sax Bělina"),
    (2, "Daniel Bělina"),
    (3, "Josef Vejda"),
    (4, "Pierre Chereau"),
    (5, "Jindřich Pekárek"),
    (6, "Ondřej Pekárek"),
    (7, "Milan Diviš"),
    (8, "Josef Vochozka"),
    (9, "Mikuláš Horák"),
    (10, "Matěj Mazanec"),
    (11, "Patrik Pavlovič"),
    (12, "Tomáš Jakubec"),
    (13, "Marek Zubalik"),
    (14, "Florian Imhof"),
    (15, "Florian Imhof"),
]


def best(query):
    return rank(query, ROSTER)[0]


# --------------------------------------------------------------- normalising


@pytest.mark.parametrize(
    ("text", "tokens"),
    [
        ("Matěj Mazanec", ["matej", "mazanec"]),
        ("MAZANEC MATEJ", ["mazanec", "matej"]),
        ("Kołodziej", ["kolodziej"]),
        (
            "NaDuel26: CHEREAU - Sabre and Sidesword",
            ["naduel26", "chereau", "sabre", "and", "sidesword"],
        ),
        ("", []),
    ],
)
def test_normalisation(text, tokens):
    assert normalise(text) == tokens


def test_name_order_does_not_matter():
    assert score("MAZANEC MATEJ", "Matěj Mazanec") == pytest.approx(
        score("Matěj Mazanec", "Matěj Mazanec")
    )


# ------------------------------------------------- what the pilot resolved


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("NaDuel26: Jan Sax Bělina - šavle a meč a štítek", "Jan Sax Bělina"),
        ("Vejda Josef", "Josef Vejda"),
        ("NaDuel26: CHEREAU - Sabre and Sidesword", "Pierre Chereau"),
        ("NaDuel26: Patrik Pavlovič (Klub Goliath) - sabre open", "Patrik Pavlovič"),
        # the missing space: one long token that matches no name token on its own
        ("JosefVochozka", "Josef Vochozka"),
        ("MikulášHorák", "Mikuláš Horák"),
    ],
)
def test_the_message_names_the_right_fencer(message, expected):
    assert best(message).name == expected


def test_a_payer_who_pays_for_others_is_not_the_answer():
    """The failure the whole design turns on. Milan Diviš pays for three people
    in this statement; scoring the payer name alongside the message put *him*
    first on all three. Scoring the message alone puts the fencer first."""
    for message, expected in [
        ("NaDuel26: Jindřich Pekárek- SB", "Jindřich Pekárek"),
        ("NaDuel26: Josef Vochozka - sabre", "Josef Vochozka"),
        ("NaDuel26: Matěj Mazanec - longsword", "Matěj Mazanec"),
    ]:
        assert best(message).name == expected
        assert best(message).name != "Milan Diviš"


# ------------------------------------- the two that must not be clear winners


def test_a_shared_surname_is_never_proposed():
    """A payment naming only a shared surname belongs to a person, and both
    tests say so: the two Pekáreks score alike, so the margin is nil, and
    neither reaches the score minimum because the given name matches nothing.

    The design predicted this would be caught by the margin, having measured a
    scorer that gave both 1.00. This one averages over the fencer's own tokens,
    so a half-named fencer scores around 0.7 — the same answer by the other
    test. The margin still earns its place; `test_a_partly_shared_full_name`
    below is where it is the only thing standing between the organizer and the
    wrong Pekárek."""
    ranked = rank("NaDuel26: Pekárek - SB", ROSTER)
    pekareks = [r for r in ranked if "Pekárek" in r.name]
    assert len(pekareks) == 2
    assert pekareks[0].score == pytest.approx(pekareks[1].score)
    assert clear_winner(ranked) is None


def test_a_partly_shared_full_name_is_proposed_on_the_margin():
    """The margin doing the work it was designed for: a full name that agrees
    with another in half its tokens. Both score above the minimum; only the
    margin separates them, and it separates them correctly."""
    ranked = rank("NaDuel26: Jindřich Pekárek- SB", ROSTER)
    assert ranked[0].name == "Jindřich Pekárek"
    assert ranked[1].name == "Ondřej Pekárek"
    assert ranked[0].score >= MIN_SCORE
    assert ranked[0].score - ranked[1].score >= MIN_MARGIN
    winner = clear_winner(ranked)
    assert winner is not None and winner.name == "Jindřich Pekárek"


def test_the_duplicate_pair_is_never_proposed():
    ranked = rank("Florian Imhof", ROSTER)
    assert ranked[0].score == pytest.approx(ranked[1].score)
    assert clear_winner(ranked) is None


def test_a_placeholder_proposes_nobody():
    """A fencer left the form's own placeholder in the message."""
    assert clear_winner(rank("jmeno", ROSTER)) is None


def test_a_clear_case_is_proposed():
    winner = clear_winner(rank("NaDuel26: Josef Vejda - sabre", ROSTER))
    assert winner is not None and winner.name == "Josef Vejda"


# ------------------------------------------------------------ the invariants


def test_every_candidate_comes_back_ranked():
    ranked = rank("anything at all", ROSTER)
    assert len(ranked) == len(ROSTER)
    assert [r.score for r in ranked] == sorted((r.score for r in ranked), reverse=True)


def test_a_query_matching_nobody_still_returns_the_roster():
    ranked = rank("zzzz qqqq", ROSTER)
    assert len(ranked) == len(ROSTER)
    assert clear_winner(ranked) is None


@pytest.mark.parametrize(
    "query",
    ["", "   ", "?/DO2026-04-09/SP", "123456", "—", "ěščřžýáíé", "a" * 500],
)
def test_ranking_never_raises_and_never_loses_a_candidate(query):
    ranked = rank(query, ROSTER)
    assert len(ranked) == len(ROSTER)
    assert all(0.0 <= r.score <= 1.0 for r in ranked)


def test_an_empty_roster_proposes_nobody():
    assert rank("Josef Vejda", []) == []
    assert clear_winner([]) is None


# ------------------- the noise the scorer had to be taught to ignore


def test_noise_in_the_query_does_not_decide_between_candidates():
    """Two shapes of noise nearly proposed the wrong Pekárek, and both are
    guarded now.

    A name token with no partner still scored ~0.43 against `naduel26`, so the
    candidate whose given name looked more like a tournament prefix won. And a
    bare surname scored against the joined name by length alone — 0.70 against
    `ondrejpekarek`, 0.64 against `jindrichpekarek` — proposing whichever
    Pekárek had the shorter given name."""
    ranked = rank("NaDuel26: Pekárek - SB", ROSTER)
    pekareks = [r.score for r in ranked if "Pekárek" in r.name]
    assert pekareks[0] == pekareks[1], "noise must not separate them"


def test_the_joined_form_serves_a_missing_space_and_not_a_fragment():
    # the whole name with its space gone: recovered
    assert score("JosefVochozka", "Josef Vochozka") == pytest.approx(1.0)
    # a surname alone against the joined name: not a match on length
    assert score("Vochozka", "Josef Vochozka") < MIN_SCORE
