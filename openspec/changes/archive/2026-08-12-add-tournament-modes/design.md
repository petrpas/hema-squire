## Context

Setup is currently one shape for every tournament: seven tabs fixed by `setup-navigation`, the payment-mode/deposit/seating machinery fixed by `tournament-admin`, team roster bounds and a composition deadline fixed by `team-disciplines`, an extra-items table, per-discipline `when`/`where`. A small event uses perhaps a third of it and is blocked from publishing by a bank account it does not want, because `setup.charges_money()` makes the account mandatory the moment any price is nonzero.

The constraint that shapes this design is that Squire is one SQLite file and one deployment, and every one of those features is already built, wired and specified. This change must not fork the product into two codebases with two behaviours; it must add a lens. The lens is four flags on the tournament.

Three seams already exist and are worth naming, because the design leans on all three. `SetupTabBar` already takes its tab list as a prop, and `OTHER` is already conditionally absent for non-owners — so a mode-dependent tab set is a change of input, not of structure. `setup.charges_money()` / `setup_missing()` is the single place completeness is decided. `scheduler.run_tournament_tick()` is the single place reminders, expiry and settlement are driven per tournament.

## Goals / Non-Goals

**Goals:**

- A first-time organizer creating a one-discipline tournament meets four fields and a publish button, and is never blocked by a setting they have no use for.
- A feature turned off can be turned back on with every stored value intact, at any time, with no migration and no data loss.
- One tournament looks the same to every organizer on its console team.
- Tournaments that predate the mode keep every setting they have configured visible.
- The payments feature, when off, genuinely stops asking fencers for money — including through publication, email and the scheduler — rather than hiding the settings while the machinery runs on.

**Non-Goals:**

- Changing what any retained setting means, or what any feature does when it is on.
- A per-user or per-role view of Setup. The mode is the tournament's, not the reader's.
- Removing anything. Every field, table and phase this change conceals is still reachable by turning its feature on.
- A fifth feature, or a mode that gates disciplines, registration windows, publication or the console's ETL phases — those are what every tournament is made of.

## Decisions

### D1 — Four booleans on the tournament, not a mode enum

`feature_schedule`, `feature_payments`, `feature_teams`, `feature_extras` as non-null booleans on `Tournament`, defaulting to false.

*Alternative considered:* a `TournamentMode` enum (`easy` / `advanced`) plus a JSON set of enabled features. Rejected because it stores the same fact twice — an `advanced` tournament with no features enabled and an `easy` one are indistinguishable in behaviour but distinguishable in the database, and every consumer would have to decide which of the two fields it trusts. Four booleans have exactly one representation per state.

*Alternative considered:* a JSON `features` column. Rejected because these are queried (the scheduler must skip payments-off tournaments; the migration backfills by derivation) and because a typo in a JSON key fails silently where a typo in a column name does not.

### D2 — Easy mode is the absence of features, not a stored value

Easy mode is `not any(flags)`. The radio in the dialog is a presentation of that predicate: choosing "easy" clears all four, choosing "advanced" reveals the checkboxes and requires at least one — an advanced tournament with nothing enabled is easy mode and is stored, and named, as such.

This is why `OTHER` states the mode as a computed line ("easy mode", or "advanced: payments, team disciplines") rather than echoing a stored label. There is no state where the label and the behaviour can drift.

### D3 — The mode belongs to the tournament, not to the reader

Stored on the tournament, changed through a tournament endpoint, subject to the same console-team authorization as any other Setup write. Every organizer on the team sees the same Setup.

*Alternative considered:* a per-account client-side preference. Rejected because two organizers debugging a tournament together would see different screens, and because "the bank account section isn't there" would become a support question with no answer visible to the person asking.

### D4 — Changing the mode writes nothing but the mode

A mode change SHALL NOT clear a hidden field, delete a hidden row, or reset a hidden parameter. `feature_teams = false` on a tournament with a team discipline leaves that discipline exactly as it was, roster bounds included. This is what makes the mode safe to experiment with, and it is the reason the flags are a lens rather than a configuration wizard.

The corollary is that hidden state can still be non-empty, so nothing downstream may assume a flag implies the absence of the data it conceals. `setup_missing()` in particular still validates roster bounds on a team discipline whose feature is off — the discipline exists, it is published, it is sold.

