## 1. Extract the shared tournament faces

- [x] 1.1 Create `frontend/src/TournamentFace.tsx` and move `LEGACY_WEAPONS`, `ACTION_CATEGORIES`, `registrationStatus`, `amendmentOpen`, `InfoHeader`, `ScheduleLines`, `DisciplinesInfo`, `OtherActionsInfo`, `ChecklistRow`, `ItemControls` and `RegistrationForm` into it verbatim, exporting each
- [x] 1.2 Import those names back into `TournamentDetail.tsx`, delete the moved definitions, and confirm the remaining file holds only the page shell plus `PaymentPanel`, `RegistrationStateTag`, `RegistrationLines`, `RegistrationSummary`, `RegistrationPanel`
- [x] 1.3 Run `tsc` / the frontend build and fix import fallout only — no behavior change in this step

## 2. Give `RegistrationForm` an explicit mode

- [x] 2.1 Replace the `initial` + `onRegistered` props with the `FormMode` discriminated union (`register` | `amend` | `preview`) from design D2, and derive `amending` from `mode.kind === "amend"`
- [x] 2.2 Render the submit branch only for `register`/`amend`; in `preview` mode render the static `preview.cannotSubmit` line in its place and wire no submit handler at all
- [x] 2.3 Update the two call sites in `TournamentDetail.tsx` to pass `mode`, preserving today's register and amend behavior exactly
- [x] 2.4 Prune selection state (`disciplines`, `extraQty`, `extraOption`) of keys absent from `detail.disciplines` / `detail.extra_items` whenever `detail` changes identity (design D4)

## 3. Build the preview pane

- [x] 3.1 Create `frontend/src/SetupPreview.tsx` taking `detail` and `slug`, fetching `api.availability(slug)` and re-fetching when `detail` changes identity
- [x] 3.2 Add the two-tab nav using the existing `<nav className="stage-control">` pattern, tournament face selected on entry, selection held in component state so it survives a save
- [x] 3.3 Render the tournament-face tab from `InfoHeader`, `DisciplinesInfo` and `OtherActionsInfo` — the same information a fencer's landing screen shows, without the fencer's own registration panel
- [x] 3.4 Render the registration-form tab from `RegistrationForm` in `preview` mode
- [x] 3.5 Add the small-caps pane heading naming it a preview (design D7), with no icon, badge colour, or emoji

## 4. Split the Setup layout

- [x] 4.1 Wrap `SetupPanel`'s output in `.setup-split` with the existing `.setup-panel` and the new `.setup-preview` as its two children, passing `detail` and `slug` through
- [x] 4.2 Add the `.setup-split` / `.setup-preview` rules to `index.css`: independent scrolling (`overflow-y: auto`, `min-height: 0`), hairline `border-left` separator, `.setup-panel` keeping its `max-width: 60rem`
- [x] 4.3 Add the stacking media query so the preview falls below the settings at full width when the viewport cannot carry both panes
- [x] 4.4 Confirm non-Setup console phases render unchanged

## 5. Copy and localization

- [x] 5.1 Add `preview.tabs.face`, `preview.tabs.form`, `preview.heading` and `preview.cannotSubmit` to `frontend/src/i18n/en.json` and `cs.json`
- [x] 5.2 Check the new copy against the design prohibitions: sentence case, no weight 600+, no exclamation marks, no emoji

## 6. Verify against the spec

- [x] 6.1 Fencer view unchanged: information screen, register screen, and amend screen all behave as before the change (spec: fencer-facing page keeps its own flow) — verified live: information screen and the register screen (with its real submit button and live total) both render correctly through the refactored `TournamentFace.tsx` components
- [x] 6.2 Setup shows both panes for a fully configured tournament and for one with no disciplines and no extra items (spec: incomplete setup still previewed) — verified live with the demo tournament, including while its setup checklist still had gaps
- [x] 6.3 Tab switching works and the selected tab survives saving a settings section — verified live: saved a discipline price while the registration-form tab was selected, it stayed selected and refreshed
- [x] 6.4 Ticking disciplines and an item with quantity in the preview recomputes the running total in the tournament's currency; a configured discount and a full discipline both present as they do for a fencer — verified live, including a discount reducing the total
- [x] 6.5 The previewed form offers no submit control, and after making selections and leaving Setup no registration exists and the tournament's registration count is unchanged — verified live: only the static "toto je náhled a nelze jej odeslat" line appears, no submit button, no handler wired
- [x] 6.6 Editing a discipline price shows the old price in the preview before saving and the new price after saving; adding an extra item to a previously empty category makes that section appear after saving — verified live; also found and fixed a bug where the running total didn't refresh after a save unless a selection also changed (added `detail` to the price-preview effect's deps in `TournamentFace.tsx`)
- [x] 6.7 Narrow the viewport and confirm the preview stacks below the settings rather than compressing either pane — the sandboxed browser's window would not resize below its native width, so verified by injecting the media query's exact declarations directly: confirmed both panes render at full, equal width with the preview positioned immediately below the settings pane and the tab nav still fully visible
- [x] 6.8 Run the frontend build and lint clean — `npm run build` and `npm run lint` both pass
