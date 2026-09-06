## Context

`tournament-publication` gates two things on publication: a draft is absent from
every fencer-facing list, and it rejects in-app registration. It then guarantees
the opposite for the organizer — "its console and its detail record SHALL remain
reachable to its organizers" — and that guarantee has been read as *operable*
because nothing said otherwise.

So every write on the console works on a draft. The roster import, HR matching,
deduplication, issuing, manual entry, the manual-edit rules, the entire payments
surface, settling seating, the export. `require_console_access` is the only gate
any of them has, and it asks who you are, not what the tournament is.

`freeze-mode-at-publication` found the consequence while verifying its own
claims. A draft manual tournament may import a roster and issue registrations
with `vs = None` — correctly, since a manual tournament tells no payer a number
to quote (`issuing.py:257`) — then switch to automatic, which is legitimate
while it is a draft, and publish. The result is an automatic tournament whose
matching resolves through variable symbols, holding registrations that have
none. That change recorded the hole rather than patching it, because a second
guard on the switch would have left every other consequence of a populated draft
standing.

The scheduler is the same story from the other end. `tournaments_to_tick`
excludes tournaments already held and tournaments whose organizer keeps the
roster; drafts it selects. Today nothing comes of that, because a draft's
registrations can only be issued ones and those are dormant by origin — safety
by coincidence rather than by rule.

## Goals / Non-Goals

**Goals:**

- An unpublished tournament holds no participants and no money, by refusal at
  the endpoint rather than by nothing having tried.
- One decision, made once, rather than a condition remembered in each writer.
- The console says what it is waiting for, in the phase where the organizer is
  looking for the work.
- A draft's clocks do not run, guaranteed at the selection.
- Setup untouched: configuration is what a draft is for.

**Non-Goals:**

- Making publication reversible. It is one-way and stays so.
- Any way to work on data before publishing. The answer to "I want to import
  now" is to publish; publication is available as soon as mandatory setup is
  complete, and a published tournament whose registration window has not opened
  is an ordinary state, not a compromise.
- Blocking reads. The tables, the detail record, the manual-edits log and the
  operation records stay readable. There will be nothing in them, which is the
  point rather than a gap.
- Retroactive cleanup of drafts that already hold data. None does here, and one
  that did would keep what it has.

## Decisions

### Decision 1: A sibling of `require_console_access`, not a widening of it

`require_console_access` is called by twenty-eight endpoints across seven
routers, and reads and writes call it alike: the console's tables ask it, and so
does the statement import. Widening it to demand publication would refuse the
reads this change deliberately leaves alone.

So `require_published(tournament)` sits beside it in `app/auth.py` and is called
by the writers, one line each, in the manner of the router's other refusals: 409
with a stated reason, so a client can say what happened rather than reporting a
failure.

**Rejected: a FastAPI dependency that infers write from the HTTP method.** It
would be one line instead of twenty-eight, and it would be wrong twice —
`POST /price-preview` writes nothing, and the fencer-facing registration routes
are POSTs that already have their own, better refusal. A rule that has to be
overridden at both ends is not a rule.

**Rejected: refusing in `operations.start`**, which every LLM-backed step passes
through. It would cover parse, match, dedup and statement in one place and cover
none of the others — the links, the recorded payments, the settled mark, the
rules, the manual rows, issuing. A gate that catches four of twenty-eight reads
as a guarantee and is not one.

### Decision 2: The export is gated with the writes

It only reads, so on the letter of the rule it could stay. It goes anyway,
because it is the one read whose output leaves the console: a worksheet the
tournament hands to its referees, its check-in desk, its scorekeepers. A roster
of nobody, produced from a tournament nobody could enter, is a document that
will be believed by whoever receives it.

The console's own tables stay readable by exactly the same reasoning inverted —
they go no further than the organizer looking at them.

### Decision 3: The phases are drawn and inactive, not hidden

Both were defensible. Hiding everything but Setup would make the draft console
read as "finish setting up, then publish", which is true, and it is one less
thing on screen.

Drawn and inactive wins because a phase that vanishes teaches nothing about when
it returns, and this product has settled that argument twice already: the
Payments phase on a tournament Squire collects nothing for is boned out rather
than removed, and the mode on a published tournament is stated rather than
hidden — both on the reasoning that a surface should answer the question it
raises. "Where did Import go?" is that question.

The cost is a console saying the same sentence in seven places. It is paid by
saying it in the phase body, where the organizer is already looking, rather than
also on every tab, every panel and every button — one statement per phase, and
the tab strip unchanged.

`Console.tsx` decides it once from `published_at` and each phase renders its
statement instead of its body. Not each panel asking for itself: a phase where
five panels each explain the same wait is the shape this avoids.

### Decision 4: Unpublished is both an exclusion and a dormancy cause

Manual mode is already both — excluded at `tournaments_to_tick` so no pass ever
sees such a tournament, and a cause in `dormancy_cause` so the paths a person
reaches by hand answer the same way. The reasoning is written in `clocks_run`:
the exclusion covers the scheduler's own pass and does not cover the count the
console states or the settlement an organizer triggers.

Unpublished takes the same double form for the same reason, even though this
change also closes the human paths by refusing settle-seating. Belt and braces
here is not redundancy: it is what makes the property true of a registration
created by any path, including one that forgets to mark it dormant, which is the
guarantee `add-registrations-kept-by` D2 bought and this change should not spend.

### Decision 5: Refused, not ignored

Every gated endpoint answers 409 with a reason naming publication, not 404 and
not a silent no-op. The console will not send these requests once the phases
state their wait, so in practice the refusal is for everything else: a retried
request, a second tab open from before publication, a script. Each should learn
why rather than see a tournament that appears not to exist.

## Risks / Trade-offs

**[The test suite is the bulk of the work] → Accepted, and it is the honest
measure of how far the current behaviour reaches.** Roughly two hundred backend
tests do data work on tournaments they never publish. Nearly all of them want
one `publish()` in the file's shared setup helper. The ones that do not — a test
that cannot publish because its tournament is deliberately incomplete, say —
are the interesting ones, and each should be read rather than forced.

**[An organizer is made to publish earlier than they wanted] → Real, and
narrower than it sounds.** Publication makes a tournament visible and opens
in-app registration according to its own dates; it does not open registration
that the dates have not opened. An organizer who wants to prepare a roster in
January for a June tournament publishes in January and registration still opens
when they said. What they lose is the ability to keep the tournament invisible
while working on its data — which is exactly the state this change decides
should not exist.

**[Someone later wants a staging mode: visible to nobody, operable by the
organizer] → It would be a change, not a workaround.** It would need to answer
what happens to the data at the moment of publication, which is the question
this change removes rather than answers.

## Migration Plan

No schema change, no data migration, no deploy ordering. The rule takes effect
on the next deploy.

The pilot deployment holds one draft, `test-2026`, with no imported row, no
registration, no transaction and no rule, so nothing is stranded. A draft
elsewhere that held data would keep it, become unable to add to it, and become
able again on publication.

Rollback is the revert. Nothing is written that a previous version would
misread.

## Open Questions

- None. The two that shaped this — whether the phases hide or state themselves,
  and whether the export counts as data work — were decided by the owner before
  the artifacts were written, and are recorded as Decisions 3 and 2.