### D5 — Payments is the one flag that is not presentational

The other three flags hide organizer-facing controls and change nothing a fencer experiences: a hidden extra item is still sold, a hidden team discipline still takes teams, a hidden `when` is still shown on the tournament page. That is deliberate and was chosen explicitly — the organizer hides *settings they are done with*, not products they are selling, and the confirmation names exactly that.

Payments cannot work that way. "Hide the bank account field but keep emailing fencers a QR code drawn on the account" is not a simpler tournament, it is a broken one. So payments-off is a behavioural switch, applied at four points:

- **Completeness** (`setup.setup_missing`): the bank account requirement is conditioned on payments being on, so a priced tournament publishes without an account. Every other item — including EUR prices and roster bounds — is unaffected, because those are about what the tournament offers, not about collecting for it.
- **Registration** (`routers/registrations.py`, `pricing.py`): the total is still computed and shown; no payment window opens, `payment_due_at` stays null, and no variable symbol is put to work.
- **Email** (`emails.py`, `spayd.py`): the confirmation carries the summary and the total as information, with no account block and no QR attachment. Reminder, expiry, surcharge and payment-received mails are never sent, because nothing generates them.
- **Scheduler** (`scheduler.run_tournament_tick`): reminders and expiries are skipped for payments-off tournaments. Seating settlement and composition reminders are not — they are about seats and rosters.

Ingestion and reconciliation (`bank.py`, `matching.py`, `routers/payments.py`) are scoped to payments-on tournaments, and the console's Payments phase is not offered. A payments-off tournament has no transactions to reconcile, and a request that tries is refused rather than silently doing nothing.

### D6 — Payments off introduces no registration state

A payments-off registration is `RESERVED`, which is what "seated" already means in this schema, with `payment_due_at` null. No new enum member, no migration of existing rows, no new branch in the several places that read `RegistrationState`.

`process_expiries` already needs a due date to expire anything, so a null due date is inert by construction rather than by a new guard — which also settles what happens when payments are turned *on* later: those registrations have no due date, so nothing expires retroactively. They sit as reserved until the organizer acts on them, which is the correct and conservative outcome and is worth stating in the spec rather than leaving to be discovered.

The fencer-facing surfaces read the flag, not the state: a payments-off `RESERVED` registration is presented as confirmed, and `fencer-home` offers no payment-instructions view for it.

### D7 — The payments tab narrows to `PRICING`; it is not removed

Currency and discounts survive payments being off — that is the source note's explicit instruction, and it is right: a tournament that prices in CZK and gives club members a discount is still doing that when Squire is not collecting the money. So the tab stays and holds those two sections, titled `PRICING`.

**The tab's identifier stays `payments`.** Only its title changes. The identifier is what the URL, the incompleteness-marker map and the tab-panel `aria-controls` are built from; renaming it would break the marker attribution fixed by `setup-navigation` for a cosmetic gain. This is a title lookup, not a new tab.

*Alternative considered:* folding currency and discounts into `DISCIPLINES` and dropping the tab in easy mode. Rejected: it makes the section allocation a function of the mode in two directions at once, and a discount list under a tab named for disciplines is a worse lie than the one it fixes.

### D8 — An extra item's time and place are not the tournament schedule

The schedule flag governs the discipline's `when`/`where` only. `ExtraItem.schedule_when` / `schedule_where` remain offered whatever the flag says, because "Saturday 20:00, Klub Fér" is how an after-party is described, not a multi-day event's logistics. This follows the source note directly and keeps the flag's label honest: it says *disciplines* specify where and when they occur.

### D9 — Existing tournaments are derived once, in the migration, and never again

The migration adds the four columns defaulting to false and immediately backfills:

| flag | on when |
| --- | --- |
| `feature_schedule` | any discipline has a non-empty `schedule_when` or `schedule_where` |
| `feature_payments` | `bank_account` is non-empty, or `payment_mode != immediate`, or any bank transaction exists for the tournament |
| `feature_teams` | any discipline has kind `team` |
| `feature_extras` | any extra item exists |

Derivation is generous: any evidence at all turns the flag on, so the worst case for an existing organizer is that their console looks exactly as it does today. A never-configured draft lands in easy mode, which is the point.

