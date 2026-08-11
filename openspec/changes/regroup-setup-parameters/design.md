## Context

Two surfaces edit tournament configuration:

```
  SetupPanel            tabbed, gated by the publish checklist, one save per tab
    tournament          IdentitySection (incl. registration_opens/closes) · Organizers
    disciplines         DisciplinesSection (incl. team_composition_deadline)
    extra               ExtraItemsSection
    payments            BankAccount · Currency · VsSeries · Discounts
    other               TeamSection · DangerZone
    publish             PublishSection

  Console rail          per ETL phase
    ParamPanel          load:     early_bird_until, weapon_rental_fee, afterparty_fee
                        payments: payment_mode, deposit_amount(+eur), seating_deadline,
                                  reservation_validity_days, reminder_day,
                                  amount_tolerance_percent, refundable_until,
                                  expiry_grace_hours, amendments_close
                        export:   output_sheet_url
                        (6 of 9 phases render an empty placeholder card)
```

Facts that shape the design:

- **`ParamPanel` is a generic field loop.** `PHASE_PARAMS` declares `{key, type, options?, hint?, when?}` and the component renders `number`/`date`/`text`/`select` uniformly. It cannot express an input nested inside an option, which the payment mode needs.
- **The publish checklist is the existing definition of Setup.** `setup_missing` keys map through `MISSING_TAB` to tab markers; a key absent from that map marks nothing, by deliberate design so an unrecognized item cannot break the bar. Two keys currently exploit that fallback as a bug rather than a safety net.
- **`amendment_availability` already reduces "unset" to "same window as registration"** (`setup.py:162-172`), so removing the field from the UI produces the requested default with no backend change.
- **Early-bird is two mechanisms, not one.** `early_bird_until` + `Discipline.fee_early` is the legacy path — and `fee_early` has no editor anywhere in the frontend, so the surviving date input cannot change any price. The `early` discount condition (`pricing.py:117`) is the live path, carrying its own `until` date per discount.

## Goals / Non-Goals

**Goals**
- Setup holds every decision about the tournament as a whole; the console holds decisions about people and teams.
- Anything that can block Publish is reachable from a Setup tab that actually contains it.
- The dates are legible as a sequence, so the constraints between them are visible before a save rather than after a rejection.
- The payment mode is chosen by reading its consequence, not by decoding a noun.
- No parameter is deleted at the data level; anything dropped can return without a migration.

**Non-Goals**
- No change to what any parameter means or how the backend reads it.
- No refund workflow. Columns are retained for a future partial-refund policy; nothing is built for it now.
- No revival of `Discipline.fee_early`. The legacy path stays legacy.
- No new console phase, and no change to the ETL phase set.

## Decisions

### Decision 1 — The publish checklist is the test for what belongs in Setup

An item that blocks publication is by definition a pre-publication decision about the tournament as a whole, so it must be editable in the arc that ends at Publish. This is already true of `location`, `disciplines`, `discipline_prices`, `bank_account` and the rest; it becomes true of `deposit_amount` and the legacy fixed fees.

Stated as an invariant the change establishes: **every key `setup.py` can put in `setup_missing` has an entry in `MISSING_TAB`, and the tab it names holds a section that resolves it.** The absent-key fallback stays for forward compatibility with a backend that emits something the client does not know, which is what it was written for.

**Correction, found while verifying (2026-08-05).** Both motivating states turn out to be unreachable through the API, so the invariant is defence in depth rather than a fix for a live defect:

- `deposit_amount` — the write path refuses to enter deposit mode without an amount (`deposit_amount_required`), to clear the amount while in deposit mode, and to enable EUR without the EUR amount. All three return 422.
- `legacy_fixed_fees_block_eur` — enabling EUR on a tournament carrying legacy fixed fees is refused with that same code as a field error.

Neither state exists in the development database. The reorganization stands on the principle rather than on these two bugs, and the invariant is still worth holding: it is what keeps a *future* publish-blocking field from being added without a Setup home, which is how both of these came to look reachable in the first place. `LegacyFeesSection` also remains useful — it is the only way out for a tournament that reached the state before the guard existed, and it stays invisible otherwise.

### Decision 2 — `TIMELINE` sits between `EXTRA` and `PAYMENTS`

The tab bar reads as the order the organizer works in: what the tournament is, what it offers, what those cost, *when it all happens*, how it is paid for. Placing the dates immediately before payments also puts the seating deadline next to the payment mode that refers to it, without the two sharing a tab.

Seven tabs is one more than the `setup-navigation` spec fixed at six. Nothing in that spec depends on the count beyond the enumeration itself.

### Decision 3 — The timeline renders in chronological order, anchored by a read-only tournament date

```
  Registration opens        [ 2026-06-01 ]
  Seating deadline          [ 2026-09-12 ]
  Registration closes       [ 2026-09-30 ]
  Team composition due      [ 2026-10-05 ]
  Tournament                  2026-10-12     ← read-only, set on TOURNAMENT
```

