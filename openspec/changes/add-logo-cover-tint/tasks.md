## 1. Backend

- [x] 1.1 `logo_hue_band(image) -> Literal["blue","green","warm"] | None` in its own module, per design D2
- [x] 1.2 Tests with synthetic images: green shield on transparent → green, red on white → warm, blue → blue, black on white → None, mostly-white with a small colored mark under 10% → None
- [x] 1.3 `Tournament.logo_tint` column; Alembic migration adding it and backfilling from stored `logo_bytes`
- [x] 1.4 Upload sets it from the re-encoded image; delete clears it; test both through the API
- [x] 1.5 `OpenTournamentOut.logo_tint`; scoped pytest, ruff, basedpyright

## 2. Frontend

- [x] 2.1 `logo_tint` on `OpenTournament`
- [x] 2.2 `TournamentCard`: cover tint = band (`warm` → `yellow`) else slug fallback; `data-tint` as `blue|green|yellow`; rename the selectors in `index.css`
- [x] 2.3 Tests: band wins over slug, null band falls back to the slug tint; update the existing tint-determinism test
- [x] 2.4 `npm run typecheck`, `npm run check`, `npm test`

## 3. Specs on archive

- [ ] 3.1 When syncing, adjust the `fencer-home` landing text ("chosen deterministically from the tournament's slug") to point at `A card's cover tint follows its logo`
