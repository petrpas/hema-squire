## Why

On a phone the public entrants roster does not fit. Its columns have fixed widths except
the name, so on a 390px screen the name gets 65px and wraps to three lines ("Hema / Praha /
Šavle"), while HRID and Paid stand out of sight behind a sideways scroll nobody is told
about, and every member of an opened team repeats the club its team row already states.
The name is what a visitor reads the roster for; the club they mostly know already.

## What Changes

- The team roster drops the HRID column, on the team row and on members' rows, at every
  width; the answer stops carrying members' identifiers.
- A member's row states a club only where the team's row states none.
- The Paid header reads "Zapl." on the public roster at every width, "Zap." below 768px;
  English stays "Paid". The roster stops borrowing the Export tables' header for it.
- Below 768px the individual roster's HRID cell is the ↗ link alone, with the identifier
  as its accessible name, under the header "HR".
- The name takes the width and may wrap; the club stays on one line and is cut with an
  ellipsis. Nat. narrows to a flag's width. No column is out of sight on a phone.
- Every team's name starts at the same place whether it can be opened or not; the
  toggle's chevron moves into the gap before the name, centred in it, level with the
  name's first line.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `public-entrants`: individual roster's Paid header; team roster's columns (no HRID) and
  member club; a new requirement that a roster fits a phone.

## Impact

- `backend/app/entrants.py`, `backend/app/schemas.py`: `TeamMemberRow` and its schema
  drop `hr_id`; `frontend/src/api.ts` follows.
- `frontend/src/entrants/TeamRoster.tsx`, `IndividualRoster.tsx`, `rosterCells.tsx`
  (`HrIdCell`), `NationalityCell.tsx`.
- `frontend/src/index.css`: entrants column widths, the 768px rules, ellipsis on club.
- `frontend/src/i18n/{cs,en}.json`: the roster's own Paid and HR headers.
