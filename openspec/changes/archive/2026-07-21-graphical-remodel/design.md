## Context

`frontend/src/index.css` (961 lines) and all 19 `.tsx` components currently use ad hoc hex colors, system fonts, rounded corners, and shadows — none of it derived from any token file. `squire-design-spec.md` is now ratified as the binding visual spec and prescribes its own rollout order (section 9): generate tokens, build one canonical reference screen, then derive everything else from it. There is no CSS-in-JS, no CSS modules, and no component library in the frontend — one global stylesheet (`index.css`) plus plain className styling. There is no frontend test runner or visual regression tooling (`package.json` has only `tsc`/`vite`); verification is manual, in-browser.

## Goals / Non-Goals

**Goals:**
- Implement every token, component rule, and prohibition in `squire-design-spec.md` across all current screens.
- Establish `TournamentDetail.tsx` as the canonical reference screen per spec section 9, then derive every other screen from its patterns rather than re-deriving styling ad hoc per screen.
- Leave `CLAUDE.md` carrying section 8 so future sessions inherit the prohibitions automatically.

**Non-Goals:**
- No behavioral, API, data-model, or business-rule changes — this is presentation-layer only.
- No dark mode (explicitly out of scope per spec section 2).
- No backend email template changes — `emails.py`/`mail.py` are plain text with no visual styling to remodel.
- No introduction of CSS modules, styled-components, or a component library — stay inside the existing global-stylesheet architecture since this change doesn't need new tooling to satisfy the spec.
- No automated visual regression tooling added in this change; verification stays manual (dev server + browser), consistent with the project's current test setup.

## Decisions

**Reference screen = `Console.tsx`.** The spec mandates "the tournament registration table (document header, ledger, footer, stamps)" by name (section 9). `Console.tsx` is the organizer's ETL console — top stepper, full-width `sheet-table`, right operations rail, phase-dependent columns, and the "Registered: N · paid: M" footer stat — which is the actual ledger the spec describes. `TournamentDetail.tsx` (App.tsx's fencer-facing single-registration page: info, disciplines, one registration form, payment slip, no table of rows) is a different screen entirely and is migrated later, alongside the other fencer-facing screens. `Console.tsx` is rebuilt first and iterated screenshot-by-screenshot until it matches the spec exactly; every other screen borrows its table, tag, stamp, and button patterns from this file rather than re-interpreting the spec independently.

**Single `tokens.css`, loaded once.** Plain CSS custom properties in a new `frontend/src/tokens.css`, imported before `index.css` in `main.tsx`. No CSS-in-JS or preprocessor — the spec's token block is already valid CSS, and the app has no build-time CSS pipeline beyond Vite's default.

**Fonts via Google Fonts `<link>` in `index.html`.** Matches the spec's explicit instruction ("Load from Google Fonts, subsets `latin,latin-ext`"). Self-hosting would add build complexity the spec doesn't ask for.

**Icons via `@tabler/icons-react`.** Chosen over hand-copied SVGs so icon usage stays sparse and consistent (spec section 5: single outline set, 1.5px stroke, 16–18px) without maintaining SVG files by hand. Tree-shakeable, so the "use sparingly" constraint doesn't cost bundle size for unused icons.

**Rollout order inside this change:**
1. `tokens.css` + font loading + `CLAUDE.md` section 8.
2. Reference screen: `Console.tsx` (stepper, ledger table, footer, stamps/badges, rail).
3. Rest of the ETL console (`ImportPanel.tsx`, `ParamPanel.tsx`, `DedupPanel.tsx`, `ExportPanel.tsx`, `MatchPanel.tsx`, `MatchDialog.tsx`, `SetupPanel.tsx`) — same organizer surface, direct reuse of the reference screen's table/rail/form patterns.
4. Fencer-facing screens: `Login.tsx`, `TournamentPicker.tsx`, `FencerHome.tsx`, `TournamentDetail.tsx` (registration form, payment slip — reuses the reference screen's stamp/payment-slip patterns), `ProfilePage.tsx`, `HRSearch.tsx`.
5. Admin/setup: `AdminPanel.tsx`, `SetupPanel.tsx`.
6. Shared components embedded in already-migrated screens, restyled last since their containers now set the pattern: `AccountMenu.tsx`, `PleaSection.tsx`, `EditableCell.tsx`.
7. Final pass: delete dead CSS from the old `index.css`, grep for stray literal hex values and non-token colors, confirm the wink-budget count (max one per screen).

**Deterministic stamp rotation** is a small pure function (hash the registration ID string, map to a −2°..+2° range) — no new dependency, lives next to the stamp component.

**Wink-budget enforcement is manual**, checked screen-by-screen during implementation against spec section 7's list; not worth automated tooling for four fixed touches.

## Risks / Trade-offs

- [Large diff touching all 19 components risks functional regressions hiding inside CSS/markup changes] → Keep edits markup/CSS-only, no logic changes; smoke-test each screen in the dev server after migrating it, not just at the end.
- [`--ink-faded` on `--paper` is borderline WCAG AA per spec section 6] → Restrict its use to 11px+ metadata/labels exactly as the spec requires; never use it for primary content or body text.
- [No frontend test runner to catch regressions automatically] → Manual pass through every screen's golden path (per screen) after its migration step, as called for by the project's own review conventions.
- [Reference-screen-first approach risks drift if later screens are migrated before the reference screen is "declared canonical"] → Don't start screen 3+ migrations until `TournamentDetail.tsx` is confirmed against the spec and treated as frozen.

## Migration Plan

Frontend-only, no data or schema migration. Ships as a normal frontend build/deploy. Rollback is a plain revert — no persisted state, API contract, or backend behavior is touched, so reverting the frontend commit(s) fully undoes the change.

## Open Questions

None blocking. Dark mode is explicitly deferred by the spec itself (section 2) and not reconsidered here.
