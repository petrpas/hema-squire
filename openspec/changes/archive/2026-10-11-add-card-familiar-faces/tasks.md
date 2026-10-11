## 1. Backend

- [x] 1.1 Resolve the caller's club and nationality: bound `HRFighter` first, account fields as fallback
- [x] 1.2 Batched load of seated, listed entrants for all tournaments of a response, reusing the roster predicate
- [x] 1.3 Selection: club match by normalized club, country fallback, caller excluded, rating order from the latest snapshot else name, top three, total
- [x] 1.4 `familiar` on `OpenTournamentOut`, absent without a credential and when empty; wire into `/open`, `/held` and the mine list
- [x] 1.5 Tests: club beats country, caller excluded, queued excluded, country fallback, no nationality → absent, anonymous → absent, diacritics and case normalize

## 2. Frontend

- [x] 2.1 `familiar` on `OpenTournament` in `api.ts`
- [x] 2.2 `FamiliarFaces` component in the card footer: three 28px faces, 8px overlap, tint by index, 2px `--paper-raised` ring, label as accessible name and title
- [x] 2.3 i18n keys in `cs.json` and `en.json` (club note with plurals, country note)
- [x] 2.4 Test: faces render with labels when present, footer left empty when absent

## 3. Finish

- [x] 3.1 `npm run typecheck`, `npm run check`, `npm test`; `uv run ruff check .`, `uv run basedpyright`, scoped pytest
