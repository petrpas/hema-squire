## Why

Squire's Setup phase presents every organizer with the settings of the largest tournament it can host: seven tabs, three payment modes, a deposit, a seating deadline, a bank account, team roster bounds, a composition deadline, per-discipline schedule fields, an extra-items table. A club running one longsword bracket on a Saturday afternoon must read past all of it to find the four fields that concern them, and the `PUBLISH` tab blocks them on a bank account they never intended to use.

Nothing about that complexity is wrong for the tournaments it was built for. It is wrong as the only door in. This change adds a **tournament mode** chosen at creation: an easy mode with none of the advanced machinery, and an advanced mode where the organizer names which of the four heavy features — schedule, payments, team disciplines, extra services — the tournament actually uses.

## What Changes

- **A second creation modal.** After the display-name/date/slug dialog creates the tournament, a Tournament Mode dialog offers easy mode or advanced mode with four independent feature checkboxes, each with a help hint saying who it is for. Dismissing it leaves the tournament in easy mode, which is what a new tournament is.
- **The same dialog reachable from Setup.** `OTHER` gains a section stating the current mode with a control that reopens the dialog, so a tournament can grow into its features rather than being frozen by a choice made in its first minute.
- **Four feature flags stored on the tournament**, not per organizer: every member of a console team sees the same tournament. Easy mode is the name for all four being off, not a fifth stored value.
- **Disabling a feature hides its settings without changing them.** Stored values are retained untouched; re-enabling the feature shows them exactly as they were. Turning off a feature the tournament already uses is **warned and confirmed**, naming what will be hidden — two team disciplines, three extra items — rather than refused or hidden silently.
- **Payments off suspends the payment machinery, not just its settings.** A payments-off tournament requires no bank account to publish, issues no variable symbol or QR code, sends no reminders, expires no reservation for non-payment, and offers no Payments phase in the console. Disciplines keep their prices in the tournament's currency and discounts still apply — the totals are shown to the fencer as information, and the money is settled outside Squire. **BREAKING** for the completeness rule: a priced tournament is publishable without a bank account when payments are off.
- **Schedule off** hides the per-discipline `when` and `where` fields. Extra services keep their own time and place regardless — that is how an after-party or a seminar is described, not a tournament schedule.
- **Teams off** removes the team kind from the discipline dialog, the roster bounds, the composition deadline and the console's Teams phase. **Extras off** removes the `EXTRA` tab.
- **The tab bar follows the mode.** `EXTRA` appears only with extras on. `PAYMENTS` is titled `PRICING` and holds only the currency and the discount list when payments are off, since a tab named for payments on a tournament that takes none is a lie. Incompleteness markers are only ever raised on tabs the mode still shows.
- **Existing tournaments are backfilled from what they already use** — schedule on if any discipline carries `when` or `where`, payments on if a bank account or a non-immediate payment mode is recorded, teams on if a team discipline exists, extras on if an extra item exists — so no organizer loses sight of something they configured, and an untouched draft lands in easy mode.
- Czech and English strings for the dialog, the `OTHER` section, the hints and the confirmations.

Not in scope: changing what any retained setting means, altering pricing or matching logic, or a fifth feature.

## Capabilities

### New Capabilities
- `tournament-modes`: the mode itself — the four feature flags and their storage on the tournament, the creation dialog and its twin in `OTHER`, easy mode as the absence of all four, what each flag conceals, the retain-don't-change rule, the warning when a feature in use is switched off, and the derivation applied to tournaments that predate the mode.

### Modified Capabilities
- `setup-navigation`: the tab set and the section allocation become functions of the mode rather than fixed at seven; `PAYMENTS` narrows to `PRICING` when payments are off; incompleteness markers attribute only to tabs the mode shows.
- `tournament-admin`: setup completeness stops requiring a bank account when payments are off; the payment and reservation parameters are offered only when payments are on; discipline `when`/`where` are offered only when schedule is on; in-app creation gains the mode dialog as its second step.
- `registration`: a payments-off registration is seated without money being requested — no reservation expiry, no QR or payment instructions in the confirmation email, the total shown as information.
- `fencer-home`: in-app payment instructions are not offered for a payments-off tournament.
- `payments`: reconciliation, ingestion, reminders and expiry notices apply only to tournaments with payments enabled.
- `seating-queue`: promotion from the substitute queue seats immediately when payments are off, rather than opening a payment window.
- `team-disciplines`: the team kind, the roster bounds and the organizer's Teams view are offered only when the team feature is on.
- `etl-console`: the Payments and Teams phases are offered according to the mode.

## Impact

**Backend** (`backend/app/`): `models.py` (four boolean columns on `Tournament`); an Alembic migration adding them and backfilling by derivation; `schemas.py` (`TournamentOut`, a mode patch model, `TournamentCreate` defaults); `routers/tournaments.py` (the mode endpoint, the in-use report the warning is built from); `setup.py` (completeness drops the bank account when payments are off); `pricing.py` / `registrations.py` (nothing owed at registration when payments are off); `emails.py` and `spayd.py` (no QR, no payment block); `scheduler.py` (reminders and expiry skip payments-off tournaments); `bank.py` / `matching.py` (ingestion scoped to payments-on tournaments); `routers/payments.py` (refuse for payments-off tournaments).

**Frontend** (`frontend/src/`): new `TournamentModeDialog.tsx`, shared by the picker and Setup; new `setup/ModeSection.tsx` on `OTHER`; `TournamentPicker.tsx` (the second step); `SetupPanel.tsx` and `setup/shared.tsx` (tab set derived from the mode); `setup/SetupTabBar.tsx` (the `PRICING` title); `setup/DisciplinesSection.tsx` and `DisciplineDialog.tsx` (schedule fields, team kind); `setup/PaymentModeSection.tsx`, `BankAccountSection.tsx`, `TimelineSection.tsx` (gating); `Console.tsx` (phase list from the mode); `api.ts`; `i18n/{en,cs}.json`.

**Design constraints**: the mode dialog and the `OTHER` section are subject to `CLAUDE.md` / `openspec/squire-design-spec.md` — no gradients, shadows, radii > 2px, emoji, spinners, or hexes outside `tokens.css`. The dialog follows the existing `.modal-backdrop` / `.modal` pattern used by the creation dialog; the feature hints use the existing `HelpHint` marker.

**Verification**: backend behaviour by `backend/tests/` — a new test module for the flags, the derivation migration, the payments-off completeness rule and the suppressed money paths; frontend by `npm run lint` (`tsc -b --noEmit`), build, and driving the console, since there is no frontend test runner.
