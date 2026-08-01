## Why

The Setup phase is one continuous column of ten sections — checklist, identity,
VS series, currency, organizers, disciplines, extra items, discounts, team, danger
zone — in a single 1884-line component. An organizer looking for the exchange rate
scrolls past the discipline table; one adding an extra item scrolls past everything
above it. Now that the preview pane occupies the right half of the workspace, the
settings column is narrower and the scroll is longer still. Nothing about the page
tells the organizer how much configuration exists or where a given setting lives.

Saving is worse than merely long, it is inconsistent. Identity, organizers, VS series,
currency and discounts each have their own bottom save button. Disciplines and extra
items have none: their rows save one at a time through a check icon that appears
inside the row, while adding and deleting a row writes to the server the instant it is
clicked. And the same `.param-save` button style is used for things that save nothing
— "recalculate missing" sits at the bottom of the discipline and extra-item tables
looking exactly like a save button, and the discount section stacks three identical
buttons of which only the last one writes. An organizer cannot tell what saves what.

The preview pane already solved the navigation half of this with tabs. Setup should
read the same way, and each tab should have exactly one thing that writes.

## What Changes

### Navigation

- The Setup settings pane gains a **tab bar with five tabs**: `TOURNAMENT`,
  `DISCIPLINES`, `EXTRA`, `PAYMENTS`, `OTHER`. One tab is shown at a time;
  `TOURNAMENT` is selected on entry.
- Sections are allocated to tabs without being rewritten:
  - **TOURNAMENT** — identity (name, subtitle, description, date, location, language,
    registration window, logo, qualification) and titular organizers.
  - **DISCIPLINES** — the discipline table.
  - **EXTRA** — the extra-items table.
  - **PAYMENTS** — currency and exchange rate, VS series, discounts.
  - **OTHER** — team access and the danger zone, both owner-only as today.
- The **completeness checklist stays above the tab bar**, visible on every tab, and
  each tab whose sections hold something still unconfigured carries a **marker** in
  the tab bar.
- **All tabs stay mounted**; the inactive ones are hidden, so unsaved work survives a
  tab switch.
- The **preview pane stays beside every tab**, unchanged.

### Saving

- Each editing tab gets **exactly one save control**, at the bottom of the tab, and it
  is the **only thing in that tab that writes to the server**. It states how many
  unsaved changes it will write and is inert when there are none.
- **Row tables become drafts.** Adding a discipline or extra item adds a local row;
  editing a row edits a local draft; deleting a row removes it from the local list.
  Nothing reaches the server until the tab is saved. The per-row check icon disappears.
- Saving a tab **fans out** to the endpoints that already exist — per-row create,
  update and delete for the tables, whole-object patch for the field sections — in a
  defined order. The tournament detail is refetched **once**, after the flush.
- The flush is **not atomic**, and the interface says so rather than pretending
  otherwise: if one row is rejected, the changes already written stay written, the
  rejected row stays dirty and marked with its error, and the save control reports what
  is left unwritten. No backend batch endpoint is introduced by this change.
- The **price-change warning** moves from the row to the tab save: it is raised once,
  before flushing, when the pending changes touch a price and the tournament already
  has registrations.
- **Only saves look like saves.** "Recalculate missing" and "add discount" become
  tertiary underlined-text actions per the design system's button hierarchy, so the
  filled/outlined save control is unambiguous.
- Two things stay immediate by nature and are stated as exceptions rather than hidden:
  **logo upload and removal** on the `TOURNAMENT` tab (they act on file choice), and
  everything on the **`OTHER` tab** — inviting or removing a team member, cancelling
  or deleting the tournament — which are actions, not settings, and keep their own
  controls and confirmations. `OTHER` therefore has no save control.
- Leaving the Setup phase for another console phase with unsaved changes **asks for
  confirmation**, because a whole tab of drafted rows can now be lost in one click.

No section's fields, validation rules, or persisted result change. No backend, API, or
data change; `setup_missing` keeps returning the same keys, now additionally mapped to
tabs on the client.

Non-goals: no re-grouping of fields between sections; no new settings; no batch or
transactional endpoint; no tabs outside the Setup phase; no move of the
payment-lifecycle parameters (reservation validity, reminder day, tolerance,
refundable-until, bank account, expiry grace, amendments-close) out of the Payments
phase rail.

## Capabilities

### New Capabilities

- `setup-navigation`: How the Setup phase's settings are navigated and committed — the
  five tabs and which sections belong to each, the default and persistence of the
  selection, the checklist's placement and per-tab incompleteness marker, the
  preservation of unsaved edits across tab switches, the one-save-per-tab rule with
  its drafted row tables, the non-atomic flush and its error reporting, the stated
  immediate-action exceptions, and the confirmation on leaving Setup dirty.

### Modified Capabilities

- `setup-preview`: the `Setup phase shows settings and preview side by side`
  requirement states the settings pane "SHALL keep its existing content, order, and
  editing behavior unchanged". Both its navigation and its commit behavior are now
  governed by `setup-navigation`. The `Preview reflects saved settings and refreshes on
  save` requirement is also restated: the preview still never shows unsaved edits, and
  the refresh trigger is now the tab save rather than a section save.

`etl-console` and `tournament-admin` are deliberately **not** modified.
`tournament-admin` requires disciplines and organizers to be "editable in the console
Setup phase … as row tables with add and remove", which drafted rows still satisfy —
it says nothing about when a row reaches the server. `etl-console`'s Setup-tab
requirement says the phase presents the tournament configuration and the completeness
checklist instead of a fencer table, which stays true.

## Impact

Frontend only.

- `frontend/src/SetupPanel.tsx` — the default export becomes a tab shell with a save
  bar per tab; the section components keep their fields and validation but hand their
  save function and dirty count to the shell instead of rendering their own save
  button. The two row tables change most: their add, edit and delete handlers move from
  API calls to draft mutations, and their save computes the diff against `detail`.
- `frontend/src/index.css` — a `.setup-tabs` bar reusing the `.stage-control`
  treatment, `.setup-tabpanel[hidden]`, the tab marker, a `.setup-save-bar`, and the
  demotion of `.param-save` on non-saving buttons to the tertiary text style.
- `frontend/src/Console.tsx` — accepts a dirty signal from `SetupPanel` and confirms
  before leaving the Setup phase with unsaved changes.
- `frontend/src/i18n/cs.json`, `en.json` — five tab labels, the marker's accessible
  label, the save control's count and its unwritten-changes report, the row error
  marker, and the leave-Setup confirmation.
- No change to `SetupPreview.tsx`, `ParamPanel.tsx`, any endpoint, or the database.