Order is fixed by meaning, not by which field is filled, so an empty date still occupies its place in the sequence and the shape of the timeline does not move as it is filled in. The tournament date appears because a timeline without its endpoint is unreadable; it stays editable only on `TOURNAMENT`, so the field keeps exactly one editor — the same rule the bank account already follows.

`seating_deadline <= registration_closes` is validated server-side. Rendering the two adjacent is what makes that constraint discoverable; the change does not add client-side cross-field validation, which would be a second place for the rule to live.

### Decision 4 — Every date states its fallback

Four of the five are optional and each falls back to a different thing:

```
  registration_opens        unset → open on publication
  seating_deadline          unset → the registration close
  registration_closes       unset → the tournament date
  team_composition_deadline unset → no deadline, no reminders
```

A hint that omits this leaves the organizer unable to tell "not set" from "not applicable". The team composition hint additionally leads with what it does not do — `models.py:199-203` is explicit that it checks and never enforces, and an organizer reading only the label would plan around a lock that does not exist.

### Decision 5 — The payment mode is an option group, not a select

Three nouns cannot carry three different futures. Each option states its consequence in the tournament's own values, so changing the payment window from 5 to 3 rewrites all three sentences:

```
  ( ) Immediate payment
      Full amount due within 5 days of registering.
      Unpaid, the seat is released.

  ( ) Reservation with deposit
      Deposit [ 500 ] Kč due within 5 days, the rest by 12 September.

  (•) Reservation without deposit
      Seat held free until 12 September. Still unpaid then,
      the fencer moves to the queue.
```

The deposit input sits inside its option because it is part of that option's sentence, not a sibling field. That is precisely what `ParamPanel`'s generic loop cannot express, and why this is a section rather than another `FieldType`.

The seating deadline appears in these sentences as read-only prose resolved from the timeline — including its fallback, so an unset deadline reads as *"by 30 September (the registration close)"* rather than as a gap. It is not editable here: one field, one editor.

### Decision 6 — Dropped parameters keep their columns

Nothing is removed at the data level. `refundable_until`, `amendments_close`, `expiry_grace_hours`, `early_bird_until` and the legacy fees keep their columns, their `TournamentUpdate` fields and their defaults. Each can be promoted back to a parameter by re-adding a field, with no migration and no behavioural break in between — `expiry_grace_hours` in particular keeps working at its stored default of 48, so grace reinstatement is unaffected.

This is what makes the cut cheap to reverse, and it is why the change needs no backend work.

### Decision 7 — Legacy fees get an escape hatch, not a migration

A tournament carrying legacy fixed fees on a EUR-priced setup is publish-blocked by `legacy_fixed_fees_block_eur`, and after the fields leave the UI it would have nothing left to clear them with.

A migration that zeroed them would silently change prices on a live tournament, which is worse than the problem. Instead a `LegacyFeesSection` appears on `PAYMENTS` **only while `uses_legacy_fixed_fees` holds**, showing the stored values read-only and offering to clear them. It is invisible on every tournament that does not have the problem, so it does not become a permanent monument to a legacy path.

It patches the four legacy fields through `updateTournament` like any other save — no endpoint, no backend change.

### Decision 8 — `amount_tolerance_percent` stays in the console

It is the one field in `ParamPanel` that is not a pre-publication decision: it is tuned while reconciliation is going badly, against transactions that already exist. It moves into the payments phase's own panel rather than a general-rules card, and `ParamPanel` is deleted rather than kept alive for one field.

`output_sheet_url` is tool configuration rather than a tournament decision, but it is also not an operation parameter, and Setup `OTHER` already holds the console-team and danger-zone sections it most resembles.

## Risks / Trade-offs

- **Seven tabs is a wider bar.** `EXTRA` and `TIMELINE` are both short labels, so the bar grows modestly, but it is now one tab from wrapping on a narrow console. Worth checking at the same widths the preview tabs are checked at.
- **The mode's consequence sentences depend on a value edited on another tab.** An organizer who changes the seating deadline on `TIMELINE` will see the payment sentences change on `PAYMENTS`. That is correct, and it is also a cross-tab effect that no other section has. The read-only rendering has to make clear the date is shown, not owned.
- **Dropping `refundable_until` removes fencer-facing information.** `TournamentDetail.tsx:326-353` tells a fencer whether cancelling now is refundable. With the date no longer settable it will read as never refundable, so the cancel copy must stop promising anything either way rather than asserting the negative.
- **Six of nine console phases lose their placeholder card.** `ParamPanel`'s empty state ("general rules") is the only thing those phases' rails render today. Removing it leaves the rail emptier; whether that reads as clean or as broken should be checked in the running console.
- **The change is large and entirely frontend.** The vitest suite covers pure modules and cs/en locale parity, not rendering, so verification is typecheck, build, those tests, and driving the app. The publish-checklist behaviour in particular has no automated coverage and must be exercised by hand on a deposit-mode tournament and a legacy-fee tournament.
