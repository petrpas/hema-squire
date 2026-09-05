## Context

The mode arrived as a value on the tournament and inherited the four feature
flags' rule that settings are changeable at any point, publication included. The
flags earn that rule — they hide controls and change nothing else. The mode does
not: it decides who owns the roster, and three separate pieces of work have since
had to reason about what happens when the answer moves.

`issue-imported-registrations` is being revised so a manual tournament allocates
no variable symbol; a switch to automatic afterwards leaves registrations with no
symbols on a tournament whose matching resolves through them.
`add-external-registration` made the external address mandatory for publishing a
manual tournament; a switch after publication makes a published tournament
incomplete, which is not a state publication is supposed to permit and which the
repository's own database reached this afternoon. And `tournament-mode`'s
confirmation counts in-app registrations, which a draft cannot hold, because the
registration gate requires publication.

Each has a local answer. The common answer is that the question should not arise.

## Goals / Non-Goals

**Goals:**

- The mode is settled by publication and cannot move afterwards.
- The attempt is refused where it is made, with a reason, not ignored.
- Nothing offers a control that would answer a refusal.
- Three problems stop needing separate handling.

**Non-Goals:**

- Freezing the payments setting. It stays changeable, and it should.
- Freezing anything else that publication does not already freeze.
- A migration path from manual to automatic. This removes the need for one on a
  published tournament; on a draft the switch is free and nothing has happened
  yet that a migration would have to carry.
- Any way back for an organizer who publishes wrongly, beyond what already
  exists for a wrong slug or a wrong variable-symbol series: cancel and recreate.

## Decisions

### Decision 1: Publication is the boundary, not the first registration

The obvious alternative is to freeze at the first registration, as the variable-
symbol series does. Rejected, and the reason is that the two are protecting
different things.

The series is protecting *issued identifiers*: before a registration exists,
nothing has been handed out, so changing it is free. The mode is protecting
*what a published tournament promised*. A published manual tournament has told
the world where to register; a published automatic one has opened its own form.
Both statements are made at publication, not at the first person who acts on
them, and both become false the moment the mode moves.

Publication is also the point the completeness rule attaches at, which is what
makes the second problem in Context disappear rather than merely become rarer.

### Decision 2: Refused at the endpoint, and not offered in the surface

Both, not either.

The endpoint refuses because it is the authority and because the console is not
the only caller. The surface stops offering because a control that exists to be
refused teaches an organizer that the product argues with them.

The refusal carries a stated reason, in the manner of the other refusals on this
router, so a client can say what happened rather than reporting a failure.

### Decision 3: The confirmation goes rather than being narrowed

`tournament-mode` requires that changing the mode be confirmed in both
directions, stating what stops or starts and counting the in-app registrations
Squire would stop managing.

With the mode changeable only on a draft, that count is always zero — the
registration gate requires publication, so a draft has no in-app registrations
by construction. A confirmation whose whole content is a number that cannot be
anything but zero is a click that teaches nothing.

What remains worth saying — that a manual tournament takes no registrations here
and that Squire writes to nobody — is already said by the surface, beside each
answer, at the moment the organizer chooses. It belongs there and not in a
dialog after the fact.

A draft *can* hold registrations issued from an import. Those are dormant by
origin, carry no due date, and are unaffected by the mode: nothing about them
changes when it moves. So there is nothing for a warning to count there either.

### Decision 4: No data migration and no backfill

Every existing tournament has a mode and every value is already valid. The
change is a rule about when the value may be written, not about the value.

A tournament published today with a mode its organizer would now change is in
exactly the position this creates deliberately. There is no repair to run,
because there is nothing wrong with the data — only with what could have been
done to it next.

## Risks / Trade-offs

**[An organizer publishes in the wrong mode and is stuck] → Accepted, and it is
the point.** The mitigations are that the choice is made on the creation surface
with each answer's consequence stated beside it, that publication is a deliberate
act behind its own tab and its own completeness check, and that a draft is freely
switchable for as long as it is a draft. The way back is cancel and recreate,
which is what a wrong slug or a wrong variable-symbol series already costs.

**[Somebody wants the switch later and this has to be undone] → It would be a
change, not a workaround.** Reintroducing it means answering the three questions
in Context on their own terms: what to do with symbol-less registrations, how a
published tournament may become incomplete, and what the confirmation counts.
Those answers are the price of the feature and were never paid; this change is
the decision not to pay them.

**[The console still shows a mode tier on a published tournament] → It states
rather than offers**, so the organizer can still read what their tournament is.
Hiding it would answer the question "which mode is this?" with silence, which is
worse than answering "manual, and settled".

## Migration Plan

No schema change, no data migration, no deploy ordering. The rule takes effect
on the next deploy and applies to every tournament as it stands.

Rollback is the revert: nothing is written that a previous version would
misread, and a tournament frozen under this rule is indistinguishable from one
that simply was not changed.

## Open Questions

- None. The one this change exists to close — what happens to a tournament whose
  mode moves after publication — is closed by making it impossible.
