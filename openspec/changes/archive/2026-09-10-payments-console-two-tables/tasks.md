## 1. The ingest gate on debits

- [x] 1.1 Drop non-positive amounts in `bank.ingest`, with the reason stated
      there once (design D5); add `dropped` to `IngestResult` and make
      `duplicate` `len(transactions) - new - dropped`.
- [x] 1.2 Remove the drop from `statements.py:155`, leaving the LLM prompt's
      instruction to report debits rather than hide them exactly as it is —
      that contract is now honoured downstream instead of locally.
- [x] 1.3 Refuse a non-positive amount in `matching._evaluate_transaction`
      before any credit is written, so the guarantee does not rest on the gate
      alone (design D5).
- [x] 1.4 Check every reader of `IngestResult.duplicate` — `IngestAndMatchOut`,
      the import and poll reports, `payments.intake.imported` / `polled` in
      `i18n/cs.json` — and decide per site whether a dropped debit is worth
      naming; the spec requires only that it is not called a duplicate.
- [x] 1.5 Tests: a Fio JSON poll and a Fio CSV upload each carrying one debit
      ingest only the credits; a debit carrying a live registration's VS
      credits and deducts nothing; the interpreted path is unchanged; the
      counts report the debit as neither new nor duplicate.

## 2. The two endpoints

- [x] 2.1 Add `GET /payments/uncredited`: transactions with no live credit, by
      `NOT EXISTS` against `payment_credits` rather than by status, each row
      carrying its `disposition` — `proposal`, `refused`, `paired_uncredited`,
      `none` (design D1, D2).
- [x] 2.2 Carry into `refused` what the flagged queue already computes: the
      reason, and the hand-settled cause where one settled the registration
      (`settled_by_hand_reason`, `settled_by_recorded_payment`).
- [x] 2.3 Build `paired_uncredited` from the active `payment_link` rules whose
      transaction holds no live credit, naming the registrations the rule
      names — the case that reads as done today.
- [x] 2.4 Widen `GET /payments/credited` to every source holding a live credit,
      grouped by `(source_kind, source_id)`, each row carrying its per-fencer
      credits with their amounts and each credit's `origin`.
- [x] 2.5 Delete `GET /payments/likely`, `/unmatched`, `/links` and `/manual`.
      Keep `/expired-holding`, `/transactions/{id}/reversal` and `/reverse`
      untouched.
- [x] 2.6 Rewrite the backend assertions that reach the deleted paths —
      sixteen test files plus `contract_seed.py` (design, Risks). Assert on
      what the two tables express, not on which queue a row was in.
- [x] 2.7 Tests for the new behaviour: a pairing that credited nothing appears
      as uncredited and leaves once a credit exists; a `partial` transaction is
      credited, not uncredited; a hand-recorded payment appears in the credited
      table with `recorded` as its origin; a payment crediting three
      registrations names all three with their own amounts.

## 3. The tab bands and the note

- [x] 3.1 Replace `payments/QueueTabs.tsx` with a component drawing two
      `stage-control` bands — fencers/payments, then credited/uncredited — and
      taking its counts and its note as props (design D3, D4).
- [x] 3.2 Move the two loads into `Console.tsx`, independent of each other, and
      pass rows and counts down; delete `QueueCard.tsx` and the
      register/unregister context.
- [x] 3.3 Reroute `useSheetVisible` (`SheetArea.tsx`) onto the new tab state so
      the fencer table still gives way to whichever payments table is open.
- [x] 3.4 Compute the note in the console — proposals-of-uncredited, credited
      total, nothing for the fencer tab — absent rather than zero, worded so a
      subset reads as a subset.
- [x] 3.5 Style the note: `--ink-faded`, `--label-size`, baseline-aligned with
      the bands, lowercase, no badge and no colour; `queue-tabs` gains the
      row it needs instead of `align-self: flex-start`.
- [x] 3.6 Make the payments sheet heading read "Správa plateb", conditional by
      phase as `console.titleImport` already is (`SheetArea.tsx:122`).

## 4. The two tables

- [x] 4.1 `payments/UncreditedTable.tsx`: payer, amount, date, message, and the
      disposition column as the table's primary sort.
- [x] 4.2 `payments/DispositionCell.tsx`: what is to be done, and the actions
      that follow from it — confirm proposal, reject proposal, assign by hand,
      reinstate, mark for refund — reusing `LinkDialog` unchanged.
- [x] 4.3 `payments/CreditedTable.tsx`: date, source, payer or recorder, amount,
      the fencers with their own amounts in one cell, and why; the reversal
      action with its existing preflight, and relink.
- [x] 4.4 Delete `LikelyPanel`, `UnmatchedPanel`, `FlaggedPanel`,
      `ExpiredHoldingPanel`, `PaymentLinksPanel`, `CreditedPanel` and
      `RecordedPaymentsPanel`, with their tests.
- [x] 4.5 Rework `i18n/cs.json`'s `payments` subtree: two table titles, the
      disposition wordings including the six refusal reasons and the
      pairing-credited-nothing case, the note strings with their plural forms,
      and the removal of the seven old queue titles.
- [x] 4.6 Frontend tests: the bands render and switch; a table that fails to
      load says so while the other renders; the note follows the open table and
      is absent at zero; the disposition column carries the right action per
      case.

## 5. Specs and checks

- [x] 5.1 Answer the design's two open questions with the owner — the fencer
      tab's line, and whether the credited table shows the payment's message —
      and fold the answers into the delta spec before syncing.
- [x] 5.2 `cd frontend && npm run typecheck && npm run check && npm test && npm run build`.
- [x] 5.3 `cd backend && uv run ruff check . && uv run basedpyright && uv run pytest`.
- [x] 5.4 `uv run vulture` after the seven panels and five endpoints are gone —
      this is exactly the "after deleting a feature" case it exists for.
- [x] 5.5 Sync the delta specs into `openspec/specs/` and archive the change.
