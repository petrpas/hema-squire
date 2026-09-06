Depends on `add-manual-paid-marking`, whose mark this change rewrites, and on
`add-payments-console-ui`, whose four views this change makes five.

## 1. Model and migrations

- [x] 1.1 `ManualPayment` in `models.py`: tournament, registration, `amount_cents`, `currency`, `received_on`, `method`, `note`, `recorded_by`, `created_at`, `removed_at`. A sibling of `BankTransaction` and **not a row inside it** — the transaction list is the statement ledger, and a row no bank sent would falsify it for every reader of that table (design D2). Say so in the class docstring
- [x] 1.2 `settled_by_hand_at` and `settled_by_hand_reason` on `Registration`, both nullable. Stored rather than deduced: paid-with-empty-counters stopped being a sound deduction the moment a waived registration can also hold a recorded payment (design D4)
- [x] 1.3 Rewrite the comment on `amount_paid_cents`. It has read *money Squire saw in a statement* since it was written; it now means *money credited, by a statement or by a person who said so* (design D1). Grep for the old sentence — it is quoted elsewhere
- [x] 1.4 Two additive migrations, both back-filling to nothing. Existing hand-marks on payments-off tournaments have no timestamp to recover and keep working on their state alone

## 2. Backend: crediting

- [x] 2.1 Make `matching._settle`'s transaction parameter optional, so the settle test, the deposit threshold, the payment event, the overpayment's refund state and the mail are reached from both routes rather than copied into the second (design D3). Events with no transaction carry the `ManualPayment` id in their detail
- [x] 2.2 Record endpoint on the **payments** router, gated by `bank.require_payments_enabled` as its neighbours are (design D7): credit the named currency lane, then call `_settle`. Tolerance applies unchanged — it is what decides settled versus partial, and the two routes must not disagree at the same number
- [x] 2.3 The confirmation or partial-payment mail goes out, the same one a bank credit sends (design D3). The fencer's inbox should not know which route their money took
- [x] 2.4 Remove endpoint: soft-delete, subtract **the row's own `amount_cents`** and not a figure derived from today's balance — the mistake the payment-link rules were built to avoid (`matching.py:751`) — and return the registration to the state that amount had settled. A `PaymentEvent` for each of recording and removal, naming the organizer
- [x] 2.5 No edit endpoint. A correction is a removal and a new record, so that what was credited and what reversed it are both readable
- [x] 2.6 List endpoint for the console's view, excluding removed rows
- [x] 2.7 Tests: a full credit settles and mails; a partial credits and stays reserved; a deposit-mode credit reaching the deposit closes the window; removal subtracts exactly what it credited **after the total was amended upward** — assert the figure, since the wrong one passes a loose assertion; refusal where payments are off; the EUR lane credited alone and never summed with the local one

## 3. Backend: the mark

- [x] 3.1 Delete `_require_squire_collects_nothing` from `routers/registrations.py`. This is the reversal of `add-manual-paid-marking` D2 and the one breaking line in the change; the endpoint's docstring carries why (design D4, and the risk note: the writer it forbade was a *silent* one)
- [x] 3.2 Write `settled_by_hand_at` and `settled_by_hand_reason`; clear both on unmark
- [x] 3.3 Require the reason where `feature_payments` is on and accept its absence where it is off, with a stated refusal. Not an inconsistency — where a live ledger is read, a paid row holding nothing is a puzzle a reader will solve as a fault (design D4)
- [x] 3.4 Counters stay untouched, as today. Assert it in the test rather than trusting it
- [x] 3.5 Tests: the waiver on a collecting tournament; the reason refused as missing there and accepted as absent elsewhere; both counters zero; the mark and its reason stored and cleared; the audit events and their actor; the existing payments-off behaviour unchanged

## 4. Backend: what reads it

- [x] 4.1 `sheet.py`: carry `settled_by_hand` and its reason on the row, and make the outstanding cells read waived rather than a balance owed (spec etl-console)
- [x] 4.2 The flagged queue's payload states, for a `registration_*` conflict, whether the registration was settled by hand and by which act — the mark or the recorded payment, with its amount and date. The organizer is deciding whether the transaction is more money or the same money twice, and needs the earlier act in front of them (design D6)
- [x] 4.3 Confirm the collision paths **without building anything**: a transaction landing on a hand-settled registration reaches `matching.py:449` and flags uncredited; one landing on a part-hand-paid registration credits and overshoots into the overpayment flag. Two tests, no new code (design D6)
- [x] 4.4 The expired-holding list already reads the counters and so already includes hand-recorded money; add the test that says so, and one that a waived registration is absent because nothing was credited
- [x] 4.5 `export_json.py`: carry the recorded payments and the mark with its reason, raise the document version, restore without replaying a credit on top of the counters the document already carries. Round-trip tests for cash, for a waiver, for the doubling that must not happen, and for an older document
- [x] 4.6 Check the remaining readers of `amount_paid_cents` named in design D1 — `scheduler.py:168`, `_apply_deposit_threshold`, `outstanding_cents`, the console's credited amount — and confirm each is correct under the counter's widened meaning. Some need nothing; the point is that each was looked at

## 5. Frontend: recording a payment

- [x] 5.1 A record-payment action on the registration's own row in the Payments phase, not on a queue: the queues hold money looking for a registration, and this is the other way round
- [x] 5.2 The dialog, under `frontend/src/payments/`, in `LinkDialog`'s idiom: amount, currency where the tournament prices in two, date, method, note. It states what the registration is owed before anything is typed, so the organizer records against a balance rather than from memory. Its own file
- [x] 5.3 A refusal keeps the dialog open with what was typed preserved, as `LinkDialog` does
- [x] 5.4 `RecordedPaymentsPanel` as the fifth view, in `QueueCard`'s shape — empty state a single heading line. It lists fencer, amount, date, method, note, recorder, and removes; removal states what it will do first, because it may unsettle a row the roster shows as paid
- [x] 5.5 Add it to `QueueTabs`/`QueueTabStrip` and to whatever counts the views, so "four" does not survive anywhere as a number

