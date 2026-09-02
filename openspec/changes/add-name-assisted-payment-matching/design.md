## Context

`matching.py` resolves a payment through its variable symbol and nothing else.
`effective_vs` reads a labelled VS; `detected_vs_tokens` finds bare numbers in the
payer text; `_resolve_global` turns those into registrations. Where none of that
finds anything, `matching.py:344` finishes the transaction as
`_finish(transaction, "unmatched", "no_vs")` and the organizer takes over.

For the pilot that branch takes every payment. The bank export has no
variable-symbol column at all, and the payments predate any VS Squire could have
issued — 43 transactions, none matchable. What the payments do carry is names, in
prose the fencers wrote themselves.

Two experiments against those 43 real transactions and the real 54-fencer roster
decided this design, and they are worth stating because the second contradicts
the first:

1. Scoring the payer name and the message **together** with stdlib string
   similarity ranked the correct fencer first in 43/43 — and resolved
   `NaDuel26: Jindřich Pekárek- SB` to **Milan Diviš**, the man who paid for him.
   Milan Diviš pays for three people in this one statement, and both Pekáreks are
   on the roster.
2. Scoring **the message alone** resolved all three of Diviš's payments correctly
   with margins of 0.36–0.42, and produced a clear single winner (score ≥ 0.85 and
   margin ≥ 0.05) for 35/43. The 8 remaining are a surname alone, a missing space,
   a diminutive, a literal `jmeno`, and one tie between the roster's duplicate
   pair.

The design follows from experiment 2 and from one line of `payments`: matching is
"never by payer name or amount alone". That line is not an obstacle to work
around — experiment 1 is exactly the failure it was written to prevent.

## Goals / Non-Goals

**Goals:**

- A payment that names a fencer is resolved without the organizer typing a number.
- No money ever moves on a name. The organizer's confirmation is the credit.
- The ambiguous cases are recognised as ambiguous rather than guessed at.
- Everything but the reading of prose is deterministic, testable and tunable.
- Works on a deployment with no model configured, less well.

**Non-Goals:**

- Changing how a VS-carrying payment is matched or credited.
- Tolerance, refunds, partial-payment or currency behaviour, which apply to a
  confirmed proposal unchanged.
- Learning from confirmations. A rejected pairing is not re-proposed, and that is
  the whole of the memory.
- Resolving a payment to a fencer who has no registration — see the dependency.

## Decisions

### Decision 1 — The model extracts; the roster is matched by rule

The alternative was to hand the model the roster and ask it to pick, which was one
of the shapes considered explicitly.

Rejected. Ranking 54 names against one name is a solved problem that experiment 2
answers with stdlib string similarity, and a model would be paid per transaction
to do it. Worse, it cannot be tested without a fake, cannot be calibrated — there
is no score to set a threshold on, only a self-reported confidence — and can name a
fencer who is not on the roster.

The model does the half a rule cannot: turning
`?/DO2026-04-09/SPNaDuel26: Patrik Pavlovič (Klub Goliath) - sabre open and sword
with buckler + weapons rental` into a person. That is one narrow question about
one row, and the model is already reading every row of the statement to interpret
it, so the question rides along at no extra call.

The split also degrades well: with no model configured, the payment's raw text
becomes the query. Experiment 2 ran exactly that way and still resolved 35/43.

### Decision 2 — Extraction reads the message, not the payer

This is the safety property of the whole change, and it is counter-intuitive: the
payer name is *better* text than the message — cleaner, no discipline lists, no
tournament prefixes — and using it makes the raw numbers look better. Experiment 1
scored 43/43 on the merged fields.

It is still wrong. The payer is who paid, and one person routinely pays for
another; the message is who the payment is for. Merging them means the strongest
possible evidence points at the wrong person precisely when the payer is also a
fencer, which is the common case for a club paying for its members.

So the payer name is a fallback consulted only where the message names nobody —
`jmeno` in this statement, where a fencer left the form's placeholder in — and a
resolution reached that way is not eligible to be a clear winner.

### Decision 3 — Two thresholds, and the margin is the one that matters

A proposal requires a minimum score **and** a minimum margin over the runner-up.

The margin is the safety-critical half, and the roster proves why. Both Pekáreks
score 1.00 against a payment naming a Pekárek; the duplicate Florian Imhof rows
score 1.00 against each other. A score threshold alone admits all of these, and
picks between tied candidates by list order — which is to say, arbitrarily.

Setting the margin above zero converts every one of those into "the organizer
decides", which is the correct answer. Starting values of 0.85 and 0.05 come from
the 43-transaction run; they are constants to tune against later statements, not
laws.

