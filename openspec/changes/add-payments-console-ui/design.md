## Context

The payments backend is complete and largely unreachable. `frontend/src/PaymentsPanel.tsx` (115 lines) calls `GET /payments/unmatched` — which returns both `unmatched` and `flagged` transactions — and then discards everything that is not `flagged`. Nothing else in the frontend touches payments beyond the fencer-facing views.

What the backend already offers and nobody calls:

| Surface | Shape | Frontend caller |
| --- | --- | --- |
| `GET /payments/unmatched` | `TransactionOut[]`, `unmatched` + `flagged` | `PaymentsPanel` (flagged only) |
| `TransactionOut.candidate_vs` | `list[int]`, from `matching.detect_candidates` | none |
| `POST /payments/link` | `LinkIn{transaction_id, vs: list[int]}` | **none** |
| `GET /rules?phase=payments` | `RuleOut[]`, `payment_link` kind, `payload.auto_created` | none |
| `DELETE /rules/{id}` | unapplies `payment_link` via `matching.unapply_payment_link` | `Console.removeRule` (edits log only) |
| `PaymentEvent.kind == "expired_holding_payment"` | rows in `payment_events` | **no endpoint at all** |
| `Registration.outstanding_cents` / `outstanding_eur_cents` | properties | `RegistrationOut` only (fencer's own view) |

Two structural facts shape the design. First, `payment_link` rules replay through `_apply_opaque` in `rules.py`, which yields no `AppliedChange`, so they never appear in the rail's per-phase edits log — the one place the console otherwise shows rules. A link, once made, is invisible. Second, `sheet.base_rows` builds rows straight from `Registration`, so the outstanding balance is two lines away from being a table column; the credited counters are already on the model.

Constraints: `CLAUDE.md` / `openspec/squire-design-spec.md` ("Bureau 1952") are binding — no gradients, shadows, radii above 2px, emoji, spinners, or hex values outside `tokens.css`. The frontend has no test runner; `npm run lint` is `tsc -b --noEmit`.

## Goals / Non-Goals

**Goals:**
- Every kind of unresolved payment money has a place in the console that shows it and an action that resolves it.
- The manual-link endpoint gets its first caller, using the candidate VS the backend already computes.
- Money stranded on expired reservations becomes visible for the first time.
- Payment links become inspectable and removable.
- Outstanding balance reads off the fencer table, not only the fencer's own page.

**Non-Goals:**
- No change to matching, crediting, tolerance, expiry, reinstatement, or refund behaviour. This change surfaces decisions the backend already makes.
- No refund workflow beyond the existing mark-for-refund action.
- No new columns or views for phases other than Payments.
- No frontend test infrastructure. Verification is typecheck, build, backend tests, and driving the console.

## Decisions

### Decision 1 — Four separate rail cards, not one panel with sections

Each concern gets its own component: `FlaggedPanel`, `UnmatchedPanel`, `ExpiredHoldingPanel`, `PaymentLinksPanel`, stacked in the payments-phase rail in that order (most-actionable first). Each owns its own fetch, loading state and error state, matching how `MatchPanel`, `DedupPanel` and `ImportPanel` already work.

*Alternative considered*: one `PaymentsPanel` with four labelled sections — fewer files, one refresh cycle. Rejected: a single fetch failure would blank all four concerns, and the component would carry four unrelated action sets. Separate cards keep each surface independently testable and independently degradable (spec: "one card fails to load").

*Consequence*: `FlaggedPanel` and `UnmatchedPanel` both call `GET /payments/unmatched` and filter to their own status, so the phase opens with two identical requests. Accepted over adding a `status` query param or lifting the fetch into `Console`: the endpoint is small and per-tournament, and either alternative recouples the two cards. If the duplication becomes a problem, the fix is a `status` filter on the endpoint, not shared state in the console.

### Decision 2 — `PaymentsPanel.tsx` is renamed `FlaggedPanel.tsx`

Its name currently claims the whole domain while implementing one queue, which is exactly the confusion that sent the original Group 10 task list to the wrong files. `git mv` preserves history; the i18n keys are already namespaced `payments.flagged.*` and do not move.

### Decision 3 — Manual link is a modal, following the `MatchDialog.tsx` pattern

`LinkDialog.tsx` uses the existing `.modal-backdrop` / `.modal` markup: backdrop click closes, inner click stops propagation, `autoFocus` on the entry field. It receives the `Transaction` and renders the payer, amount, date and message as context, then `candidate_vs` as selectable entries plus a field for a hand-typed VS.

Selection is a `number[]`, not a single value — the multi-registration split is what `LinkIn.vs` exists for, and an inline row control cannot express it legibly. Confirm posts once with the full array.

*Alternative considered*: expanding the row inline. Rejected: no room for the message text an organizer needs to identify a payer, and multi-select in a table row is unreadable.

**Error handling** is specified by the endpoint: `404` with `detail = {"unknown_vs": [...]}` when a VS resolves to nothing, `409 already_matched` when the transaction was matched by a concurrent poll. `ApiError` in `api.ts` already carries `status` and `detail`, so the dialog reads `detail.unknown_vs`, names the offending values, and stays open with the entry preserved. A `409` closes the dialog and refreshes the queue — the work was done elsewhere.

### Decision 4 — New endpoint `GET /api/tournaments/{slug}/payments/expired-holding`

`PaymentEvent.kind == "expired_holding_payment"` is written by `scheduler.py` and read by nothing. The endpoint joins those events to their registration and returns fencer name, VS, credited amount (local and EUR), and the expiry time.

It is filtered to registrations **still** in `EXPIRED` state with credit remaining — a reservation later reinstated or refunded drops off the list on its own. This makes the card a work queue that empties, not an append-only log; the log already exists as the payment-event audit trail.

*Alternative considered*: deriving the list from registration state alone (`EXPIRED` with `amount_paid_cents > 0`) and skipping the event table. Rejected: the event is what distinguishes "expired holding a payment" from "expired, then paid late and flagged", and the backend already draws that distinction deliberately.

### Decision 5 — Outstanding balance is a sheet field, not a panel

`sheet.base_rows` gains `outstanding_amount` and `outstanding_eur_amount`, computed from the existing `Registration.outstanding_cents` / `outstanding_eur_cents` properties via the same cents→amount conversion `registrations.py` uses. `SheetRow` gains both; `PHASE_COLUMNS.payments` gains `outstanding` after `total_amount`.

This puts the balance on the same replay path as every other row value: it recomputes on rerun, sorts with the table, and follows rows into exports. A separate rail list would be a second place to read registration state, drifting from the first.

Rendering goes through the existing `formatMoneyWithEur(local, eur, tournament)` in `money.ts`, which already owns the "does this tournament show EUR" decision — `Console` holds `detail` (a `TournamentDetail`) so the currency context is in hand. `CellDisplay` gains a money case for `outstanding` and `total_amount`; today `total_amount` falls through to `String(value)` with no unit, which the same case fixes.

*Note on the two counters*: local and EUR credit are never summed (a registration settles when either currency's credit covers that currency's total, per the payments design). The column therefore shows the local balance with the EUR balance in parentheses where applicable — exactly what `formatMoneyWithEur` does — rather than inventing a single combined figure.

### Decision 6 — The payment-links card reads the rules API directly

`GET /rules?phase=payments`, filtered client-side to `kind === "payment_link"`. Each row shows the target (`txn:{external_id}`), the linked VS from `payload.vs`, and marks `payload.auto_created === true` as auto-created. Removal calls the existing `DELETE /rules/{id}`, which already unapplies the link server-side.

*Alternative considered*: making `payment_link` emit `AppliedChange` rows so links appear in the existing edits log. Rejected as out of scope — it changes `rules.replay` semantics for a kind that deliberately touches no sheet row, and the edits log has no removal affordance for opaque rules.

## Risks / Trade-offs

- **Duplicate fetch of `/payments/unmatched` from two cards** → Accepted (Decision 1). The endpoint is per-tournament and unpaginated; the escape hatch is a `status` query param, which does not change any component's shape.
- **A link posted against a transaction a concurrent Fio poll just matched** → The endpoint already returns `409 already_matched`; the dialog treats it as "someone else resolved this", closes, and refreshes rather than reporting an error the organizer cannot act on.
- **`unapply_payment_link` on a registration since marked paid by another route** → Existing backend behaviour, unchanged here; the card surfaces the result by refetching after removal rather than assuming the outcome.
- **Outstanding on the sheet touches every consumer of `base_rows`** → The added keys are additive and `SheetRow` has an index signature, so exports and other phases ignore them; backend tests cover the sheet shape.
- **Four cards plus a modal is a lot of new copy** → All strings land in `i18n/{en,cs}.json` under `payments.*` in the same pass; Czech is not deferred, since the console's primary users are Czech organizers.
- **No frontend tests** → Verification is `npm run lint`, `npm run build`, and driving the console against a tournament with seeded unmatched, flagged, expired-holding and linked cases. Backend additions (endpoint, sheet fields) get pytest coverage.

## Migration Plan

Additive throughout: one new read endpoint, two new sheet fields, four frontend components (one renamed). No schema change, no migration, no data backfill. Rolling back is deleting the components and reverting the two backend additions; nothing persists that the old console cannot read.
