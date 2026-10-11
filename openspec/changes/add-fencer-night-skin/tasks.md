## 1. Binding text

- [x] 1.1 Amend `CLAUDE.md`'s prohibition list: radius and weight bullets replaced with the skin-token carve-outs, plus the line that everything else binds both skins and the night skin is defined in `design-system` (Requirement: Skins) and nowhere else
- [x] 1.2 ~~Amend `openspec/squire-design-spec.md`~~ — the file was removed in 5d8943b; `openspec/specs/design-system` is the only binding text and this change's delta carries the Skins requirement

## 2. Tokens with day values (console must not change)

- [x] 2.1 Add the new role tokens to `:root` in `tokens.css` with day values: `--radius-card/pill/plate/chip` 2px, `--font-display: var(--font-doc)`, `--weight-display: 500`, `--body-size: 14px`, `--hairline-strong: var(--ink)`, `--stamp-on-tint: var(--stamp)`, `--plate`/`--qr-paper: var(--paper-raised)`, `--scrim: rgba(43, 42, 38, 0.35)`
- [x] 2.2 Wire `body` to `--body-size`, document titles to `--font-display`/`--weight-display`, `.modal-backdrop::backdrop` to `--scrim`, the payment slip's QR frame (ground and quiet-zone padding) to `--qr-paper`
- [x] 2.3 Grep `index.css` for `rgba(`, named colors and hex; move any color literal outside `tokens.css` to a token
- [x] 2.4 Screenshot a console phase, the picker and the admin panel before and after; confirm identical

## 3. Night skin

- [x] 3.1 Add the `[data-skin="night"]` block to `tokens.css` with the brief §1.3 values, `color-scheme: dark`, night `--scrim`, and a comment stating the measured contrasts (design D4)
- [x] 3.2 Add IBM Plex Sans Condensed 600/700 to the existing Google Fonts link in `index.html`
- [x] 3.3 Set `data-skin="night"` on `FencerShell`'s root, on a wrapper around `FencerLayout`'s `Login` branch, and on the roots of `ProfilePage` and `NotFound`; night root paints `--paper` at full dynamic height, plus the `html:has([data-skin="night"])` background rule
- [x] 3.4 Audit every public screen in night (list, detail, entrants, register form, payment slip with QR, modals, sign-in, profile, not-found) and fix rules that read a literal or look wrong; confirm the QR is dark-on-light with its quiet zone

## 4. Backend aggregates

- [x] 4.1 Expose the `registration_closes or date` resolution from `setup.py` as one function and use it for `registration_closes_on` (None for `elsewhere`) on `OpenTournamentOut`
- [x] 4.2 Add a club normalizer module (casefold, strip diacritics, collapse whitespace, trim; empty → None)
- [x] 4.3 Compute `entrant_count` and `club_count` for all tournaments of a list response in one grouped query, reusing the public roster's seated/listed predicates; wire into `/open`, `/held` and the mine list
- [x] 4.4 Tests: a fencer in two disciplines counts once, queued and cancelled do not count, clubs differing in case/diacritics/whitespace count once, `registration_closes_on` equals the detail's close; run `pytest tests/<scope> -q --maxfail=3 --tb=short --show-capture=no`
- [x] 4.5 Add the three fields to `OpenTournament` in `api.ts`

## 5. Card building blocks

- [x] 5.1 Lift the hash out of `PaidStamp.tsx` into `slugHash`; `stampRotation` calls it
- [x] 5.2 `monogram.ts` with tests for the spec's scenarios (two words, one word, function words, digits only, never empty, ≤3 chars)
- [x] 5.3 `CapacityMeter.tsx`: text figure + `aria-hidden` 4px track, full state in `--stamp` with `plno · +N čeká` / `full · +N waiting` (plural forms), no transition; test full state and `aria-hidden`
- [x] 5.4 `StatusBlock.tsx` carrying `StatusChip`/`BondBadge` logic as the three-line block; test each status, absent lines omitted

## 6. Home page

- [x] 6.1 Split `TournamentCard.tsx` out of `FencerHome.tsx`: cover with `data-tint`, plate (logo on `--plate` or monogram), ring by status, ordinal, status block, body (name, subtitle, date · city, organizers as text, disciplines with meters), footer counts, Spravovat sibling link, Paid stamp on Mine/Past
- [x] 6.2 Card grid and card CSS: `auto-fill minmax(320px, 1fr)`, gap 20px, max 1240px; hover by `@media (hover: hover)` only, border + ground, 120ms
- [x] 6.3 Tab band as the segmented pill control, same `useTabBand` logic; full-width equal tabs below 480px
- [x] 6.4 Top bar type: title in `--font-display` at `--title-size`; sign-in as a secondary pill with `--hairline-strong` border; account menu trigger rounded through `--radius-pill` (design D10a: no monogram)
- [x] 6.5 `NextOpening.tsx` on `useOpeningMoment`: soonest future opening within 7 days, countdown fixed-width tabular, replaced at the moment via one list refresh; stacked below 480px; tests for hidden beyond 7 days and replacement at the moment
- [x] 6.6 Narrow card row below 480px (56px plate, no cover, status as one line)
- [x] 6.7 i18n keys in `cs.json` and `en.json` together: status lines, `home.nextOpening.*`, meter full text, footer counts with plural forms (`šermíř/šermíři/šermířů`, `klub/kluby/klubů`)
- [x] 6.8 Update `publicHome.test.tsx` where it asserts the old chip markup; add the tint-determinism test
- [x] 6.9 Deferred, not built (optional per design Non-Goals): (Optional, one sitting) "právě otevřeno" row of ringed plates above the tab band on phones

## 7. Finish

- [x] 7.1 Keyboard pass: every card, tab, strip control and button shows `--focus` in night
- [x] 7.2 Reduced motion: hover transition off, countdown still ticks
- [x] 7.3 `npm run typecheck`, `npm run check`, `npm test` from `frontend/`; `uv run ruff check .` and `uv run basedpyright` from `backend/`
