No schema change, no migration, no backfill: this is a rule about when a write
may happen, not about anything written. The one draft in the pilot deployment
holds nothing.

## 1. Backend: the gate

- [x] 1.1 `require_published(tournament)` in `app/auth.py`, beside `require_console_access` rather than inside it — that one is called by reads and writes alike and the reads stay (design Decision 1). 409 with a stated reason, in the manner of the router's other refusals
- [x] 1.2 Call it from `routers/import_api.py`: the roster upload, the parse, `/match`, `/dedup`, `/dedup/decide`, `/issue`, and the clear. Issuing is the one that started this, so it gets a test of its own rather than only a sweep
- [x] 1.3 Call it from `routers/payments.py`: statement import, the bank poll, `process`, links, the likely-queue confirm and reject, resettle, the clear, reinstate, mark-for-refund, and the recorded payments both ways
- [x] 1.4 Call it from `routers/rules_api.py` (all three) and `routers/manual_api.py` (both), the manual row being the least visible way a participant could reach a draft
- [x] 1.5 Call it from `settle-seating` and the settled mark in `routers/registrations.py`. Leave the fencer-facing routes alone: they already refuse a draft with the not-yet-published reason, which is a better answer than this one
- [x] 1.6 Call it from `routers/export_api.py` — both the worksheet and the canonical document (design Decision 2)
- [x] 1.7 Sweep for what the list above missed: every endpoint calling `require_console_access` that writes anything. A rule that covers most writers is a guard, not a guarantee

## 2. Backend: the clocks

- [x] 2.1 `scheduler.tournaments_to_tick` excludes unpublished tournaments, alongside the held and the organizer-kept, with the reason in the docstring beside the two already there
- [x] 2.2 `setup.dormancy_cause` gains the unpublished cause, read live from the tournament. Order it first: it is the broadest and the cheapest to decide
- [x] 2.3 Tests: no pass selects a draft; the count and the settlement both read a draft's registrations as dormant; publication starts the clocks with no registration rewritten

## 3. Backend: tests

- [x] 3.1 A refusal test per gated route, asserting the reason and that nothing was written
- [x] 3.2 **The wide part.** Roughly two hundred tests do data work on tournaments they never publish. Add the publish to each file's shared setup helper — `test_import.py`, `test_dedup.py`, `test_payments_console.py`, `test_payments_clear.py`, `test_import_operations.py`, `test_imported_rows_union_migration.py`, `test_issuing.py`, `test_rules.py`, `test_matching.py`, `test_sheets_export.py` and their neighbours
- [x] 3.3 Read, do not force, the ones that resist. A test whose tournament is deliberately incomplete cannot publish, and what it should become is a question about this change rather than an obstacle to it
- [x] 3.4 A test that a draft holding data from before this rule keeps it and can still be read — the migration claim, asserted rather than assumed

## 4. Frontend: the console states its wait

- [x] 4.1 `Console.tsx` decides once from `published_at` whether the phases act, and passes that down. Not each panel asking for itself (design Decision 3)
- [x] 4.2 Each phase other than Setup renders one statement in place of its body — its table, its panels, its parameter rail and its controls. One statement per phase, not per panel
- [x] 4.3 Setup is untouched, and the phase strip is untouched: same phases, same order, same addresses. A draft's phase URL opens that phase and states its wait rather than redirecting
- [x] 4.4 The Fencers phase offers no hand-entry control on a draft, that being the one control whose absence the general statement should not have to imply
- [x] 4.5 Tests: a phase states its wait on a draft and shows its body once published; Setup is unaffected; the wait is stated once on the Payments phase rather than once per view; a phase URL on a draft lands on that phase

## 5. Localization

- [x] 5.1 English and Czech for the phase's statement and for the refusal. One statement string, written to be true of every phase, rather than one per phase saying the same thing differently
- [x] 5.2 `locale-parity.test.ts` covers the drift; parity does not prove a key a component asks for exists

## 6. Verification

- [x] 6.1 `pytest`, `ruff check .`
- [x] 6.2 `vitest`, `npm run lint`, `npm run build`
- [ ] 6.3 The console opened on a real draft. A screen that now says the same sentence in seven places is a layout claim and wants an eye
- [x] 6.4 Walk the hole this change exists to close: on a draft, import a roster and confirm nothing issues; publish; confirm the import then runs and the registrations take the symbols their mode calls for
