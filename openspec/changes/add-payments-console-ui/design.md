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

Constraints: `CLAUDE.md` / `openspec/squire-design-spec.md` ("Bureau 1952") are binding — no gradients, shadows, radii above 2px, emoji, spinners, or hex values outside `tokens.css`. `CLAUDE.md` also fixes where the files go: a panel composed of several components lives under a directory named for it, as `setup/`, `dedup/` and `manual/` already do. The frontend runs `vitest` (`npm test`) over a dozen suites, several of them covering this console, and every panel built recently ships its tests beside it.

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
- No change to the rail's own furniture: `TolerancePanel` and `ManualEditsRail` keep their shape and placement.

## Decisions

### Decision 1 — The four queues are the phase's main area, not rail cards

The Payments phase's main column holds the four queues stacked above the fencer table — `UnmatchedPanel`, `FlaggedPanel`, `ExpiredHoldingPanel`, `PaymentLinksPanel`, then `SheetArea`. The rail keeps only what it holds for every other phase: the operation's parameters (`TolerancePanel`) and the manual-edits log.

This follows `DedupView`'s reading of the console: the work a phase exists to do belongs in the column the organizer is looking at, not in a 300px sidebar beside it.

**Where it diverges from Deduplication**: `DedupView` replaces the fencer table outright, because that phase concerns a handful of rows out of fifty and listing all fifty states the work where it is hardest to see. Payments is the opposite — every registration has a payment state, and this change adds an `outstanding` column to that very table (Decision 5). So the table stays and the queues sit above it. The queues are the exceptions, the table is the ledger, and the phase reads top to bottom in that order.

**Empty queues collapse to their heading.** A queue with nothing in it renders its title and a zero count, and no body. The absence is stated rather than omitted — that is the console's ledger idiom throughout — but a full "nothing here" card for each of four queues would push the fencer table down by four cards on the ordinary tournament where nothing is wrong. One line each is the whole cost when the phase is clean, and the table starts where it does today; the queues take room in proportion to the work they hold.

Each queue is its own component with its own fetch, loading state and error state, matching how `MatchPanel`, `DedupPanel` and `ImportPanel` already work.

*Alternative considered*: one `PaymentsPanel` with four labelled sections — fewer files, one refresh cycle. Rejected: a single fetch failure would blank all four concerns, and the component would carry four unrelated action sets. Separate views keep each surface independently testable and independently degradable (spec: "one view fails to load").

*Alternative considered*: leaving the four cards in the rail, as this change originally planned. Rejected once the rail was counted honestly — `TolerancePanel` plus four queues plus `ManualEditsRail` is six stacked cards in a 300px column, and the queue an organizer opens the phase to act on would sit below the fold.

*Alternative considered*: full parity with Deduplication, the queues replacing the table. Rejected: it would strand the outstanding column this change adds, and Payments is a phase that does something to every row.

*Consequence*: `FlaggedPanel` and `UnmatchedPanel` both call `GET /payments/unmatched` and filter to their own status, so the phase opens with two identical requests. Accepted over adding a `status` query param or lifting the fetch into `Console`: the endpoint is small and per-tournament, and either alternative recouples the two views. If the duplication becomes a problem, the fix is a `status` filter on the endpoint, not shared state in the console.

### Decision 2 — `PaymentsPanel.tsx` becomes `payments/FlaggedPanel.tsx`

Its name currently claims the whole domain while implementing one queue, which is exactly the confusion that sent the original Group 10 task list to the wrong files.

The five components also move into `frontend/src/payments/`, the directory convention `CLAUDE.md` states and `setup/`, `dedup/` and `manual/` already follow: four queues and a dialog are a panel composed of sections, not five loose files at the root of `src/`. `git mv` preserves history; the i18n keys are already namespaced `payments.flagged.*` and do not move.

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

Rendering goes through the existing `formatMoneyWithEur(local, eur, tournament)` in `money.ts`, which already owns the "does this tournament show EUR" decision. `CellDisplay` gains a money case for `outstanding` and `total_amount`; today `total_amount` falls through to `String(value)` with no unit, which the same case fixes.

The currency context reaches the cell as its own prop, alongside the `timezone` and `hrIdentity` props `CellDisplay` already takes — not as the whole `TournamentDetail`. Those two set the precedent: a cell is a function of what it draws, not of where the console is, so it receives the one fact it needs to draw money rather than the tournament record to go looking through.

*Note on the two counters*: local and EUR credit are never summed (a registration settles when either currency's credit covers that currency's total, per the payments design). The column therefore shows the local balance with the EUR balance in parentheses where applicable — exactly what `formatMoneyWithEur` does — rather than inventing a single combined figure.

### Decision 6 — The payment-links card reads the rules API directly

`GET /rules?phase=payments`, filtered client-side to `kind === "payment_link"`. Each row shows the target (`txn:{external_id}`), the linked VS from `payload.vs`, and marks `payload.auto_created === true` as auto-created. Removal calls the existing `DELETE /rules/{id}`, which already unapplies the link server-side.

*Alternative considered*: making `payment_link` emit `AppliedChange` rows so links appear in the existing edits log. Rejected as out of scope — it changes `rules.replay` semantics for a kind that deliberately touches no sheet row, and the edits log has no removal affordance for opaque rules.

## Risks / Trade-offs

- **Duplicate fetch of `/payments/unmatched` from two cards** → Accepted (Decision 1). The endpoint is per-tournament and unpaginated; the escape hatch is a `status` query param, which does not change any component's shape.
- **A link posted against a transaction a concurrent Fio poll just matched** → The endpoint already returns `409 already_matched`; the dialog treats it as "someone else resolved this", closes, and refreshes rather than reporting an error the organizer cannot act on.
- **`unapply_payment_link` on a registration since marked paid by another route** → Existing backend behaviour, unchanged here; the card surfaces the result by refetching after removal rather than assuming the outcome.
- **Outstanding on the sheet touches every consumer of `base_rows`** → The added keys are additive and `SheetRow` has an index signature, so exports and other phases ignore them; backend tests cover the sheet shape.
- **Four queues plus a modal is a lot of new copy** → All strings land in `i18n/{en,cs}.json` under `payments.*` in the same pass; Czech is not deferred, since the console's primary users are Czech organizers.
- **The queues push the fencer table down exactly when the phase is busiest** → Intended: on a tournament with money to resolve, the money is the work and the ledger is the reference. The collapse-to-heading empty state (Decision 1) keeps the cost at four lines on a clean tournament.
- **Verification** → `vitest` covers the new components — the dialog's two error branches, the empty collapse, and per-view failure isolation — alongside `npm run lint`, `npm run build`, `pytest` for the endpoint and sheet fields, and driving the console against seeded unmatched, flagged, expired-holding and linked cases.

## Migration Plan

Additive throughout: one new read endpoint, two new sheet fields, five frontend components under `payments/` (one of them the renamed `PaymentsPanel`), and the payments phase's main column rearranged around them. No schema change, no migration, no data backfill. Rolling back is deleting the directory, restoring the old rail placement, and reverting the two backend additions; nothing persists that the old console cannot read.
