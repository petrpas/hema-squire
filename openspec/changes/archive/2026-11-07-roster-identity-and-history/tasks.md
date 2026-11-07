## 1. The member gets an identity that survives a save

- [x] 1.1 Add `removed_at` and `removed_by_fencer_id` to `TeamMember`, filter
  `Team.members` to live members ordered by ordinal, and add
  `Team.removed_members` (design D2). State the filter in the model's docstring.
  Verify `uv run basedpyright` is clean.
- [x] 1.2 Add the `RosterChange` model (design D3) — team, member, kind, field,
  before, after, actor, `by_organizer`, `after_deadline`, `created_at`.
- [x] 1.3 One alembic revision for the two columns and the table; verify
  `uv run alembic upgrade head` then `downgrade -1` then `upgrade head` on a copy
  of the local database leaves the rosters readable.
- [x] 1.4 `RosterMemberIn` carries an optional `id`; `RosterMemberOut` states it.
  Verify the console and detail-page payloads still validate against their
  response models (`uv run pytest tests/test_team_disciplines.py -q`).

## 2. The save becomes a diff

- [x] 2.1 Rewrite `update_roster` in `routers/registrations.py` as the diff of
  design D1: named members updated in place, unnamed ones added, omitted ones
  marked removed, ordinals rewritten from the request order. A member id not
  belonging to this team is refused, not ignored.
- [x] 2.2 Write the log from that diff (one entry per added, removed, restored
  and per changed field; nothing for a reorder), with the actor and the two
  stored flags.
- [x] 2.3 Verify with new tests in `tests/test_team_disciplines.py`: a corrected
  nationality keeps the member's id; a reorder keeps all four ids and writes no
  log entry; two members identical in every field are renamed one at a time; a
  save that adds one and drops one keeps the other three; a foreign member id is
  refused.
- [x] 2.4 Verify the nine `Team.members` read sites still state the live roster
  with a removed member present: run `uv run pytest tests/test_team_disciplines.py
  tests/test_entrants.py tests/test_export_json.py tests/test_scheduler.py
  tests/test_mail_content.py -q --maxfail=3 --tb=short --show-capture=no`.
- [x] 2.5 Verify the member count, the below-minimum mark and the composition
  reminder all ignore a removed member — a test per surface, since each reads
  `len(team.members)` in its own file.

## 3. Restoring a removed member

- [x] 3.1 Restore returns the same member rather than a copy, and is refused
  where it would exceed the discipline's maximum. Verify both with tests.
- [x] 3.2 Verify a removed member is reachable as history and carries the moment
  and actor of its removal.

## 4. The organizer's own route

- [x] 4.1 Add the console's roster endpoint under the tournament prefix, gated by
  `require_console_access`, sharing the diff and the log with the entrant's route
  and recording `by_organizer` (design D6). Verify a fencer who is not an
  organizer of this tournament is refused, and that the entrant's own route still
  refuses a team that is not theirs.
- [x] 4.2 Verify the organizer's edit moves no money and sends no mail: a test
  asserting totals, credits, outstanding, refund state and the mailbox are all
  unchanged after a swap on a paid registration.
- [x] 4.3 Verify the deadline constrains neither actor: an edit by each, after the
  composition deadline, is accepted, and the organizer's entry states
  `after_deadline`.

## 5. The backup document

- [x] 5.1 Carry removed members and the roster log in `export_json.py`, bump
  `SCHEMA_VERSION` to 22, and read a v21 document as live members with an empty
  log. Verify with a round-trip test beside
  `test_v6_roundtrip_with_teams_and_rosters` and a v21 fixture restore.

## 6. The two editors

- [x] 6.1 `TeamsTab.tsx` sends the server's member ids; its client-side `rowId`
  gives way to them for stored members while a newly added member still needs a
  local key until it is saved. Verify with a test that a save after a reorder and
  a rename sends the ids it was given.
- [x] 6.2 `TeamsPanel.tsx` gains the roster editor and the log beside each team,
  and states a bound member's HEMA Ratings identifier, which the requirement
  already demands and the panel omits today. Verify the panel offers no admission
  and no cancellation, per the modified requirement.
- [x] 6.3 Split `TeamsPanel.tsx` along its seams if it approaches ~300 lines, per
  the frontend conventions.
- [x] 6.4 Add the Czech and English wording for the editor, the log and the
  history's start, and verify `npx vitest run src/i18n/locale-parity.test.ts`.

## 7. Finishing

- [x] 7.1 From `backend/`: `uv run ruff check .`, `uv run basedpyright`, and
  `uv run pytest tests/test_team_disciplines.py tests/test_export_json.py
  tests/test_api_contract.py -q --maxfail=3 --tb=short --show-capture=no`.
- [x] 7.2 From `frontend/`: `npm run typecheck`, `npm run check`, `npm test`.
- [x] 7.3 Confirm the venue scenario end to end on the running app: enter a team
  as a fencer, then from the console swap one member, and read the log — the
  entrant's save and the organizer's swap both there, named, with the organizer's
  marked as after the deadline where the tournament has one.
