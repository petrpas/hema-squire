## Why

An organizer configuring a tournament in the console Setup phase cannot see what the
result looks like to a fencer without leaving the console, switching to the fencer
view, and finding the tournament. Because Setup is where prices, disciplines, extra
items, discounts and the qualification text are written, and the fencer-facing
registration form is the only place those settings visibly combine, the organizer is
editing blind — mistakes in pricing or in an extra item's option list are discovered
by fencers rather than by the organizer.

The tournament has exactly two fencer-facing faces: its information page and its
registration form. Both are already built from components inside
`TournamentDetail.tsx`. Showing them beside Setup costs nothing beyond making those
components importable — and reusing them guarantees the preview cannot drift from
what fencers actually see.

## What Changes

- The console Setup phase becomes a two-pane layout: the existing Setup sections on
  the left, a **preview pane** on the right.
- The preview pane carries two tabs, mirroring the tournament's two fencer-facing
  faces:
  - **Tournament face** — the information page: header, schedule, disciplines with
    availability, qualification, organizers, other actions.
  - **Registration form** — the priced checklist a fencer fills in.
- The preview renders through the **same components** the fencer view renders, moved
  into a shared module so both call sites import one implementation. No parallel
  preview markup exists, so any future change to the fencer view appears in the
  preview automatically.
- The preview refreshes when a Setup section is saved. Saving already calls
  `onSaved`, which refetches the tournament detail; the preview re-renders from that
  same detail, so it always shows the tournament's real, currently-published state
  rather than an unsaved draft.
- The previewed registration form is **interactive but cannot be submitted**: the
  organizer can tick disciplines, set quantities and answer option fields and watch
  the running total recompute through the existing read-only price-preview endpoint.
  The submit control is replaced by an inert marker; no registration is ever created
  from the preview.
- The fencer-facing tournament page is **unchanged** — it keeps its information
  screen and its separate register/amend screen. The tabs exist only in the console
  preview.

Non-goals: no live reflection of unsaved edits; no editing of the tournament from
inside the preview; no change to any backend endpoint.

## Capabilities

### New Capabilities

- `setup-preview`: The console Setup phase presenting the tournament's two
  fencer-facing faces beside the settings being edited — its two-pane layout, the
  tab pair, the same-components rule, the non-submitting guarantee, and the
  refresh-on-save behavior.

### Modified Capabilities

None. No existing requirement changes behavior: `tournament-admin` keeps every Setup
editing requirement as written, and `registration` keeps every fencer-facing form
requirement as written — the preview is bound to render through the same components,
so it inherits those requirements rather than restating or altering them.

## Impact

Frontend only; no backend, database, or API change.

- `frontend/src/TournamentDetail.tsx` — `InfoHeader`, `ScheduleLines`,
  `DisciplinesInfo`, `OtherActionsInfo`, `ChecklistRow`, `ItemControls` and
  `RegistrationForm` extracted to a shared module and imported back; the default
  export's behavior is unchanged.
- `frontend/src/SetupPanel.tsx` — wrapped in the new two-pane shell; its own sections
  untouched.
- New `frontend/src/tournamentFace/` (or equivalent shared module) holding the
  extracted components, plus a new preview pane component with the two tabs.
- `frontend/src/index.css` — a two-pane rule for the Setup workspace; the existing
  `.setup-panel` `max-width` no longer governs the whole workspace.
- `frontend/src/i18n/cs.json`, `en.json` — tab labels and the inert-submit marker.
- Existing read-only endpoints reused as-is: `GET /api/tournaments/{slug}`,
  `GET /api/tournaments/{slug}/availability`, `POST` price preview.
