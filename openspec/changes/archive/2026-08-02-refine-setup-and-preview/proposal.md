## Why

The tabbed Setup phase and its side-by-side preview are in place, and using them
surfaced a list of small defects and rough edges: a slug generator that stutters the
year, a settings field the organizer should never touch, a header that scrolled
content bleeds through, inconsistent price column labels, preview tabs stretched to
the full pane, and a registration form whose optional-answer block reads as a set of
leftover fields dangling under the total. None of these is structural; together they
are what stands between the Setup phase and being presentable.

## What Changes

**Tournament creation**

- The derived slug appends the event year only when the slugified name does not
  already carry one. `My Tournament 2027` derives `my-tournament-2027`, not
  `my-tournament-2027-2026`.

**Setup — TOURNAMENT tab**

- Fields are reordered: display name, subtitle, logo, date, location, description,
  qualification, registration opens, registration closes, registration instructions.
  The qualification statement therefore moves from between the registration dates and
  the logo to between the description and the registration dates.
- The communication-language field is removed from Setup. The tournament keeps a
  stored communication language, assigned at creation and used for fencer emails as
  before; it is simply no longer organizer-editable. **BREAKING** for the organizer's
  ability to change it after creation.
- Logo upload becomes a tertiary underlined text action, matching "add organizer",
  instead of a button.

**Setup — PAYMENTS tab**

- The VS series becomes read-only. It stays automatically assigned at creation as the
  lowest free value for its year, and Setup shows it and the resulting variable-symbol
  prefix as a statement of fact. **BREAKING**: the organizer can no longer change the
  series before the first registration, and the collision and frozen-series rejections
  that only that editor could provoke stop being reachable.

**Setup — all tabs**

- The checklist and tab bar stop being overlappable: scrolled section content is never
  visible above or through them.
- Every price column across disciplines, extra items and discounts is labelled "unit
  price" in both currencies, replacing today's mix of "fee" and "price".

**Preview**

- The preview's face/form tab bar is sized to its labels rather than stretched across
  the pane, matching the settings tab bar.
- The optional when/where/ruleset line under a discipline or action loses its leading
  dash.
- On the registration form, generous vertical space is set before the registration
  instructions and before the total, and the total is aligned to the right, over the
  price column it sums.
- The non-billable block below the total loses the post-tournament sparring checkbox
  and the accommodation note. The free-text remarks field stays — it is the fencer's
  only channel to the organizer — and is relabelled "Note" in English. The registration
  API continues to accept after-sparring and accommodation, which the table-import path
  still parses from legacy sources; only the form stops offering them. **BREAKING** for
  fencers registering in-app, who can no longer declare either.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `tournament-admin`: slug derivation skips a year already present in the name; the
  TOURNAMENT tab's field order changes and the qualification statement's stated
  position moves with it; the communication language leaves the editable set; the VS
  series becomes read-only; price columns are labelled "unit price"; the logo control
  is a tertiary text action.
- `setup-navigation`: the checklist and tab bar are never overlapped by scrolled
  content; the section allocation no longer names the communication language; the
  controls exempt from the tab's save control are stated to be tertiary text actions.
- `setup-preview`: the preview tab bar is sized to its content.
- `registration`: the form's spacing and total alignment are fixed; the non-billable
  fields offered by the form reduce to the remarks note.
- `fencer-home`: the information screen's optional detail line carries no leading dash;
  the Register screen's non-billable fields reduce to the note.
- `localization`: the tournament's communication language is fixed at creation and not
  exposed for editing.

## Impact

- `frontend/src/TournamentPicker.tsx` — `deriveSlug`.
- `frontend/src/SetupPanel.tsx` — `IDENTITY_FIELDS` order, qualification and logo
  placement, logo control markup, `VsSeriesSection`, discipline/extra/discount column
  headers, the panel's header/body/footer structure.
- `frontend/src/SetupPreview.tsx` — tab bar class.
- `frontend/src/TournamentFace.tsx` — `DisciplinesInfo` / `OtherActionsInfo` detail
  line, `RegistrationForm` spacing, total, and "other" block.
- `frontend/src/index.css` — `.setup-panel*`, `.stage-control`, `.detail-extra`,
  `.form-total`, `.register-section`.
- `frontend/src/i18n/{cs,en}.json` — unit-price labels, note label, removed keys.
- Backend: none. `vs_series` stays writable at the API level (the PATCH path keeps its
  guards); `language`, `aftersparring` and `accommodation` stay on the model and in the
  schemas, since the import and email paths depend on them.
