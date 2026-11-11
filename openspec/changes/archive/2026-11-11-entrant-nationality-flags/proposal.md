## Why

The public entrants roster states each fencer's nationality as a country code. A column
of codes is read one row at a time; a column of flags is read at a glance, and a visitor
scanning who comes from where finds it faster. The owner asked for flags in place of the
codes.

## What Changes

- The Nat. column of the public entrants roster states a recognised country as its flag,
  with the country's name, in the page's language, as the flag's accessible name and
  hover title. This covers an individual's row, a team member's row and a team row
  stating the nationality all its members share.
- A nationality no country can be read from keeps being stated as written, as text.
- The public roster's rows and team members carry the country's ISO 3166 alpha-2 code
  beside the nationality as written, so the client does not have to read countries
  itself.
- The design system's Global prohibitions gain one carve-out by name: a national flag
  stating a nationality on the public entrants roster is a picture of a country, not a
  color of the system. It is exempt from "one saturated color" and "no hex outside
  `tokens.css`", and from nothing else. The copy of the list in `CLAUDE.md` follows.
- A new frontend dependency: `flag-icons` (MIT), its SVG files bundled, never fetched
  from a third party.

Not changed: the organizer console, the Export tables, the data export and the printed
roster (`roster-print`) keep stating the code.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `public-entrants`: the Nat. column states a recognised country as a flag named in the
  page's language; an unrecognised spelling stays text.
- `design-system`: Global prohibitions carve out national flags on the public entrants
  roster from the one-saturated-color and hex rules.

## Impact

- `backend/app/entrants.py`: `EntrantRow` and `TeamMemberRow` gain `country`, read with
  `hr_index.country_code`; the response schema and `frontend/src/api.ts` follow.
- `frontend/src/entrants/`: a `NationalityCell` used by `IndividualRoster` and
  `TeamRoster`.
- `frontend/package.json`: `flag-icons`.
- `openspec/specs/design-system/spec.md`, `CLAUDE.md`: the carve-out.