## 6. Frontend: the mark in the full phase

- [x] 6.1 **No new column.** `PHASE_COLUMNS.payments` is unchanged and `settled` stays the boned-out phase's alone, where it is that phase's whole content (owner decision on review: the full phase's table is already seven columns, and the mark would be empty on almost every row)
- [x] 6.2 The waiver lives on the **state cell** — it changes exactly that cell, from reserved to paid with no money behind it. `StateCell` is its own file beside `SettledCell`, which stays the boned-out phase's cell and is untouched: each cell has one job rather than one cell branching on which tournament it is drawn for. Offered on a reserved row and, to unset, on a waived one; never on a registration the money settled
- [x] 6.3 The outstanding column reads waived on a marked row, from the sheet value rather than a second computation in the cell. **The word alone; the reason opens from it** in `HelpHint`'s box but with none of its marking — no glyph, no underline, no help cursor. An organizer's reason runs to a sentence, and a money column as wide as the longest one is not a money column any more (owner decision on review)
- [x] 6.4 `StateBadge` translates the state rather than printing the stored enum: the table was reading `reserved` in the middle of a Czech page. Czech `registration.state.reserved` is *Rezervace* (owner decision on review)
- [x] 3.6 **`RegistrationOut.vs` is `int | None`.** A tournament whose organizer keeps the roster mints no variable symbols (`issuing.py:257`), and the field was declared `int` — so marking such a registration committed the write and then failed to serialise the response with a 500. The change appeared on the next reload, which made it read as a refresh problem rather than an error. Older than this change; reached first by the mark, because it is the first endpoint to return `RegistrationOut` for a registration that may carry no symbol (found by the owner in the server log)
- [x] 6.6 A refused mark is stated in the dialog that asked for it, which stays open with the reason intact. `toggleSettled` swallowed every failure, so a refusal left a row that had not changed and nothing at all saying why — the shape of "nothing happens" (found on review)
- [x] 6.5 Tests: `stateCell.test.tsx` for the waiver's placement, its reason, what it refuses to touch and the translated state; `settledCell.test.tsx` trimmed back to the boned-out cell; the record action asserted to sit in the row-actions column and nowhere else; the waived reading; the dialog posts and refreshes through the console's existing reload signal; the failure path states itself

## 6b. One outstanding balance (Decision 5b)

- [x] 6b.1 `Registration.balance_cents(tournament)` on the model: one signed amount and its currency, the lane the money came in, zero on a settled registration unless past tolerance, zero on a waiver. `matching._tolerance_cents` delegates to the model's `tolerance_cents` so the percentage lives once
- [x] 6b.2 The wire carries `outstanding_amount` with `outstanding_currency` and no longer carries `outstanding_eur_amount` — `sheet.py`, `registration_out`, `RegistrationOut`, `SheetRow`, `RegistrationDetail`
- [x] 6b.3 The amend endpoint's `overpaid` and `underpaid` ask `balance_cents`, not an `or` across both lanes. The `or` was true for every registration, so amending a paid one always sent a surcharge demand
- [x] 6b.4 The link dialog's roster offers the balance rather than the raw counter, so a tolerance-settled fencer reads as owing nothing there too
- [x] 6b.5 The console cell and the fencer's registration page state one figure in `outstanding_currency`; the total keeps both prices, because a price is not a balance
- [x] 6b.6 Tests: the two-lane partial states one balance in the lane paid into; a tolerance-forgiven shortfall reads zero; a surcharge past tolerance survives the settle; the console cell renders one currency and follows the lane

## 7. Localization

- [x] 7.1 English strings: the record action and its dialog, the four methods, the panel and its empty state, the removal warning, the waiver reason prompt, the waived balance, the flagged queue's two new readings, every refusal
- [x] 7.2 Czech in the same pass — `volná účast` is the reason the owner named and belongs in the prompt's own example. `locale-parity.test.ts` covers the drift; parity does not prove a key a component asks for exists

## 9. The balance the tolerance hid

- [x] 9.1 **The tolerance decides the state, not the column.** `balance_cents` zeroed a settled registration whose credit fell within tolerance; on `na-duel-2026` that was nine rows reading "0 Kč" with 21 to 43 Kč missing behind each — foreign payers who sent the EUR price, whose bank converted it, and who landed short of the crown price. The organizer was told their books balanced when they did not, and the difference was recorded nowhere (owner decision, 2026-09-06)
- [x] 9.2 A waiver stays the one exception and reads zero whatever its counters hold; a trivial overpayment reads as the negative figure it is
- [x] 9.3 Tests: a settled-within-tolerance shortfall states itself and the row still reads paid; an overpayment reads negative. Neither behaviour had a test before
- [x] 9.4 The tournament's tolerance is left alone — 10% is a value of that tournament, not of the code, and at 750 Kč it accepts a payment 75 Kč short

## 8. Verification

- [x] 8.1 `pytest`, `ruff check .`
- [x] 8.2 `vitest`, `npm run lint`, `npm run build`
- [x] 8.3 The Payments phase on screen against a running instance: five views, two new columns, the dialog, and a waived row read beside a credited one. A phase that gained a panel and a column is a layout claim and wants an eye
- [x] 8.4 Walk the collision once by hand: record a cash payment, then import a statement carrying the same money, and confirm the flagged row says which act settled the registration