### Decision 4 — `likely` is a transaction status, not a registration state

The proposal lives entirely on `BankTransaction` — its status becomes `likely` and
it references the fencer proposed. The registration it points at is untouched:
same total, same credited amount, same state.

That is what makes "a proposal holds no money" enforceable rather than aspirational.
Every consumer of registration state — the sheet's outstanding column, the paid
flag, reminders, the confirmation mail, export — reads the registration and
therefore cannot see a proposal at all. There is no path by which a proposal
leaks into the money.

The status column already carries `matched | unmatched | flagged | partial`
(`models.py:700`), so this is a new value in an established vocabulary, not a new
mechanism.

### Decision 5 — Confirmation reuses the manual link, it does not parallel it

Confirming a proposal is the organizer supplying the variable symbol the payer
omitted. So it goes through the existing manual-link path — the same `payment_link`
rule, the same crediting, the same tolerance, the same survival across reruns.

This keeps one crediting path in the codebase and means a confirmed proposal is
indistinguishable afterwards from a payment the organizer linked by hand, which is
what it is. Rejection is the only genuinely new verb, and it records that this
pairing was refused so the resolver does not offer it again.

### Decision 6 — Ranking is a whole-roster ordering, not a shortlist

The dialog gets every fencer ordered, with the strongest marked, plus a text
lookup. A shortlist with the rest alphabetical was the alternative considered.

Ranking the whole roster costs nothing once the scores exist, and it never ranks
worse than alphabetical. The lookup is what actually saves the hard cases — the
`jmeno` payment ranks nobody usefully, and no shortlist would have helped. The HR
search dialog is the pattern to follow, so this is a form the console already has.

### Decision 7 — Resolution runs at ingest, on the no-VS branch

The resolver is consulted at `matching.py:344`, where a transaction is about to be
finished as `unmatched` for want of a VS. Nothing before that branch changes, so a
VS-carrying payment never touches this code and the existing matching tests keep
their meaning.

## Risks / Trade-offs

**A proposal that credits is worse than no feature.** It moves money silently and
mails the wrong fencer a confirmation. → Decision 4 makes it structurally hard, and
the tests must assert the registration's credited amount, its outstanding amount,
its state and the collecting mailer — not the transaction's status string, which is
the thing that would be right in a broken implementation.

**Thresholds tuned on one statement from one bank in one language.** 43
transactions is enough to catch a design error and not enough to be a
distribution. → They are named constants, and the queue makes a bad threshold
visible as work rather than as silent error: too strict shows up as a full
unresolved queue, too loose as rejections. Neither loses money.

**The organizer confirms 35 proposals by clicking 35 times, and clicking becomes
reflexive.** A confirmation flow that is always right trains the person not to
read. → Each entry shows the bank's own text beside the fencer, so the evidence is
in front of the eye that clicks. Worth revisiting if a bulk-confirm is ever asked
for; it is deliberately not offered here.

**Extraction is cached per row, so a better prompt does not improve old
statements.** → Consistent with how every other interpretation in the import
behaves, and re-import after clearing the stored decisions is the existing escape
hatch.

**The roster can be large.** Ranking is linear in fencers per transaction; a
2000-fencer tournament against 500 transactions is a million comparisons. → Local
string work, once at ingest, not per request. If it ever matters, blocking on a
first letter or a length band is the standard remedy and needs no design change.

## Migration Plan

One Alembic migration: the `likely` status value needs none if the column is a
plain string, which it is (`models.py:700` — `String(20)` with a comment, not an
enum); the proposed-fencer reference and the rejected-pairing record do need one.

No backfill. Existing unmatched transactions stay unmatched; running the resolver
over them retrospectively is a deliberate action, not a migration, and is worth
offering only if the pilot asks for it.

Rollback: proposals are transactions in a status nothing else reads, so reverting
leaves them looking unmatched, which is what they are. No money is at risk in
either direction, which is the benefit of Decision 4.

## Open Questions

- Should confirming a proposal for a fencer whose registration is already fully
  paid be refused, or flagged as it would be for a VS-carrying payment? The
  existing flagged path probably answers this without new behaviour.
- Should the resolver run again over payments left unresolved before this change
  shipped, on the organizer's say-so? Cheap to offer, and the pilot is exactly the
  case that would want it.
- Should a rejected pairing be remembered per payment, or per fencer across
  payments? Per payment is the conservative reading and what the spec says; per
  fencer would silence a fencer whose name keeps mis-attracting payments.
