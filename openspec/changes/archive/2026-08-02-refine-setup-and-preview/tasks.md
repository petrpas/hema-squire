## 1. Slug derivation

- [x] 1.1 In `TournamentPicker.tsx`, change `deriveSlug` to append the year only when the slugified base carries no year token, testing `/(^|-)(19|20)\d{2}(-|$)/` on the base (design D1)
- [x] 1.2 Check "Prague Open" + a 2026 date derives `prague-open-2026`
- [x] 1.3 Check "My Tournament 2027" + a 2026 date derives `my-tournament-2027` with no second year
- [x] 1.4 Check "Turnaj 3 zbraní" + a 2026 date derives `turnaj-3-zbrani-2026`, and that a name whose year is already the whole slug tail (`Open 2026`) is not double-suffixed
- [x] 1.5 Check the slug still recomputes as the name and date change, and still stops recomputing once the organizer edits it by hand

## 2. Settings pane structure

- [x] 2.1 In `SetupPanel.tsx`, wrap the tab panels and the save bar in a `.setup-panel-body` element, leaving `.setup-panel-header` as a sibling above it (design D2)
- [x] 2.2 In `index.css`, move the scrolling from `.setup-panel` to `.setup-panel-body`: the panel becomes a non-scrolling column flex container, the body takes `flex: 1` and `overflow-y: auto`
- [x] 2.3 Strip `.setup-panel-header` of `position: sticky`, `top`, `z-index`, and the negative-margin trick with its comment — none of it is needed once the header is outside the scrollport
- [x] 2.4 In the ≤1300px block, give `.setup-panel-body` the same `overflow-y: visible` treatment `.setup-panel` already has, so the stacked layout scrolls as one column
- [x] 2.5 Scroll check: on `TOURNAMENT` scrolled to the bottom, nothing is visible above the checklist and the band above it stays opaque
- [x] 2.6 Sticky-header check: scroll `DISCIPLINES` until the table's column headers stick, and confirm they stick below the pane header, never over it
- [x] 2.7 Narrow-viewport check: below 1300px the preview still stacks below the settings, the header scrolls away with the content, and the save bar is intact

## 3. TOURNAMENT tab

- [x] 3.1 Remove `language` from `IDENTITY_FIELDS`; leave `Tournament.language`, its schemas and every email path untouched (design D4)
- [x] 3.2 Reorder `IDENTITY_FIELDS` to `display_name, subtitle, date, location, description, registration_opens, registration_closes, registration_instructions`
- [x] 3.3 Render `IdentitySection` as three field runs with the logo block after the first and the qualification block after the second, giving the order name, subtitle, logo, date, location, description, qualification, reg. opens, reg. closes, reg. instructions (design D5)
- [x] 3.4 Confirm the save path still patches every field in `IDENTITY_FIELDS` plus qualification, unchanged by the reordering
- [x] 3.5 Change the logo upload and removal from buttons to tertiary underlined text actions matching "add organizer", adding CSS as needed and dropping the `.secondary` button treatment
- [x] 3.6 Check the logo still uploads on file choice and still reports the four distinguishable failures
- [x] 3.7 Check no Setup tab offers the communication language, and that a tournament created with `cs` still sends Czech confirmation emails

## 4. PAYMENTS tab — VS series

- [x] 4.1 Reduce `VsSeriesSection` to a read-only statement of the series and the prefix: remove the input, the `useSectionSaver` registration, the `series` state, and the `vs_series_taken` / `vs_series_frozen` error handling (design D3)
- [x] 4.2 Remove the now-unused `setup.vsSeries.series`, `.seriesHint`, `.taken`, `.frozen`, `.frozenHint` keys from both locale files, keeping `.title` and `.prefix`
- [x] 4.3 Leave the `PATCH` handler's `vs_series` guards and `vs_series_editable` on `TournamentOut` in place; confirm the backend tests covering them still pass
- [x] 4.4 Check the `PAYMENTS` save control counts no pending change for the series on a tournament with no registrations

## 5. Price column labels

- [x] 5.1 Change `setup.disciplines.fee` / `.feeEur` values to "unit price ({{currency}})" / "unit price (EUR)" in `en.json`, and to "jednotková cena …" in `cs.json` (design D6)
- [x] 5.2 Change `setup.extras.price` / `.priceEur` the same way
- [x] 5.3 Change the discount list's fixed-amount column headers the same way
- [x] 5.4 Grep the two locale files for any remaining Setup column header reading "fee" or "price" and bring it into line
- [x] 5.5 Check both currency modes: a single-currency tournament shows one "unit price" column, a CZK + EUR one shows two, on disciplines, extras and discounts alike

## 6. Preview pane

- [x] 6.1 Give `SetupPreview`'s `stage-control` a `preview-tabs` class with `align-self: flex-start`, leaving `.stage-control` itself alone (design D10)
- [x] 6.2 Check on a wide console that the two tabs are as wide as their labels, aligned to the pane's leading edge
- [x] 6.3 Delete `.detail-extra::before` so the subordinate when/where/ruleset line carries no leading dash (design D7)
- [x] 6.4 Check the line still reads as subordinate — one size down, faded ink — and that its parts are still separated by the spaced middle dot, on both a discipline and an action row

## 7. Registration form

- [x] 7.1 Add top margin to `.registration-instructions` larger than the inter-section gap (design D8)
- [x] 7.2 Give `.form-total` the same larger top margin, `text-align: right`, and right padding matching the checklist's price column, with a comment tying the two values together
- [x] 7.3 Remove the `aftersparring` checkbox and the `accommodation` field from `RegistrationForm`, along with their state and their `form.aftersparring` / `form.accommodation` locale keys (design D9)
- [x] 7.4 Keep the note field under the `form.sections.other` heading; relabel `form.remarks` to "Note" in `en.json` and "Poznámka" in `cs.json`
- [x] 7.5 Keep sending `aftersparring: false` and `accommodation: null` in the submit and amend payloads; leave the backend schema untouched
- [x] 7.6 Check a real in-app registration: the reservation is created, the total is unchanged, and the note is stored and visible to the organizer
- [x] 7.7 Check an amendment of an existing registration that had an accommodation note set — it saves without error, and the total is unchanged
- [x] 7.8 Check the total is aligned over the price column on a form with a long price such as `1 450 Kč (58 €)`

## 8. Verification

- [x] 8.1 Run the frontend build and lint; no unused imports, state, or locale keys left behind
- [x] 8.2 Run the backend test suite; nothing should have moved, including the VS-series collision and frozen tests
- [x] 8.3 Walk all five Setup tabs against `openspec/enhancements.md` and confirm each listed item
- [x] 8.4 Walk both preview tabs against the same list, on a tournament with disciplines carrying when/where/ruleset and at least one action item
- [x] 8.5 Check the design prohibitions in `CLAUDE.md` hold for every control added or restyled — no new hex outside `tokens.css`, no radius above 2px, no button where a text action was specified
- [x] 8.6 Sync the six deltas into `openspec/specs/` and archive the change
