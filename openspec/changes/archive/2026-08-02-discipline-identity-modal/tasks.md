## 0. Sequencing and ground rules

- [x] 0.1 Applies on top of `split-discipline-identity` (archived). Both deltas are written
      against the specs as that change left them; re-base if `openspec/specs/tournament-admin`
      or `openspec/specs/discipline-identity` moves before this is applied
- [x] 0.2 The dialog owns identity (kind, material, weapon, gender, name, slug) and nothing
      else; the row owns capacity, prices, and the optional fields. Keep the boundary at the
      freeze line (design D1) — a field that is not frozen with the others does not belong
      in the dialog
- [x] 0.3 No stored slug is rewritten by anything in this change (design D5). If a step
      seems to require regenerating existing slugs, it is the wrong step. The pre-split
      slugs that carry a space are migrated later, by `add-field-validation` section 8a,
      when the slug gains a pattern — not here

## 1. Taxonomy: slug normalization and a kind-aware name

- [x] 1.1 In `backend/app/taxonomy.py`, add `normalize_slug(value: str) -> str`: fold
      diacritics to ASCII, collapse every run of characters outside `[A-Za-z0-9-]` to a
      single `-`, strip leading and trailing `-`. Preserve case (design D4 — this is the
      change's one open decision; if it flips to case-folding, only this function and the
      generation scenarios change)
- [x] 1.2 Unit-test `normalize_slug` against the spec's cases: `Tešák` → `Tesak`,
      `Sword & Buckler (variant)` → `Sword-Buckler-variant`, `LS` → `LS`, `Team-LS`
      unchanged, `LS-A` unchanged. Include an input that normalizes to the empty string
      and decide there what happens (fall back to the generated slug, not an empty one)
- [x] 1.3 Add a kind-aware generated name — `taxonomy_name` keeps its signature for the
      classification part, and the team marker is composed on top of it, so the existing
      30-entry table stays the one definition of a classification's name
- [x] 1.4 Test that an individual and a team discipline classified alike generate different
      names (spec: "Team discipline name states its kind")

## 2. Backend: slug generation learns about kind

- [x] 2.1 In `routers/tournaments.py`, give `generate_slug` the discipline's kind and prefix
      the base with `Team-` for a team discipline, before the `-2`/`-3` collision counter
      runs. Update both call sites
- [x] 2.2 Run the generated base through `normalize_slug`, so a custom weapon cannot produce
      an unencodable slug
- [x] 2.3 In `add_discipline`, normalize an organizer-supplied slug before the uniqueness
      check, so that two overrides differing only in punctuation collide rather than both
      being accepted
- [x] 2.4 Same in `update_discipline`, and confirm `slug_changed` is computed against the
      *normalized* incoming value — otherwise an override that normalizes to its current
      slug is treated as a change and refused on a frozen discipline
- [x] 2.5 Test: `LS` then `Team-LS` for individual-then-team longsword; `LS-2` for a second
      individual; `Team-LS-2` for a second team; and that an existing tournament whose team
      discipline is `LS-2` is left exactly as it is

## 3. Backend: report the frozen state

- [x] 3.1 Add `identity_frozen: bool` to `DisciplineOut` in `schemas.py`
- [x] 3.2 Compute it from the same predicate as the freeze — `_discipline_referenced` — and
      **not** from `availability.taken_seats`, which asserts individual kind, counts only
      paid and unexpired-reserved entries, excludes substitutes, and ignores teams entirely
      (design D6)
- [x] 3.3 Compute it for a whole tournament in one pair of grouped queries rather than
      calling `_discipline_referenced` per row, so serializing the detail does not become
      2N queries
- [x] 3.4 Populate it wherever `DisciplineOut` is built; check every construction site, not
      just the Setup one
- [x] 3.5 Test: unreferenced → false; one cancelled entry → true (the case `taken` gets
      wrong); a substitute entry → true; a team entry on a team discipline → true
- [x] 3.6 Test that renaming a discipline whose identity is frozen still succeeds — the flag
      covers slug, classification and kind, never the name

## 4. Frontend: the derivation port

- [x] 4.1 Port `taxonomy_code` and the generated-name composition into the frontend, beside
      the existing `LEGACY_WEAPONS` table, keeping one module as the single place the
      duplication lives (design D3)
- [x] 4.2 Port `normalize_slug` alongside it
- [x] 4.3 Test the port against the same case table as tasks 1.2 and 2.5, stated in the same
      order, so a drift between the two implementations shows up as a failing pair

