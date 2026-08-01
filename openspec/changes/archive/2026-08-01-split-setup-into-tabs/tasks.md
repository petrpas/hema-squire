## 1. Tab shell

- [x] 1.1 In `frontend/src/SetupPanel.tsx`, add the `SetupTab` type and the `SETUP_TABS` order constant (`tournament`, `disciplines`, `extra`, `payments`, `other`) at module level
- [x] 1.2 Add the `MISSING_TAB` map from `setup_missing` keys to tabs (`location`, `organizers` → tournament; `disciplines`, `discipline_prices` → disciplines; `extra_item_prices` → extra; `discount_prices`, `legacy_fixed_fees_block_eur` → payments), with lookup falling back to "no tab" for unknown keys
- [x] 1.3 Add `const [tab, setTab] = useState<SetupTab>("tournament")` to the default export and compute the offered tab list as `isOwner ? SETUP_TABS : SETUP_TABS.filter(t => t !== "other")`
- [x] 1.4 Wrap `ChecklistSection` and the new tab bar in a `.setup-panel-header` inside `.setup-panel`, above the panels

## 2. Section allocation

- [x] 2.1 Wrap `IdentitySection` and `OrganizersSection` in the `tournament` panel, in that order
- [x] 2.2 Wrap `DisciplinesSection` in the `disciplines` panel
- [x] 2.3 Wrap `ExtraItemsSection` in the `extra` panel
- [x] 2.4 Wrap `CurrencySection`, `VsSeriesSection` and `DiscountsSection` in the `payments` panel, in that order
- [x] 2.5 Wrap the owner-only `TeamSection` and `DangerZoneSection` in the `other` panel, keeping their existing `isOwner` gates
- [x] 2.6 Render every panel as `<div className="setup-tabpanel" hidden={tab !== id}>` so all sections stay mounted, passing each section the props it receives today

## 3. Tab bar and markers

- [x] 3.1 Render the bar as `nav.stage-control.setup-tabs` with one button per offered tab, `active` on the selected one, labels from `setup.tabs.*`
- [x] 3.2 Compute the marked-tab set from `detail.setup_missing` through `MISSING_TAB` and render a `.tab-mark` span inside each marked tab's button, with a visually-hidden `setup.tabs.incomplete` label
- [x] 3.3 Add the tabs ARIA wiring: `role="tablist"`, `role="tab"` + `aria-selected` + `aria-controls`, `role="tabpanel"` + `aria-labelledby`
- [x] 3.4 Add left/right arrow-key movement between tabs in the tablist

## 4. Saver registry

- [x] 4.1 Define the `SectionSaver` type (`pendingCount`, `touchesPrice`, `validate()`, `flush()`) and a `SaveOutcome` type carrying the change, its section, and any server error
- [x] 4.2 Add the `useSectionSaver(tab, id, saver)` hook writing into a `Map` ref held by `SetupPanel`, removing its entry on unmount
- [x] 4.3 Add `SetupSaveBar`: reads the savers registered to the active tab, sums `pendingCount`, and renders one save control stating the count, inert at zero
- [x] 4.4 Implement the save flow — `validate()` on every saver first, abort without writing if any returns false; then `flush()` sequentially in section order; then call `onSaved` exactly once
- [x] 4.5 Collect `SaveOutcome`s and render the result at the save bar: what was written, what remains pending, and the server's reason against each failed change
- [x] 4.6 Move `usePriceChangeGuard` to the save bar: raise `PriceChangeWarning` once before flushing when any saver reports `touchesPrice` and `hasRegistrations` is true; cancelling writes nothing

## 5. Field sections give up their save buttons

- [x] 5.1 `IdentitySection` — remove its bottom save button, register a saver whose `flush()` performs the existing `updateTournament` patch; keep logo upload and removal immediate and visually distinct from the save control
- [x] 5.2 `OrganizersSection` — same treatment; `pendingCount` counts the organizer list as one pending change when dirty
- [x] 5.3 `VsSeriesSection` — same treatment, keeping the `vs_series_editable` gate
- [x] 5.4 `CurrencySection` — same treatment, keeping the currency-mode invariants
- [x] 5.5 `DiscountsSection` — same treatment; the whole discount list stays one patch, and "add discount" becomes a tertiary text action
- [x] 5.6 Confirm every field section reports `touchesPrice` correctly (currency and discounts do; identity, organizers and VS series do not)

## 6. Row tables become drafts

