## Context

Four lifecycle passes act on registrations: `process_reminders`,
`process_expiries`, `settle_seating` and `pending_demotions` — the last being the
count the console states before the organizer confirms an irreversible
settlement, which must select exactly what settlement will then move.

Two conditions today say "leave this registration alone", and they reach
differently:

| condition | reminders | expiry | demotion at settlement |
|---|---|---|---|
| `feature_payments` off | yes, via a branch in `run_tournament_tick` | yes, same branch | **no** |
| `Registration.clocks_dormant` | yes, in the pass's own `where` | yes, same | yes |

The gap in the third column is the bug. `settle_seating` selects `state ==
RESERVED` on the premise that it means "still owes money". A payments-off
tournament never reaches `PAID` — money is not requested and reconciliation is
refused — so every registration is permanently `RESERVED` and the premise selects
everyone. Reproduced: two registrations, one tick past the deadline, both
demoted.

The two conditions also live in different *kinds* of place. `clocks_dormant` is a
column consulted inside each pass's query; payments-off is a Python branch
wrapping two of the four passes. Nothing makes the set of passes agree.

A third condition is coming — the automatic/manual registration cut, where the
organizer keeps the list and Squire runs nothing against it. It must have one
place to land rather than a fourth arrangement of its own.

## Goals / Non-Goals

**Goals:**

- One decision point that answers "does Squire run its lifecycle clocks against
  this registration?", consulted by every pass and by nothing else.
- The answer carries its cause, so "why did this one not expire?" is readable.
- A payments-off tournament stops demoting registrations that owe nothing.
- `pending_demotions` and `settle_seating` select alike by construction.
- A third cause costs one line in one function.

**Non-Goals:**

- The automatic/manual axis itself. This change prepares the landing site; it
  does not add the condition.
- Any change to a payments-on tournament. Its reminders, expiries, settlement
  and mail must be bit-for-bit what they are today.
- Reworking how `clocks_dormant` is set, or who sets it. `issue-imported-
  registrations` owns that and stays as it is.
- The public participant list's treatment of a payments-off tournament, which is
  a separate defect on the same ground (`registration`'s "Public participant
  list" reads confirmed as `state == PAID`, so a payments-off list is empty or
  entirely unconfirmed, while the lifecycle requirement says such a registration
  is "presented as confirmed"). Named here so it is not rediscovered as part of
  this change.

## Decisions

### Decision 1: A pure function over `(tournament, registration)`, not a hybrid property

`dormancy_cause(tournament, registration) -> str | None` — `None` meaning the
clocks run, otherwise the reason they do not.

Alternative considered: a `hybrid_property` on `Registration` with a SQL
expression, so the passes keep filtering in the database. Rejected: the condition
depends on the tournament, so the expression needs a correlated subquery against
`tournaments` for a value every caller already holds in a local variable — all
four passes take `tournament` as a parameter. It would buy nothing and would make
the predicate hard to read and hard to test in isolation.

Two of the four passes already filter in Python after a broad select
(`process_reminders` builds `due` in a comprehension; `pending_demotions` and
`settle_seating` count and act over the loaded rows). The remaining one,
`process_expiries`, filters on `expires_at` in SQL, which is a different
condition and stays there. So the function fits the shape the module already has.

The function lives beside the lifecycle rather than on the model, because it is a
statement about what the scheduler does, not about what a registration is.

### Decision 2: The cause is derived where it can be, stored only where it cannot

`clocks_dormant` stays a stored column. It records an origin — this registration
was issued for an imported row — and origin is not recomputable from the
registration's current contents in a way that would survive the row being cleared.
No new column, and no migration.

Payments-off is read from the tournament at the moment of asking. It is a live
setting: turning payments on must make the clocks run again from that instant,
which a stored copy would get wrong.

The returned cause is a small closed set of strings, one per condition, so that
adding the third means adding one member and one branch.

### Decision 3: Dormancy suppresses the demotion, not the settlement

This is the decision that makes the fix safe.

`settle_seating` does two things at once: it moves registrations below the line,
and it stamps `seating_settled_at`, which closes seating so that later
registrations join the queue instead of taking seats. Only the first is about
money.

So dormancy filters the demotion set; the stamp is unconditional. A payments-off
tournament still settles on its deadline and still sends later registrations to
the queue — seats are finite whether or not anyone paid for them — it simply
finds nobody to move.

There is precedent in the spec rather than novelty: immediate mode already
"demotes nobody but closes seating", because every unpaid reservation expired
first. Payments-off reaches the same place by a different road.

Alternative considered: skipping settlement entirely on a dormant tournament.
Rejected — it would let a fencer take a seat after the seating deadline on a
tournament whose room is already full, and it would leave `seating_settled_at`
unstamped so that turning payments on later would demote everyone at once.

### Decision 4: The `feature_payments` branch in `run_tournament_tick` goes away

Today expiry and reminders are skipped wholesale for a payments-off tournament.
With the predicate in place that branch is redundant — every registration on such
a tournament is dormant, so both passes select nothing — and redundant is the
problem this change exists to remove. Two places that must agree is exactly what
produced the gap.

The cost is two queries per payments-off tournament per tick that return no rows.
That is the right trade against a second decision point.

The Fio polling branch above it keeps its `feature_payments` check. That is a
statement about the tournament — do not call the bank — not about a registration,
and it has no per-registration counterpart.

### Decision 5: `pending_demotions` and `settle_seating` share one selection

Today they are two queries carrying the same `where` and a comment on each asking
future editors to keep them aligned. The count the console shows and the set
settlement moves become one function returning the registrations to demote;
`pending_demotions` counts what it returns and `settle_seating` acts on it.

## Risks / Trade-offs

**[A payments-on tournament changes behaviour] → The load-bearing test is not
that the predicate returns the right value.** It is a payments-on tournament run
through the full lifecycle — reminders, an expiry, a demotion, a settlement —
asserting the same events, the same mail and the same placements as today. If the
existing suite passes untouched in `test_scheduler.py`, `test_registrations.py`,
`test_payment_e2e.py` and the seating tests, that is the evidence.

**[Existing payments-off tournaments have already been demoted] → Not repaired
by this change, and it must say so.** A tournament whose seating settled while
payments were off is carrying registrations marked substitute for a reason that
was never valid. Un-demoting them is a data repair with its own judgment calls —
which placements were substitutes legitimately? — and it is not something a
scheduler fix should do silently. The change stops the bleeding; the owner
decides whether any live tournament needs the repair.

**[The stamp is now reached on tournaments that never reached it before] →
Intended, and narrow.** A payments-off tournament past its deadline stamps
`seating_settled_at` where before it stamped it *and* demoted everyone. Strictly
fewer effects than today.

**[Removing the branch runs two queries that always return nothing] →
Accepted.** The scheduler ticks on an interval over the tournaments still ahead;
two empty indexed selects are not the cost worth optimising against a correctness
guarantee.

## Migration Plan

No schema change and no data migration. The behaviour change takes effect on the
next scheduler tick after deploy.

Rollback is the revert: nothing is written that a previous version would
misread.

Before deploying, the owner should be told which live tournaments have payments
off and a seating deadline in the past, since those are the ones whose
registrations may already have been demoted — the pilot included, if it qualifies.

## Open Questions

- Should the recorded cause be surfaced anywhere the organizer can see it — the
  queue view, or a registration's row in the console — or is it for the log and
  the maintainer only? Deferred: nothing today asks for it, and the automatic/
  manual cut is a better moment to decide, since that is when a fencer might
  reasonably ask why their registration is not moving.
