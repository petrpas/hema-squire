"""Resolving a payment to a fencer by the words the payer wrote.

The half of name-assisted matching that knows what a tournament is:
`nameranking` scores a query against a list of names and knows nothing else,
this asks who is on the roster, decides what to query with, and applies the
rules that separate a proposal from a guess (spec name-assisted-matching).

**Nothing here moves money.** A resolution sets the transaction's status to
`likely` and names the fencer proposed; the registration is untouched — same
total, same credited amount, same state — and no mail is sent. Crediting happens
only when a person confirms, and it happens through the manual-link path, which
is to say by variable symbol. That is what makes "a proposal holds no money"
enforceable rather than aspirational: every consumer of registration state reads
the registration and therefore cannot see a proposal at all.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BankTransaction, Fencer, Registration, RegistrationState, Tournament
from app.nameranking import MIN_MARGIN, MIN_SCORE, Ranked, clear_winner, rank

LIKELY = "likely"
# Why a payment the resolver could not propose was left for a person. Each is a
# different question for the organizer, so they are told apart rather than all
# reported as "no variable symbol".
NO_ROSTER = "no_roster"  # nobody registered to rank against
NO_NAME_MATCH = "no_name_match"  # ranked, and nobody scored well enough
AMBIGUOUS = "name_ambiguous"  # two scored alike; the choice is a person's
PAYER_ONLY = "payer_name_only"  # the text named nobody but the payer


@dataclass(frozen=True)
class Resolution:
    """What the resolver concluded. `proposed` is None where the answer belongs
    to a person, and `ranked` is the whole roster in order either way — the
    dialog lists all of it, and the reason a proposal was withheld is legible
    from the top two scores."""

    proposed: Fencer | None
    # keyed by fencer id, which is what `roster` ranks by
    ranked: list[Ranked[int]]
    reason: str | None


def roster(session: Session, tournament: Tournament) -> list[tuple[int, str]]:
    """Every fencer with a live registration on this tournament, as (id, name).

    Live because a proposal has to have something to credit: a cancelled or
    expired registration is not a place to put money, and offering one would
    turn a confirmation into a second decision the organizer did not expect.
    """
    rows = session.execute(
        select(Fencer.id, Fencer.display_name)
        .join(Registration, Registration.fencer_id == Fencer.id)
        .where(
            Registration.tournament_id == tournament.id,
            Registration.state == RegistrationState.RESERVED,
        )
        .distinct()
    ).all()
    return [(row[0], row[1]) for row in rows]


def query_for(transaction: BankTransaction) -> tuple[str, bool]:
    """What to rank the roster against, and whether the answer may be proposed
    without a person looking at it.

    Three steps down, and the last one is where eligibility stops.

    The named person read out of the statement is the query where there is one.
    Failing that, the payment's own message text — which carries no payer name,
    `searchable_text` deliberately excluding it — and which is exactly what
    resolved 35 of the pilot's 43 with no model reading anything. Both are
    eligible to be proposed.

    The payer name is the last resort and is **never** a clear winner (design
    Decision 2). It is who paid, not who the payment is for, and one person
    routinely pays for another: on the pilot's statement one club organizer pays
    for three fencers, and proposing him would credit the wrong person three
    times. It is offered as a ranking so the dialog has something to show, and
    never as an answer.
    """
    named = (transaction.named_person or "").strip()
    if named:
        return named, True
    message = (transaction.searchable_text or "").strip()
    if message:
        return message, True
    return (transaction.payer_name or "").strip(), False


def resolve(session: Session, tournament: Tournament, transaction: BankTransaction) -> Resolution:
    """Rank the roster for one payment and decide whether to propose.

    Withheld on any of four grounds, and each is a state the organizer resolves
    rather than an error: nobody to rank, no clear winner, a winner the
    organizer has already refused for this payment, or a query that could only
    be built from text carrying the payer's own name.
    """
    candidates = roster(session, tournament)
    if not candidates:
        return Resolution(None, [], NO_ROSTER)

    query, may_propose = query_for(transaction)
    ranked = rank(query, candidates)

    if not may_propose:
        return Resolution(None, ranked, PAYER_ONLY)

    winner = clear_winner(ranked)
    if winner is None:
        # told apart because they ask the organizer different questions: nobody
        # scored well enough is a payment naming somebody who is not here, and
        # two scoring alike is a payment naming a surname two fencers share
        best = ranked[0].score if ranked else 0.0
        tied = len(ranked) > 1 and best - ranked[1].score < MIN_MARGIN
        reason = AMBIGUOUS if best >= MIN_SCORE and tied else NO_NAME_MATCH
        return Resolution(None, ranked, reason)

    refused = set(transaction.rejected_fencer_ids or [])
    if winner.key in refused:
        # the organizer has already said no to this pairing; offering it again
        # would be the system arguing with them
        return Resolution(None, ranked, AMBIGUOUS)

    fencer = session.get(Fencer, winner.key)
    return Resolution(fencer, ranked, None)


def propose(transaction: BankTransaction, resolution: Resolution) -> bool:
    """Record a proposal on the transaction, or leave it unmatched.

    Writes to the transaction and to nothing else. Returns whether a proposal
    was made, so the caller can count it separately from the payments it left
    for a person.
    """
    if resolution.proposed is None:
        transaction.status = "unmatched"
        transaction.status_reason = resolution.reason or "no_vs"
        transaction.proposed_fencer_id = None
        return False
    transaction.status = LIKELY
    transaction.status_reason = None
    transaction.proposed_fencer_id = resolution.proposed.id
    return True