- [x] 6.1 `DisciplinesSection` — replace the `detail`-derived draft map with an owned `rows: Draft[]` plus `removed: Set<code>`, reseeded from `detail` only while the section is clean
- [x] 6.2 `+` appends a local row with a temporary id and makes no server call; remove the per-row save (`IconCheck`) control entirely
- [x] 6.3 `✕` removes the row from `rows` at once and records it in `removed` when it exists on the server
- [x] 6.4 `validate()` marks rows missing a code or capacity and returns false; `pendingCount` = added + edited + removed
- [x] 6.5 `flush()` performs deletes, then updates, then creates, resolving one `SaveOutcome` per change
- [x] 6.6 Repeat 6.1–6.5 for `ExtraItemsSection` (validation: name and price; the category/kind rules are unchanged)
- [x] 6.7 Check that a `detail` refetch caused by another tab's save cannot stomp drafted rows in these two sections

## 7. Styling

- [x] 7.1 Add `.setup-tabpanel[hidden] { display: none }` and a `.setup-tabpanel` flex-column rule with the settings pane's existing `gap`, so within-tab spacing is unchanged
- [x] 7.2 Add `.setup-tabs` layout on top of the existing `.stage-control` treatment — no new colors, no new radius
- [x] 7.3 Add `.setup-panel-header` as `position: sticky; top: 0; background: var(--paper)` with a hairline bottom border; drop the sticky positioning if it fights `.setup-panel`'s `overflow-y: auto`
- [x] 7.4 Add `.tab-mark` as a 4px `--stamp` square at `var(--radius)`, plus a visually-hidden utility class if one does not exist
- [x] 7.5 Add `.setup-save-bar` at the bottom of the settings pane and give the save control the design system's primary/secondary treatment
- [x] 7.6 Demote "recalculate missing" (three sections), "add discount" and "add row" from `.secondary.param-save` to the tertiary underlined-text style
- [x] 7.7 Confirm no hex outside `tokens.css` and no prohibited pattern (shadow, radius > 2px, second saturated color) was introduced

## 8. Leaving Setup

- [x] 8.1 Have `SetupPanel` report an aggregate dirty boolean upward through a new `onDirtyChange` prop
- [x] 8.2 In `frontend/src/Console.tsx`, intercept a phase change away from Setup while dirty and confirm, stating the changes will be discarded; declining stays in Setup with everything intact

## 9. Localization

- [x] 9.1 Add `setup.tabs.*` (five labels + `incomplete`) to `frontend/src/i18n/cs.json` and `en.json`
- [x] 9.2 Add the save-bar copy: the pending count, the nothing-to-save state, the partial-write report, and the per-row error marker
- [x] 9.3 Add the leave-Setup confirmation copy; lowercase in source, no exclamation marks, no Title Case

## 10. Verification

- [x] 10.1 `cd frontend && npm run lint && npm run build` clean
- [x] 10.2 Allocation check: every section that existed before appears on exactly one tab, in the specified order, none duplicated or lost
- [x] 10.3 One-writer check: each editing tab has exactly one save control, no section or row has one, and `OTHER` has none
- [x] 10.4 Draft check: add a discipline row, edit another, delete a third; confirm nothing changed on the server (preview unchanged, reload shows the original) until the tab is saved
- [x] 10.5 Flush check: save that tab and confirm all three changes are written, the detail is refetched once, and the count returns to zero
- [ ] 10.6 Partial-failure check: force a server rejection on one of several pending changes; the others stay written, the rejected one stays pending with its reason shown, and the bar does not report success
- [ ] 10.7 Retry check: correct the rejected change, save again, and confirm nothing already written is written twice
- [x] 10.8 Validation check: a drafted row missing a required value is marked, blocks the save, and no other pending change is written by that attempt
- [x] 10.9 Price-warning check: with registrations present, a tab save touching prices warns once, and cancelling writes nothing
- [x] 10.10 State check: type into a discipline row, switch to `PAYMENTS` and back — the value is still there and still unsaved
- [x] 10.11 Marker check: with a discipline missing a price as the only gap, only `DISCIPLINES` carries the `--stamp` dot; fill it, save, and confirm the dot clears — and that the dot is never confused with the save bar's pending count
- [ ] 10.12 Unknown-key check: an unmapped `setup_missing` key shows as a chip, marks no tab, and does not break the bar
- [x] 10.13 Owner check: as a non-owner console member, `OTHER` is not offered and the other four tabs work
- [x] 10.14 Leave-Setup check: with unsaved changes, switching to another phase confirms; declining keeps everything; a clean Setup leaves without asking; switching tabs never asks
- [x] 10.15 Preview check: the preview stays beside all five tabs, never shows drafted rows, keeps its own tab across settings-tab switches, and refreshes after a tab save
- [x] 10.16 Narrow-viewport check: below 1300px the preview still stacks below the settings, with the tab bar and save bar intact
- [x] 10.17 Keyboard check: the tab bar is reachable, arrow keys move between tabs, focus rings use `--focus`, and no hidden panel's fields are reachable by tabbing

## 11. Close out

- [x] 11.1 Run `openspec validate split-setup-into-tabs --strict` and fix any reported issue
- [ ] 11.2 Sync the `setup-navigation` and `setup-preview` deltas into `openspec/specs/` and archive the change
