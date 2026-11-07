## Why

Squire states a nationality as its two-letter ISO code wherever a HEMA Ratings
profile's value is shown — the Matching evidence register, every phase after it,
the Export tables, the printed roster (`etl-console`, `export-tables`) — for one
stated reason: a reader comparing "PL" against "Poland" is reading a difference
that is not there.

A team's roster members are the exception, and not by decision. A member bound
through the HR search is stored with the index's own English country name
("Czech Republic", "United States"), because the roster save keeps what the
client sent and the client echoes the search result verbatim. So the Teams tab,
the organizer's teams view and the public team roster print whole country names
in a column that reads as codes everywhere else in the application, three
columns to the left of a fencer table that reads `CZ`.

## What Changes

- A roster member's nationality SHALL be held as the two-letter ISO code of the
  country it names, whatever vocabulary its source spelled it in — the same
  reading `etl-console` fixes for the identity columns.
- Where no country can be identified from the spelling, the source's own words
  SHALL stand, as they do in the evidence register: a spelling Squire cannot
  read is still what it was given.
- The reading is applied where a member is written — the roster save — so that
  every surface that lists members gets it without restating it, present ones
  and future ones alike.
- The canonical JSON export keeps stating what the record holds, as it does for
  every other field. A restore applies the reading like any other write, so that
  a document written before this change does not land the only rows in the
  database that disagree with it.
- Existing member rows are converted by the migration that introduces the rule.

## Capabilities

### New Capabilities

<!-- none -->

### Modified Capabilities

- `team-disciplines`: binding a member takes the profile's nationality as its
  ISO code rather than in the index's own spelling.

## Impact

- `backend/app/routers/registrations.py` (`update_roster`) and the restore in
  `backend/app/export_json.py` — the two places a roster member row is written.
- `backend/alembic/` — one data migration over `team_members.nationality`.
- `backend/tests/test_teams*.py` and the entrants roster tests — assertions
  spelling a country out.
- No frontend change: the dialog keeps sending what the search returned
  (`frontend/src/RosterMemberDialog.tsx`), and the server is where an input is
  read. No change to the HR index, which keeps the index's own spelling —
  `hr_index.country_code` already converts, and the nationality filter on the
  search still works in the index's vocabulary.