## 5. Frontend: the discipline dialog

- [x] 5.1 New dialog component using the existing `.modal-backdrop` / `.modal` /
      `.modal-actions` structure (`index.css:987-1100`, as `MatchDialog.tsx` uses it), so it
      inherits the double-frame framing `design-system` fixes
- [x] 5.2 Fields in order: kind, material, weapon, gender, then a rule, then name and slug.
      Defaults individual / steel / open. Labels above controls per `design-system` form
      conventions. Selects for the closed sets unless the radio question in design's Open
      Questions is settled first
- [x] 5.3 Weapon offers the five taxonomy weapons plus the "other" free-text path the row
      has today, carried over unchanged
- [x] 5.4 Prefill name and slug from the fields above, with an independent touched-flag per
      field: derive until the organizer types there, then leave that field alone while the
      other keeps deriving (design D3)
- [x] 5.5 Slug field carries the existing help hint text; keep the i18n key rather than
      writing a second one
- [x] 5.6 Duplicate-name warning: compare trimmed and case-insensitively against every other
      row in the table, drafted rows included, excluding the row being edited. Warn below
      the field in `--stamp` per the form conventions; do not block confirm
- [x] 5.7 Confirm validates locally what the server would refuse — slug uniqueness within the
      tournament, and name required for a weapon outside the taxonomy — and reports it in
      the dialog rather than deferring to the tab save (design D2)
- [x] 5.8 Confirm mutates the draft row only. No `addDiscipline` or `updateDiscipline` call
      from the dialog; the tab's save control stays the only writer
      (`setup-navigation`: "Row tables are drafts until the tab is saved")
- [x] 5.9 Cancel changes nothing, including for a dialog opened on an existing row
- [x] 5.10 Add the Czech and English strings for every new label, hint, and warning

## 6. Frontend: the row loses its identity controls

- [x] 6.1 Add `originalSlug` to `DisciplineRow`, set from the server value in
      `disciplineToRow` and never changed by editing (design D7)
- [x] 6.2 `disciplineRowDirty` (`SetupPanel.tsx:774`) resolves the original by
      `originalSlug`, and compares `slug` as one of the fields it checks — today it compares
      neither, so a slug edit reads as "not dirty" and is silently dropped
- [x] 6.3 `disciplineRowTouchesPrice` (`:819`) resolves by `originalSlug` too
- [x] 6.4 `api.updateDiscipline` (`:995`) takes `originalSlug` as the path segment and sends
      the new slug in the body
- [x] 6.5 Replace the weapon/gender/material cell, and the name, slug and kind cells, with
      two text cells: name, then slug in faded ink. Table goes from eight columns to six
      (five without EUR); update the `colSpan` on the detail subrow, which is currently
      hard-coded to `eur ? 8 : 7`
- [x] 6.6 Add the reopen control to `col-actions` beside the delete action, from the same
      outline icon set at 1.5px stroke. Render it only when `identity_frozen` is false; a
      frozen row shows delete alone
- [x] 6.7 "+ add discipline" opens the dialog instead of appending a blank row; a row exists
      only once the dialog is confirmed
- [x] 6.8 Confirm the row's own validation still marks an invalid drafted row and blocks the
      save, per `setup-navigation` — the fields it validates have moved but the rule has not
- [x] 6.9 Check the price-change warning still fires: `disciplineRowTouchesPrice` must keep
      returning true for a row added through the dialog

## 7. Verification

- [x] 7.1 Backend tests green, including the existing `test_team_disciplines.py` and the
      discipline-identity tests inherited from the previous change
- [x] 7.2 Frontend typecheck and build green
- [x] 7.3 Walk the console: add an individual longsword and a team longsword; confirm the
      slugs read `LS` and `Team-LS`, the names differ, and the table shows no greyed control
      anywhere
- [x] 7.4 Walk the freeze: reopen an unreferenced discipline and change its weapon and slug,
      save, confirm both landed; register a fencer into it; confirm the reopen control is
      gone from that row and still present on the others
- [x] 7.5 Walk the drop-guard from 6.2 explicitly — change only the slug, and confirm the
      save counter registers one pending change and the server receives it
- [x] 7.6 Confirm a tournament created before this change is untouched: same slugs, same
      names, no row newly frozen or newly editable
- [x] 7.7 Re-read `CLAUDE.md`'s prohibitions against the dialog: no shadow, no radius above
      2px, no emoji or filled icons, no second saturated color, no hex outside `tokens.css`
- [x] 7.8 `openspec validate discipline-identity-modal --strict`
