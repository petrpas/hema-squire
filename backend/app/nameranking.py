"""Ranking a tournament's roster against the words a payer wrote.

A variable symbol is a shortcut: quoted, it finds a registration without anybody
reading the message. About one payment in ten carries none, or carries one that
is mistyped, or belongs to somebody other than the person the message names —
and on a tournament whose registrations the organizer keeps, no payment carries
one at all. Those are resolved from the payer's own text, and this is the half
of it that needs no model.

Deterministic on purpose (design Decision 1). Ranking 54 names against one name
is a solved problem; a model would be paid per transaction to do it, could not
be calibrated — there is no score to set a threshold on, only a self-reported
confidence — and could name a fencer who is not on the roster. It also has to
work on a deployment with no model configured at all, where the payment's raw
text becomes the query and this still resolved 35 of the pilot's 43.

No database access and no imports from the app: a query string and a list of
names in, the same names ranked out.
"""

import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher

# Thresholds a proposal must clear, both of them (design Decision 3). Tunable
# constants, not laws: they come from one 43-transaction statement from one bank
# in one language, which is enough to catch a design error and not enough to be
# a distribution.
#
# The margin is the safety-critical half. Both Pekáreks on the pilot roster
# score 1.00 against a payment naming a Pekárek, and the duplicate Florian Imhof
# rows score 1.00 against each other; a score threshold alone admits all of them
# and then picks by list order, which is to say arbitrarily. A margin above zero
# turns every one of those into "the organizer decides", which is the right
# answer.
MIN_SCORE = 0.85
MIN_MARGIN = 0.05


# Letters that carry no combining mark to strip: NFKD leaves them alone because
# they are their own letters, not a base plus an accent. A Polish surname on a
# Czech statement is written both ways by the same person, so they have to fold.
_STANDALONE = str.maketrans(
    {
        "ł": "l",
        "Ł": "l",
        "đ": "d",
        "Đ": "d",
        "ø": "o",
        "Ø": "o",
        "ß": "ss",
        "æ": "ae",
        "Æ": "ae",
        "œ": "oe",
        "Œ": "oe",
        "þ": "th",
        "Þ": "th",
        "ð": "d",
        "Ð": "d",
    }
)


def normalise(text: str) -> list[str]:
    """Fold a name to comparable tokens: diacritics stripped, lowercased, split
    on everything that is not a letter or a digit.

    `Günther`/`Guenther` do not survive this as equals — folding turns `ü` into
    `u`, not `ue` — but `Kołodziej`/`Kolodziej` and `MAZANEC MATEJ`/`Matěj
    Mazanec` do, and those are the shapes a Czech statement actually produces.
    """
    folded = unicodedata.normalize("NFKD", text.translate(_STANDALONE))
    stripped = "".join(c for c in folded if not unicodedata.combining(c))
    token, tokens = [], []
    for char in stripped.lower():
        if char.isalnum():
            token.append(char)
        elif token:
            tokens.append("".join(token))
            token = []
    if token:
        tokens.append("".join(token))
    return tokens


# A name token with no real partner in the query still scores something against
# noise — `ondrej` reaches 0.43 against `naduel26`. Left in, that noise decides
# between candidates: on a payment naming only `Pekárek` the two Pekáreks came
# out 0.714 and 0.636, a margin wide enough to propose one of them, chosen by
# which given name happened to look more like a tournament prefix. Anything
# below this floor is not a match and counts as none.
_TOKEN_FLOOR = 0.6

# How much of the joined name a single query token must cover before it is
# treated as the name with its spaces missing rather than as a fragment of it.
_JOINED_MIN_SHARE = 0.7


def _ratio(a: str, b: str) -> float:
    ratio = SequenceMatcher(None, a, b).ratio()
    return ratio if ratio >= _TOKEN_FLOOR else 0.0


def score(query: str, name: str) -> float:
    """How well the payer's words match one fencer's name, from 0 to 1.

    Insensitive to name order, because a statement writes `MAZANEC MATEJ` as
    readily as `Matěj Mazanec`. Each of the name's tokens is scored against its
    best partner among the query's, and the name's tokens are what is averaged
    over — so a query carrying a tournament prefix, a discipline list and a club
    is not penalised for the words that are not the name.

    Averaging over the *name's* tokens is what makes a surname alone
    (`Jakubec`, `CHEREAU`, `Zubalik`) fall short: the fencer's given name
    matches nothing in the query, so half the average is near zero and the score
    lands around 0.7. That is the design's intended outcome for those payments —
    they are among the eight the pilot left to a person — reached by the score
    test rather than the margin.

    The margin is what catches the other shape: two full names that agree in
    part. `Jindřich Pekárek` scores 1.00 against himself and about 0.65 against
    `Ondřej Pekárek`, so the margin is wide and the proposal is made; a bare
    `Pekárek` scores about 0.71 against both, and fails on score *and* margin
    together. Both tests earn their place on different evidence.
    """
    query_tokens = normalise(query)
    name_tokens = normalise(name)
    if not query_tokens or not name_tokens:
        return 0.0

    # A missing space (`JosefVochozka`, `MikulášHorák`) leaves the query as one
    # long token that matches neither name token well on its own. Comparing the
    # name's joined form against each query token recovers it.
    #
    # Only where the token could plausibly *be* the whole name. A bare surname
    # is also one token, and against a joined name it scores by length alone:
    # `pekarek` reached 0.70 against `ondrejpekarek` and 0.64 against
    # `jindrichpekarek`, which is a margin wide enough to propose one of the two
    # Pekáreks because his given name is shorter. This path is for spaces that
    # fell out, not for fragments.
    joined_name = "".join(name_tokens)
    best_joined = max(
        (
            _ratio(joined_name, token)
            for token in query_tokens
            if len(token) >= _JOINED_MIN_SHARE * len(joined_name)
        ),
        default=0.0,
    )

    per_token = [
        max(_ratio(name_token, query_token) for query_token in query_tokens)
        for name_token in name_tokens
    ]
    averaged = sum(per_token) / len(per_token)
    return max(averaged, best_joined)


@dataclass(frozen=True)
class Ranked[Key]:
    """One candidate and how well it matched. `key` is whatever the caller
    ranked by — a fencer id, usually — carried through untouched so this module
    needs to know nothing about what a fencer is. Generic in it, so the caller
    gets its own key type back rather than having to widen or re-narrow."""

    key: Key
    name: str
    score: float


def rank[Key](query: str, candidates: list[tuple[Key, str]]) -> list[Ranked[Key]]:
    """Every candidate, best first. Ties keep the order they were given in, so
    the ranking is a function of its inputs and nothing else.

    Always returns everything it was given, including for a query that matches
    nobody: the caller decides what to do with a bad best score, and a dialog
    listing the whole roster needs the whole roster ordered even when the top of
    it is meaningless (design Decision 6).
    """
    ranked = [Ranked(key=key, name=name, score=score(query, name)) for key, name in candidates]
    return sorted(ranked, key=lambda r: -r.score)


def clear_winner[Key](ranked: list[Ranked[Key]]) -> Ranked[Key] | None:
    """The one candidate strong enough and far enough ahead to be proposed, or
    None where the answer belongs to a person.

    Both tests, always. A high score with no margin is the tied-surname case,
    which is exactly what must not be waved through.
    """
    if not ranked:
        return None
    best = ranked[0]
    if best.score < MIN_SCORE:
        return None
    runner_up = ranked[1].score if len(ranked) > 1 else 0.0
    if best.score - runner_up < MIN_MARGIN:
        return None
    return best
