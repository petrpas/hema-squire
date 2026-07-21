## Why

`squire-design-spec.md` ("Bureau 1952") is now the ratified single source of truth for Squire's visual design, but nothing implements it yet. The current frontend (`frontend/src/index.css` and all `.tsx` components) uses ad hoc hex colors, system fonts, rounded cards, and shadows — none of which match the spec. This change executes the spec's own implementation procedure (section 9): build the token file, establish the canonical reference screen, then derive every other screen from it.

## What Changes

- Add `frontend/src/tokens.css` with the full token set from spec section 2 (paper/ink/rule/stamp/pastel colors, IBM Plex type stack, geometry), plus IBM Plex Sans/Mono/Serif loading from Google Fonts (`latin,latin-ext`).
- Rebuild `Console.tsx` (the organizer's ETL console — top stepper, full-width sheet table, right operations rail) as the canonical reference screen — document header, ledger table, footer, "Paid" stamps, category tags — matching the spec exactly. This is the tournament registration table the spec means. This screen is the pattern every other screen is derived from.
- Add `@tabler/icons-react` (outline set, 1.5px stroke) as a frontend dependency; use icons only where the spec implies one, text labels remain the default (section 5). Replace the raw `~`/`✓`/`✗`/`↺`/`✕`/`↻` glyphs in `Console.tsx`.
- Restyle every remaining screen/component from the reference screen's patterns: the rest of the ETL console (`ImportPanel.tsx`, `ParamPanel.tsx`, `DedupPanel.tsx`, `ExportPanel.tsx`, `MatchPanel.tsx`, `MatchDialog.tsx`, `SetupPanel.tsx`), fencer-facing screens (`Login.tsx` login + signup, `TournamentPicker.tsx`, `FencerHome.tsx`, `TournamentDetail.tsx`, `ProfilePage.tsx`, `HRSearch.tsx`), `AdminPanel.tsx`, and shared components (`AccountMenu.tsx`, `PleaSection.tsx`, `EditableCell.tsx`).
- Rewrite `frontend/src/index.css` against the tokens: remove all literal hex values, `border-radius` > 2px, shadows, gradients, zebra stripes, blue links, skeleton/spinner loading UI, and toast entrance animations.
- Apply the wink budget (section 7) deliberately: keep exactly the four permitted touches (deterministic "Paid" stamp rotation, empty-state microcopy, form numbering as tiskopisy — registration = no. 3, account creation = no. 1, tournament creation = no. 2 — and the document/table footer line + revision number), update `i18n/cs.json` and `i18n/en.json` copy for these, and strip any other decorative flavor text. Winks are excluded from error paths and anything payment-related.
- Append spec section 8 (Prohibitions) to the repo's `CLAUDE.md` so it's enforced in every future session regardless of context.

Out of scope: backend email templates (`backend/app/emails.py`, `mail.py`) — these are plain-text and already carry no visual styling; no behavioral, API, or data-model changes anywhere.

## Capabilities

### New Capabilities
- `design-system`: the Bureau 1952 tokens (`tokens.css`) and component conventions (table/form/button/tag/modal/wink-budget/prohibitions) as enforceable, testable requirements binding on all current and future Squire screens.

### Modified Capabilities
(none — this change is presentational only; no existing capability's behavioral requirements change)

## Impact

- `frontend/src/tokens.css` — new file
- `frontend/index.html` — Google Fonts `<link>` for IBM Plex Sans/Mono/Serif
- `frontend/package.json` — add `@tabler/icons-react`
- `frontend/src/index.css` — rewritten against tokens
- `frontend/src/*.tsx` (all 19 components) — restyled to match the reference screen's conventions
- `frontend/src/i18n/cs.json`, `frontend/src/i18n/en.json` — wink-budget microcopy updates
- `CLAUDE.md` — append section 8 prohibitions
- No backend changes; no API, schema, or business-rule changes