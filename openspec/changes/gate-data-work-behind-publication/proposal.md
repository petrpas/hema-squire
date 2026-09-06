## Why

A draft is a tournament being written. It is invisible to fencers and rejects
in-app registration with the not-yet-published reason — `tournament-publication`
already says so. But its console is the whole console: an organizer can import a
roster, match it against HEMA Ratings, resolve duplicates, issue registrations,
upload a bank statement and credit payments, all against a tournament that does
not yet exist to anybody but them.

That was never decided. It is what falls out of gating in-app registration and
nothing else, and `freeze-mode-at-publication` ran into the consequence while
verifying its own work: a draft may issue registrations carrying no variable
symbol, switch itself to automatic — legitimately, it is still a draft — and
publish carrying them onto a tournament whose matching resolves through symbols.
Guarding that switch a second time would have treated the symptom. The cause is
that an unpublished tournament holds participants at all.

Publication is where a tournament stops being a draft of itself and starts being
a thing other people act on. The data work belongs on that side of the line.

## What Changes

- **A draft holds no participants and no money.** Every operation that writes a
  tournament's data SHALL be refused while it is unpublished: the roster import
  and its parse, HR matching, deduplication and its verdicts, issuing, manual
  entry of a fencer, the manual-edit rules, the whole payments surface —
  statement import, the bank poll, matching, links, recorded payments, the
  settled mark — and settling seating. **BREAKING** for every one of those
  endpoints on a draft.
- **The export is refused too**, though it only reads. It is the one read that
  produces something outward: a worksheet a tournament sends to its referees.
  From a tournament nobody can enter, it would be a roster of nobody.
- **The console shows its phases and states why they are inactive**, rather than
  hiding them. An organizer preparing a tournament should be able to see the
  work that awaits it, and a tab that vanishes teaches nothing about when it
  comes back. The phases are drawn, each says that data work begins at
  publication, and none of them acts.
- **A draft's clocks do not run.** `tournaments_to_tick` excludes tournaments
  already held and tournaments whose organizer keeps the roster; it does not
  exclude drafts, so the lifecycle passes reach them today. Unpublished becomes
  a third exclusion there and a cause in the dormancy predicate, exactly as
  manual mode is both — a guarantee at the selection and a cause at the paths a
  person reaches.
- **Setup is untouched.** Configuration is what a draft is for: the place, the
  disciplines, the prices, the mode, the payments setting, the features, the
  logo, the team. All of it stays freely editable, including into
  incompleteness, as `tournament-publication` already provides.

Not in scope: making publication reversible, or any way to work on data before
it. An organizer who wants to import a roster publishes first; publication is
already available the moment mandatory setup is complete, and a published
tournament with no registration window open is a perfectly ordinary state.

Not in scope either: reading. The console's tables, the tournament detail, the
manual-edits log and the operation records stay readable on a draft — there is
simply nothing in them, because nothing could have been written.

## Capabilities

### Modified Capabilities
- `tournament-publication`: **A tournament is a draft until it is published**
  gains what a draft may not do. Today it fixes visibility and in-app
  registration and then guarantees the console stays reachable; it does not say
  that reachable means readable rather than operable. That is the rule's home,
  because publication is the boundary it names.
- `etl-console`: the phases are drawn on a draft and none of them acts, each
  stating that data work begins at publication. **Phase-tabbed fencer table**
  and the manual entry of a fencer are the requirements this reaches.
- `data-export`: the export is refused on a draft, stating why.
- `registration`: **One dormancy predicate governs the lifecycle passes** gains
  unpublished as a cause, and the pass selection gains it as an exclusion.
- `imported-registrations`: issuing waits for publication. It is reached from
  the head of every payment intake and from the Payments phase on arrival, both
  of which stop on a draft; saying so here is what keeps the symbol-less
  registrations closed rather than merely unreachable by the routes anybody
  currently takes.

## Impact

**Backend** (`backend/app/`): a `require_published` beside
`auth.require_console_access` — a sibling rather than a widening, because that
function is called by reads and writes alike and reads stay. Called from the
write endpoints of `routers/import_api.py`, `routers/payments.py`,
`routers/rules_api.py`, `routers/manual_api.py`, `routers/export_api.py`, and
from `settle-seating` and the settled mark. `scheduler.tournaments_to_tick`
gains the third exclusion; `setup.dormancy_cause` gains the third cause.

**Frontend** (`frontend/src/`): the console's phase strip renders every phase on
a draft and each phase's body states that it waits for publication, in place of
its panels and its table. `Console.tsx` decides it once from `published_at`
rather than each panel asking.

**No schema change and no migration.** The one draft in the pilot deployment
holds nothing — no imported row, no registration, no transaction, no rule — so
there is no tournament for the rule to be retroactively unkind to. A draft that
did hold data would keep it and simply stop being able to add to it, which is
the correct behaviour and needs no repair.

**The cost is the tests.** Roughly two hundred backend tests exercise data work
on tournaments they never publish — `test_import.py` publishes in none of its
twenty, `test_dedup.py` in none of its twelve, `test_payments_console.py` in
none of its fourteen. Each file's shared setup helper gains a publish. That is
mechanical, but it is wide, and a test that cannot simply publish is a
behaviour this change did not intend and wants reading.

**Verification**: `pytest` for the refusal on every gated route and for the
draft's clocks; `vitest` for a phase stating its wait; and the console opened on
a real draft, because a screen that now says the same thing seven times is a
layout claim.
