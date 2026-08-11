## 1. The flags and their migration

- [x] 1.1 Add `feature_schedule`, `feature_payments`, `feature_teams`, `feature_extras` to `Tournament` in `backend/app/models.py` as non-null booleans defaulting to false, with a comment stating that easy mode is the absence of all four and that they are never re-derived at runtime (design D1, D2, D9).
- [x] 1.2 Write the Alembic revision adding the four columns and backfilling them in the same revision by the D9 derivation — schedule from any discipline's `schedule_when`/`schedule_where`, payments from `bank_account` / `payment_mode != immediate` / any `BankTransaction` for the tournament, teams from any team-kind discipline, extras from any `ExtraItem`.
- [x] 1.3 Expose the four flags on `TournamentOut` in `backend/app/schemas.py`, and add the mode patch model that takes all four together (a mode is chosen as a whole, never one flag at a time).
- [x] 1.4 Add the mode endpoint to `backend/app/routers/tournaments.py` under the existing console-team authorization, writing only the four flags and never a setting they conceal (design D4).
- [x] 1.5 Tests: flags default false on creation; the migration's derivation on a configured tournament, on a bare draft, and on a tournament whose only payments evidence is an ingested transaction; the endpoint's authorization; that a mode write leaves every concealed setting byte-identical.

## 2. Payments off in the backend

- [x] 2.1 In `backend/app/setup.py`, condition the `MISSING_BANK_ACCOUNT` item on `feature_payments`, leaving every other item — EUR prices, roster bounds, legacy-fee conflicts — unaffected, and keep `guard_published_completeness` consistent with it.
- [x] 2.2 In the registration path (`backend/app/routers/registrations.py`, `pricing.py`), leave `payment_due_at` null and open no payment window when payments are off; the total is still computed and stored (design D6).
- [x] 2.3 In `backend/app/emails.py` / `spayd.py`, send the confirmation without account block or QR attachment for a payments-off tournament, and suppress reminder, expiry, surcharge and payment-received mail entirely.
- [x] 2.4 In `backend/app/scheduler.py`, skip `process_reminders` and `process_expiries` for payments-off tournaments in `run_tournament_tick`, leaving seating settlement and composition reminders running.
- [x] 2.5 In `backend/app/bank.py` / `matching.py` / `routers/payments.py`, refuse ingestion, matching and linking against a payments-off tournament with a reason naming the feature, rather than accepting them with no effect.
- [x] 2.6 In the queue promotion path, seat without opening a payment window or sending instructions when payments are off (`seating-queue` delta).
- [x] 2.7 Tests: a priced payments-off tournament publishes with no account; registration sets no due date; the scheduler expires nothing across a long tick; confirmation mail carries no account, VS or QR; ingestion and linking are refused; promotion opens no window; turning payments back on leaves account, mode, deposit, window, credited payments and transactions intact and expires nothing retroactively.

## 3. The mode dialog

- [x] 3.1 Build `frontend/src/TournamentModeDialog.tsx` on the existing `.modal-backdrop` / `.modal` pattern: the easy/advanced radio with easy preselected, the four checkboxes revealed under advanced, a `HelpHint` on each, and advanced-with-nothing-ticked resolving to easy mode.
- [x] 3.2 Add the in-use report the warning is built from, derived client-side from the tournament payload Setup already holds — team disciplines, extra items, disciplines carrying schedule fields, and the recorded payment settings (design D10) — and the confirmation step that states it. Turning a feature on is never warned.
- [x] 3.3 State in the payments warning that hiding payments stops Squire asking for money, and in the other three that hidden items are still sold and still shown to fencers.
- [x] 3.4 Add `getTournamentMode` / `setTournamentMode` to `frontend/src/api.ts` and the four flags to the `Tournament` type.
- [x] 3.5 Czech and English strings for the dialog, the four labels, the four hints, and every warning line.

## 4. Creation and the OTHER section

- [x] 4.1 In `TournamentPicker.tsx`, open the mode dialog after `createTournament` succeeds and before navigating; a rejected creation must never reach it, and dismissing it must still land the organizer in Setup on an easy-mode tournament (design D11).
- [x] 4.2 Build `frontend/src/setup/ModeSection.tsx` stating the mode in words — easy mode, or advanced naming the enabled features — with the control that reopens the dialog, carrying no save control, and place it on `OTHER`.
- [x] 4.3 Applying a mode from `OTHER` refreshes the tab bar and the sections around it without leaving Setup and without a save.

## 5. Setup follows the mode

- [x] 5.1 Derive the tab list in `SetupPanel.tsx` / `setup/shared.tsx` from the flags: `EXTRA` only with extras on, `OTHER` still owner-only, the other five always, order never changed.
- [x] 5.2 Title the payments tab `PRICING` while payments are off, keeping its identifier `payments` for the URL, the marker map and `aria-controls` (design D7).
- [x] 5.3 Show on the payments tab only the currency/exchange-rate section, the discount list and any legacy fixed fees while payments are off; hide the payment mode, deposit, window, reminder day, bank account and VS statement.
- [x] 5.4 Hide the seating deadline on `TIMELINE` while payments are off, and the composition deadline while the team feature is off; retain both stored dates.
- [x] 5.5 Hide the discipline `when`/`where` fields while schedule is off, leaving the extra-item time and place offered in every mode (design D8).
- [x] 5.6 Hide the kind control in `DisciplineDialog.tsx` and the roster bounds on the row while the team feature is off, so an added discipline is individual.
- [x] 5.7 Raise incompleteness markers only on tabs the mode offers; report an item whose editor is concealed on `PUBLISH` alone, naming the feature that restores it.
- [x] 5.8 Derive the console phase list in `Console.tsx` from the flags, and redirect a URL naming a phase the mode does not offer to the default phase.
- [x] 5.9 Czech and English strings for the `PRICING` title, the `PUBLISH` "turn on this feature" lines, and the mode section.

## 6. Verification

- [x] 6.1 `npm run lint` and `npm run build` clean in `frontend/`.
- [x] 6.2 Drive the console: create a tournament in easy mode and publish it priced with no bank account; turn each feature on and off in turn and confirm every stored value returns unchanged; confirm the warning counts are right; confirm `EXTRA`, `PRICING`/`PAYMENTS`, the Payments phase and the Teams phase appear and disappear with their features.
- [x] 6.3 Run the backend suite and confirm no existing test depended on the bank account being mandatory for a tournament that would now be payments-off.
- [x] 6.4 Check the new dialog and section against `CLAUDE.md` — no gradients, shadows, radii > 2px, emoji, spinners, or hexes outside `tokens.css`.
