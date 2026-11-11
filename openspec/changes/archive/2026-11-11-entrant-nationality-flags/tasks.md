## 1. Server

- [x] 1.1 `backend/app/entrants.py`: add `country: str | None` to `EntrantRow` and `TeamMemberRow`, set with `hr_index.country_code` from the nationality the row states; follow through the response schema
- [x] 1.2 Test in the entrants suite: "CZ", "CZE" and "Czech Republic" all yield `country == "CZ"`, "England" yields "GB", "Bohemia" yields `None` with the nationality unchanged
- [x] 1.3 `uv run ruff check .` and `uv run basedpyright` pass

## 2. Client

- [x] 2.1 Add `flag-icons` to `frontend/package.json`; `frontend/src/api.ts`: `country: string | null` on the entrant row and team member types
- [x] 2.2 `frontend/src/entrants/flags.ts`: the code→URL map via `import.meta.glob` over the 4×3 SVGs with `?url&no-inline`
- [x] 2.3 `frontend/src/entrants/NationalityCell.tsx`: flag `<img>` with the country's name (`Intl.DisplayNames`, page language) as `alt` and `title`; text where `country` is null or has no file
- [x] 2.4 Use it in `IndividualRoster` and `TeamRoster` (team row from the shared nationality's member, member rows from their own)
- [x] 2.5 `.entrant-flag` in `index.css`: 12px high, hairline frame, `var(--radius)`, no shadow, no new hex; `.entrant-flag-mono` with `filter: grayscale(1)`, applied by `NationalityCell` to `RU` only
- [x] 2.6 Tests in `entrantsTab.test.tsx`: a coded row draws a flag named in the page language and no code; a null country states the nationality as text; a team sharing a country draws it on the team row; an RU row's flag carries the greyscale class and a CZ row's does not
- [x] 2.7 `npm run typecheck`, `npm run check`, `npm test`, `npm run build` pass

## 3. Design rules

- [x] 3.1 Carry the carve-out into the "design prohibitions" copy in `CLAUDE.md`
- [x] 3.2 Check in the browser on a roster with a mostly white flag (PL, JP) — public pages are always night, so the night skin is the one that applies — that the hairline frame keeps it readable
