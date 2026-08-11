## 1. Tab structure

- [x] 1.1 Add `timeline` to `SetupTab` and `SETUP_TABS` in `frontend/src/setup/shared.tsx`, between `extra` and `payments` (design Decision 2)
- [x] 1.2 Add the tab panel to `SetupPanel.tsx` following the existing `role="tabpanel"` / `hidden` pattern, with its `aria-labelledby` wired like its siblings
- [x] 1.3 Add `timeline` to `SECTION_ORDER` and register its sections with the `SaverRegistry` like every other tab
- [x] 1.4 Czech and English labels for the tab, lower case like their siblings: English `timeline`, Czech `termíny` (owner's call, 2026-08-05 — the phrase an organizer actually uses, over the literal `časová osa`)
- [x] 1.5 Check the tab bar at the widths the preview tabs are checked at — seven labels is one from wrapping on a narrow console (design Risks)

## 2. Timeline section

- [x] 2.1 New `frontend/src/setup/TimelineSection.tsx`: `registration_opens`, `seating_deadline`, `registration_closes`, `team_composition_deadline`, in that fixed chronological order, each with a hint
- [x] 2.2 Render `Tournament.date` at the foot, read-only, as the anchor, naming `TOURNAMENT` as where it is edited (design Decision 3)
- [x] 2.3 Keep an unset date in its place in the sequence — order is fixed by meaning, not by which fields are filled
- [x] 2.4 Show `team_composition_deadline` only while a team discipline exists, including one added in the current unsaved `DISCIPLINES` draft; a stored deadline on a tournament with no team disciplines is retained, not cleared
- [x] 2.5 Hint copy, en and cs, each stating its fallback (design Decision 4):
  - registration opens — before it the tournament is visible but nobody can enter; unset, it opens on publication
  - seating deadline — not the registration close; after it registration stays open but grants only a queue place and unpaid reservations move below the line; unset, it falls on the registration close
  - registration closes — the hard close, nothing accepted after; unset, it falls on the tournament date
  - team composition — leads with what it does **not** do: reminds only, locks no roster, cancels no team, frees no capacity; unset, no deadline and no reminders
- [x] 2.6 Remove `registration_opens` / `registration_closes` from `setup/IdentitySection.tsx`, leaving the tournament date, and check its save path still covers the fields it keeps
- [x] 2.7 Remove `team_composition_deadline` from `setup/DisciplinesSection.tsx`, including its saver registration and its `MISSING_TAB`-adjacent behaviour

## 3. Payment mode section

- [x] 3.1 New `frontend/src/setup/PaymentModeSection.tsx`, standing first on `PAYMENTS`: three options for `payment_mode`, each with a one-line consequence built from the current form values (design Decision 5)
- [x] 3.2 Nest the `deposit_amount` input inside the deposit option, with `deposit_amount_eur` beside it when the tournament prices in EUR
- [x] 3.3 Add `reservation_validity_days` (the payment window) and `reminder_day` to the section; the consequence sentences read the window live, so changing it rewrites them without a save
- [x] 3.4 Resolve the seating deadline for the sentences from the timeline value, falling back to the registration close and then the tournament date, and render it as read-only prose naming the fallback where it applies — never as a field (design Decision 5)
- [x] 3.5 Add an editor for `unpaid_list_treatment` — specced, exposed in `api.ts`, and with no editor anywhere in the frontend today
- [x] 3.6 Czech and English strings for the mode names, the three consequences, the deposit, the window, the reminder day and the unpaid-list treatment
- [x] 3.7 Verify against `CLAUDE.md` / `squire-design-spec.md`: no radii above 2px, no shadows, no emoji, no spinners, no hex outside `tokens.css`, no Title Case in the option text, and no second saturated colour in the option group

## 4. Legacy fees escape hatch

- [x] 4.1 New `frontend/src/setup/LegacyFeesSection.tsx` on `PAYMENTS`, rendered only while the tournament carries legacy fixed fees (`weapon_rental_fee`, `afterparty_fee` or either `_early` sibling is set)
- [x] 4.2 Show the stored values read-only and offer a single clear action patching all four to their empty state through `updateTournament` — no endpoint, no migration (design Decision 7)
- [x] 4.3 Czech and English strings explaining that these are the superseded pricing path, that extra-service items replace them, and that clearing unblocks EUR
- [x] 4.4 Confirm the section is absent on a tournament with no legacy fees

## 5. Fields leaving the UI

- [x] 5.1 Remove `refundable_until`, `amendments_close`, `expiry_grace_hours`, `early_bird_until`, `weapon_rental_fee`, `afterparty_fee` from every editor. Columns, `TournamentUpdate` fields and defaults are untouched (design Decision 6)
- [x] 5.2 Stop asserting refundability in the fencer's cancel copy (`TournamentDetail.tsx:326-353`): with `refundable_until` unsettable it would read as never refundable, which is a promise in the other direction. The copy should say neither (design Risks)
- [x] 5.3 Leave `RefundState`, `refundable` and `refund_state` in `api.ts` and in the model — retained for a future partial-refund policy
- [x] 5.4 Leave `markTransactionForRefund` and the flagged-transaction action in `PaymentsPanel.tsx` alone: it marks money for manual return and is the only exit from the flagged queue

## 6. Console side

- [x] 6.1 Move `amount_tolerance_percent` into the payments phase's own panel, keeping its `checkPercent` validation (design Decision 8)
- [x] 6.2 Move `output_sheet_url` to Setup `OTHER`, keeping its `checkUrl` validation, and add it to the `OTHER` allocation
- [x] 6.3 Delete `frontend/src/ParamPanel.tsx` and its import and usage in `Console.tsx`
- [x] 6.4 Check the rails of the six phases that rendered only `ParamPanel`'s placeholder card — confirm an emptier rail reads as clean rather than broken (design Risks)
- [x] 6.5 Remove the now-unused `rail.parameters` / `rail.generalRules` strings if nothing else claims them

## 7. Publish checklist attribution

- [x] 7.1 Add `deposit_amount: "payments"` to `MISSING_TAB` in `setup/shared.tsx` — today it is absent, so the item marks no tab and, when it is the only one, `PUBLISH` is left unmarked too
- [x] 7.2 Confirm `legacy_fixed_fees_block_eur: "payments"` now names a tab that actually holds the section resolving it (task 4)
- [x] 7.3 Cross-check every key `backend/app/setup.py` can emit against `MISSING_TAB`: `location`, `organizers`, `disciplines`, `discipline_prices`, `team_bounds`, `extra_item_prices`, `discount_prices`, `legacy_fixed_fees_block_eur`, `bank_account`, `deposit_amount`. Every one has an entry and its tab holds a resolving section (design Decision 1)
- [x] 7.4 Keep the unrecognized-key fallback — it exists for a backend ahead of a deployed client, and must not break the bar

## 8. Verification

- [x] 8.1 `npm run lint` (`tsc -b --noEmit`) and `npm run build` in `frontend/`
- [x] 8.2 `pytest` in `backend/` — expected untouched, run to confirm
- [ ] 8.3 BLOCKED — the state is unreachable. `schemas`/`routers.tournaments` refuse to enter deposit mode without an amount (`deposit_amount_required`), to clear the amount while in deposit mode, and to enable EUR without the EUR amount. `MISSING_DEPOSIT_AMOUNT` is therefore defensive-only, and no tournament in the dev DB is in that state. The `MISSING_TAB` entry added in 7.1 is correct and keeps the parity invariant, but the bug it fixes cannot currently occur — see the note added to design.md
- [x] 8.4 Drive Setup on a **EUR tournament carrying legacy fees**: `PAYMENTS` carries the marker, the clear action is offered, clearing unblocks publication
- [x] 8.5 Drive the timeline: set each date in turn, confirm the order never moves, the hints state their fallbacks, and the tournament date has no field
- [x] 8.6 Drive the payment mode: switch between all three, confirm the consequence text follows the payment window and the seating deadline, and that an unset deadline reads as the registration close
- [x] 8.7 Confirm no tournament parameter remains reachable from any console phase panel, and that a tournament configured before this change opens with every stored value intact