Derivation is **not** a rule the application maintains. It runs once. Adding a team discipline later does not flip `feature_teams` — the organizer turns the feature on to get the control that adds one, so the case does not arise through the UI, and re-deriving at runtime would make D4 impossible to hold (the flag would fight the organizer's own choice to hide something).

### D10 — The warning is built from a server-computed in-use report

Turning a feature off names what will be hidden. The counts come from the tournament payload the console already holds where possible (`disciplines`, `extra_items`), and from the tournament's own fields for payments (account recorded, mode, deposit). Nothing new is fetched to open the dialog; the report is derived client-side from state Setup already has, so the dialog opens instantly and stays correct as the organizer's unsaved drafts change.

Turning a feature **on** is never warned. There is nothing to lose.

### D11 — Creation defaults to easy mode and the dialog is dismissible

`TournamentCreate` sets all four flags false. The mode dialog opens after the tournament is created — not as a second page of one form — because the tournament must exist before it can carry a mode, and because a failure to set the mode must not lose a successfully created tournament. Dismissing the dialog therefore leaves an easy-mode tournament and lands the organizer in Setup exactly as today; nothing is left half-created.

The radio preselects easy mode, which is both the stored state and the recommendation.

### D12 — The API stays permissive for the three presentational flags

The backend does not refuse to store a team discipline because `feature_teams` is false, or an extra item because `feature_extras` is false. Those flags describe which controls Setup offers, and the data they conceal is legitimately present (D4). Only the payments flag is enforced server-side, because only it changes what the system does.

This keeps the flags from becoming a second, weaker validation layer that every endpoint must consult and every test must set up.

## Risks / Trade-offs

- **An organizer hides a feature and forgets what it held.** → The `OTHER` section always states the mode in words, the disable warning names the counts, and re-enabling restores everything untouched. Nothing is destroyed by forgetting.
- **Payments turned off on a live tournament mid-reconciliation.** → The warning names the recorded account and the credited payments. Credited money, transactions and payment events are retained; expiry stops rather than firing; already-issued variable symbols are not reissued or renumbered. Turning payments back on resumes with everything present.
- **A published, priced, payments-off tournament shows fencers a total with no way to pay it in-app.** → That is the feature, not a defect: the money is settled outside Squire. The registration-instructions field is the organizer's place to say how, and it is offered on `TOURNAMENT` in every mode.
- **A rollback that drops the columns turns every tournament advanced again.** → Behaviourally safe for the three presentational flags. The one sharp edge is a payments-off tournament published without a bank account: after a rollback it fails the completeness check on its next save. The mitigation is that `guard_published_completeness` reports the missing account clearly and the organizer can supply one — no tournament is un-published and no registration is lost.
- **Two dialogs at creation is more friction than one.** → Accepted deliberately. The alternative is a longer single form, which is what this change exists to get away from, and the second dialog is dismissible.
- **The mode is a lens over a codebase that assumes all features exist**, so a future feature will need a decision about which flag, if any, conceals it. → Accepted; the flag set is deliberately small and closed. A fifth feature is out of scope here.

## Migration Plan

1. One Alembic revision: add `feature_schedule`, `feature_payments`, `feature_teams`, `feature_extras` as non-null booleans defaulting to false, then backfill by the D9 derivation in the same revision, so no tournament is ever observable in the wrong mode.
2. Backend behaviour (completeness, registration, email, scheduler, payments scoping) ships with the migration, since the completeness rule reads a column that must exist.
3. Frontend ships after, reading the flags from `TournamentOut`. A frontend that predates the change ignores the fields and renders as today, which is a correct intermediate state.
4. Rollback: down-revision drops the four columns; see the risk above for the one case that needs an organizer's attention.

## Open Questions

- Should the mode be changeable after publication? This design says yes, with the same warning, on the grounds that a published tournament can already have its prices, dates and disciplines edited within the completeness guard. If it turns out organizers hide payments on a published tournament by accident, locking the payments flag after the first credited transaction is the narrow fix.
- Refunds are settled outside the system today (`tournament-admin`), so payments-off changes nothing about them. When a refund policy arrives it will need to state what it means on a payments-off tournament.
