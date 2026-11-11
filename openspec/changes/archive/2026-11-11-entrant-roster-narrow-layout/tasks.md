## 1. Server

- [x] 1.1 Remove `hr_id` from `TeamMemberRow` (`backend/app/entrants.py`) and `EntrantTeamMemberOut` (`backend/app/schemas.py`)
- [x] 1.2 A team roster's members carry no `hr_id`, even when bound to a profile (`test_team_disciplines.py`, replacing the settled-identifier test)
- [x] 1.3 `uv run ruff check .` and `uv run basedpyright` pass

## 2. Columns and headers

- [x] 2.1 i18n: `entrants.column.paid` / `paidShort` / `hr` / `hrShort` in `cs.json` and `en.json`
- [x] 2.2 `TeamRoster`: drop the HRID column and `COLUMNS` to 5; Paid header from the new keys; member club empty where the team row states one
- [x] 2.3 `IndividualRoster`: fixed layout with a `colgroup`; HRID and Paid headers as wide/short pairs
- [x] 2.4 `HrIdCell`: number in a span, identifier as the link's `aria-label`
- [x] 2.5 `api.ts`: `EntrantTeamMember` without `hr_id`

## 3. Layout

- [x] 3.1 `index.css`: column widths for both rosters (Nat. at flag width, club share, name the rest); club and text nationality one line with ellipsis
- [x] 3.1a Nat. and Paid cells and headers centred (`col-nat`, `col-paid`) on both rosters
- [x] 3.1b `.entrants-table .col-gutter`: right padding 2px larger, so the position numbers sit 2px further left; the console's gutter unchanged
- [x] 3.2 `@media (max-width: 768px)`: short headers shown, HR number hidden, narrow HR and Paid widths
- [x] 3.3 Team names in one column whether openable or not; the chevron out of the flow, centred in the gap before the name, level with its first line

## 4. Verification

- [x] 4.1 Tests in `entrantsTab.test.tsx`: no identifier on a team roster; member club only where the team row has none; an openable and an unopenable team's names start at the same x; Paid header "Zapl."; the HR link's accessible name states the identifier
- [x] 4.2 Browser at 390px (team and individual rosters): no sideways scroll, all columns visible, club cut, names wrap; and on desktop
- [x] 4.3 `npm run typecheck`, `npm run check`, `npm test`, `npm run build` pass
