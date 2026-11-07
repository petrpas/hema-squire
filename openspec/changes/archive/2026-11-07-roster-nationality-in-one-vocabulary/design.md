## Context

See proposal.md — Why. The mechanics:

- `hr_index.country_code` already does the reading: `pycountry` lookup over the
  text and over its folded form, then a small alias table, `None` where nothing
  matches. Its callers all spell the same fallback, `country_code(x) or x`
  (`rules.py`, `substitution.py`, `hr_index.evidence_fields`).
- `TeamMember.nationality` has one writer: `update_roster`
  (`routers/registrations.py`), a whole-roster replace taking `RosterMemberIn`
  straight from the client, which echoes back whatever `/api/hr/search`
  returned — the index's own English country name. Where the roster is still
  empty the Teams tab is prefilled from the entering fencer's own record
  (`_team_out`), which holds the index's spelling too; it reaches the rows
  through the same save. The restore in `export_json.py` also constructs
  members, from a dump Squire itself wrote.
- It has four readers: the Teams tab (`_team_out`), the organizer's teams view
  (`routers/tournaments.py`), the public roster (`entrants.TeamMemberRow`) and
  the canonical JSON export, which is also an importer (`export_json.py` reads
  the same field back).

## Goals / Non-Goals

**Goals:**

- One vocabulary in the column, decided in one place.
- No reader has to know about it, including readers not written yet.

**Non-Goals:**

- The fighters index. `HRFighter.nationality` keeps the index's own spelling:
  the search's nationality filter matches on it, and the refresh writes what the
  page says.
- A fencer's own `nationality`. It is converted where it is displayed, by the
  replay that builds the table rows, and that path is not touched here.
- The public roster's columns, the Teams tab's layout, the export's shape.

## Decisions

**D1 — read on write, not on display.** The conversion happens where a member
is written, so the stored row holds the code. Four readers exist and a fifth
will be added by someone who has not read this file; a display-side rule would
have to be restated in each, which is how the column came to disagree with the
fencer table in the first place. The cost is that the index's spelling is not
kept — accepted, because `country_code(x) or x` keeps every spelling it cannot
resolve, which is the only case where the original carries information the code
does not.

Alternative considered: convert in the three display serializers and leave the
rows as given. Rejected for the restatement above, and because the canonical
export reads the same field: a display rule applied there would make the export
differ from the rows it must restore, and applying it everywhere *but* the
export means the rule has an exception on the one path that round-trips.

**D2 — the write path converts, the schema does not.** Not a validator on
`RosterMemberIn`: a field whose value changes as it passes through validation
makes an echo of the submission disagree with what was submitted, and that type
is echoed back by the roster response. The save converts where it builds the
`TeamMember`, one line beside the `club` and `name` it already takes verbatim.

The restore converts too, and for the same reason rather than a different one:
it is a writer of rows, and the migration cannot reach a row that arrives after
it ran. A document written before this change would otherwise restore into the
only member rows in the database that disagree with the column. `data-export`
already settles this direction for an older document's discipline code, which
restores "with its classification parsed from it, which is exactly what the
migration does to stored rows" — the same sentence covers this.

The export stays verbatim, which is not the other half of a contradiction: by
then the rows hold codes, so reporting what the record holds and stating the
code are the same act, and a field that converts on the way out would be a
second reading nobody can see.

**D3 — existing rows are converted by migration, not left to drift.** A data
migration over `team_members.nationality` applying the same reading. Squire is
pre-launch, so this is small by definition; leaving them would mean the column
disagrees with itself, which is worse than either state. The migration converts
only what resolves to a country and leaves the rest, exactly as the write path
does, and needs no down-conversion to reverse — the codes are valid input to
every reader before and after.

**D5 — the migration spells the reading out instead of importing it.** No
revision in `alembic/versions` imports application code, and the reason holds
here: the chain is replayed from the baseline against whatever the application
looks like at that moment, so a revision calling `hr_index.country_code` breaks
every future `upgrade head` the day that function moves. The alias list is
therefore copied, with a comment in both places saying so. The duplication is
bounded — the migration runs once per database and never needs an alias added
after the fact.

## Risks / Trade-offs

- **An alias the lookup misses leaves a country name in the column** →
  `country_code`'s alias table is where that is fixed, for every caller at once;
  the member row stays displayable either way.
- **The code is less legible to a reader than the country name** → It is the
  reading every other identity column in the application already uses; the
  inconsistency is the defect, not the brevity.

## Migration Plan

One Alembic revision, data only, no schema change. Forward: read each
`team_members.nationality`, write the resolved code where one resolves. Rollback:
the revision's down is a no-op — the codes are valid values for the old code
path, which stored whatever it was given.
