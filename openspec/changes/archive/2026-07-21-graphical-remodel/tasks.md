## 1. Foundation

- [x] 1.1 Create `frontend/src/tokens.css` with the full token set from spec section 2 (paper/ink/rule/stamp/pastel colors, font stack, geometry).
- [x] 1.2 Add IBM Plex Sans/Mono/Serif Google Fonts `<link>` to `frontend/index.html` (subsets `latin,latin-ext`).
- [x] 1.3 Import `tokens.css` before `index.css` in `frontend/src/main.tsx`.
- [x] 1.4 Add `@tabler/icons-react` to `frontend/package.json`.
- [x] 1.5 Append spec section 8 (Prohibitions) to the repo's `CLAUDE.md`.

## 2. Reference screen — tournament registration table

- [x] 2.1 Rebuild `Console.tsx` document header (topbar/tournament name in serif H1 per spec sections 3–4) and stepper (phase nav).
- [x] 2.2 Rebuild the `sheet-table` ledger: hairline row rules, 2px header underline, no zebra stripes, hover = `--paper-shade` only, ordinal first column (`#`) in `--font-data`.
- [x] 2.3 Implement the deterministic "Paid" stamp rotation function (hash registration/row ID → −2°..+2°) and apply it to the state badge for paid rows.
- [x] 2.4 Implement category tags and any plain-text "pending — VS …" treatment (no badge) for unpaid rows shown in the ledger.
- [x] 2.5 Restyle the operations rail (right sidebar: phase params, manual edits list) per form/card conventions.
- [x] 2.6 Rebuild the table footer/stats line ("Registered: N · paid: M") and add the "File maintained in good order." wink + revision number where applicable.
- [x] 2.7 Restyle this screen's buttons per the primary/secondary/tertiary hierarchy (max one primary) and replace the raw `~`/`✓`/`✗`/`↺`/`✕`/`↻` glyphs with text labels or Tabler icons.
- [x] 2.8 Manually verify in the dev server against every rule in spec sections 2–8; iterate until it matches exactly. Declare this screen canonical before continuing.

## 3. Rest of the ETL console

- [x] 3.1 Restyle `ImportPanel.tsx` and `ParamPanel.tsx` (forms: Roman-numeral sections, bottom-rule inputs, error message style). (Already conformed via shared `rail-card`/`param-field` classes; no markup changes needed.)
- [x] 3.2 Restyle `DedupPanel.tsx` and `MatchPanel.tsx` / `MatchDialog.tsx` (tables and modal double-frame treatment). (Already conformed via shared classes; removed a stray `✗` glyph from match.notFound copy.)
- [x] 3.3 Restyle `ExportPanel.tsx`. (Already conformed via shared classes; no markup changes needed.)
- [x] 3.4 Restyle `SetupPanel.tsx` (the console's Setup phase tab). Replaced raw ✕/✓/+ glyphs with Tabler icons, made the danger-zone confirm button primary.
- [x] 3.5 Replace loading indicators across the console with plain text ("Leafing through the file…" / three dots) — no skeleton shimmer or spinners. (Already text-only via `t("common.loading")`; no shimmer/spinner existed.)
- [x] 3.6 Smoke-test the full ETL flow (setup → load → parsing → matching → dedup → payments → export) in the dev server for visual and functional regressions.

## 4. Fencer-facing screens

- [x] 4.1 Restyle `Login.tsx` (login + signup forms) per form conventions; apply the account-creation tiskopis number (form no. 1).
- [x] 4.2 Restyle `TournamentPicker.tsx`; apply the tournament-creation tiskopis number where relevant (form no. 2). Also fixed the modal's unstyled submit button (now `btn-primary`).
- [x] 4.3 Restyle `FencerHome.tsx` tabs/history/detail views using the reference screen's table and tag conventions. (Already conformed via shared classes.)
- [x] 4.4 Restyle `TournamentDetail.tsx` (info header, disciplines/extras, registration form, payment panel, registration summary/cancel) reusing the reference screen's stamp, tag, and payment-slip patterns; apply the registration form's tiskopis number (form no. 3). Registration state now uses `PaidStamp`/tag system instead of a plain chip; payment block restructured as `.payment-slip`.
- [x] 4.5 Restyle `ProfilePage.tsx`. Fixed unstyled HR-bind confirm button (now `btn-primary`), role chip upgraded to `tag-file-blue`.
- [x] 4.6 Restyle `HRSearch.tsx` (search form + results table). (Already conformed via shared classes.)
- [x] 4.7 Add/verify empty-state microcopy ("The file is empty. For now." / cs equivalent) on any screen with a legitimately empty list, respecting the one-wink-per-screen budget. Applied to FencerHome's three empty-tab states (only one visible at a time).
- [x] 4.8 Smoke-test fencer signup → registration → payment path in the dev server.

## 5. Admin

- [x] 5.1 Restyle `AdminPanel.tsx`. Replaced raw ⤬/✓/✕ glyphs with Tabler icons, owner/shared-HR markers upgraded to the tag system.
- [x] 5.2 Smoke-test admin flows in the dev server.

## 6. Shared components

- [x] 6.1 Restyle `AccountMenu.tsx`. Replaced the raw "⋯" glyph with a Tabler `IconDots` trigger.
- [x] 6.2 Restyle `PleaSection.tsx`, keeping error/plea copy matter-of-fact (no wink). Fixed unstyled submit button (now `btn-primary`).
- [x] 6.3 Restyle `EditableCell.tsx` to match table cell and input focus conventions. (Already conformed via shared classes.)

## 7. i18n and content

- [x] 7.1 Update `frontend/src/i18n/cs.json` and `en.json` with copy for the four wink-budget touches (empty states, tiskopis titles, footer line).
- [x] 7.2 Verify no other decorative/flavor copy was introduced outside the wink budget.

## 8. Cleanup and audit

- [x] 8.1 Remove now-dead rules from `frontend/src/index.css`; confirm every remaining rule references `tokens.css` variables. (Full rewrite against tokens; no literal colors remain.)
- [x] 8.2 Grep the frontend for literal hex values outside `tokens.css` and eliminate any found. (None found.)
- [x] 8.3 Grep for `border-radius` values greater than 2px, `box-shadow`, `text-shadow`, `blur`, and gradients; eliminate any found. (None found.)
- [x] 8.4 Verify focus outlines, 120ms transition limits, and `prefers-reduced-motion` handling are present app-wide. (Global `:focus-visible`, 120ms transitions, reduced-motion media query in place.)
- [x] 8.5 Walk every screen once more counting wink-budget touches (max one each) and confirming none appear on error/payment paths. (Console footer, signup/tournament-creation/registration tiskopis numbers, FencerHome empty states — one each, none on error/payment copy.)
- [x] 8.6 Run `npm run lint` (tsc) and `npm run build` in `frontend/` to confirm no build regressions. (Both clean.)

Follow-up noted but out of this pass's scope: a few pre-existing copy strings across `i18n/en.json`/`cs.json` still use Title Case (e.g. some `setup.*`/`admin.*` labels), which section 8 technically prohibits. Fixing every such string was not enumerated as a task in this change and would require a full bilingual copy pass; flagged for a follow-up change rather than done ad hoc here.
