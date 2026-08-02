## 0. Sequencing

- [x] 0.1 Apply after `refine-setup-and-preview` and `add-explicit-publishing`. The
      `setup-navigation` delta here is written against the six-tab `Section allocation to
      tabs` that `add-explicit-publishing` leaves behind; if that change is archived
      later, re-base this delta on the five-tab wording before syncing
- [x] 0.2 Add `team_bounds` to the per-tab incompleteness marker attribution introduced by
      `add-explicit-publishing` (`Per-tab incompleteness markers`), pointing at
      `DISCIPLINES` — the setup key from task 3.2. No spec delta needed: that requirement
      already says an unrecognized key marks no tab and breaks nothing

## 1. Data model and migration

- [x] 1.1 Add `DisciplineKind(enum.StrEnum)` with `INDIVIDUAL` and `TEAM` to
      `backend/app/models.py`, beside the other enums
- [x] 1.2 Add to `Discipline`: `kind` (`str_enum(DisciplineKind)`, default `INDIVIDUAL`),
      `team_min: Mapped[int | None]`, `team_max: Mapped[int | None]`. Comment that
      `capacity` counts teams and `fee`/`fee_early`/`fee_eur`/`fee_early_eur` are per team
      when `kind is TEAM` (design D2), and that the kind is frozen once referenced
- [x] 1.3 Add `team_composition_deadline: Mapped[date | None]` to `Tournament`, beside
      `amendments_close`, with a comment that it checks and never enforces (design D7)
- [x] 1.4 Add `Team`: `id`, `tournament_id` (FK), `discipline_id` (FK),
      `registration_id` (FK `registrations.id`), `name: Mapped[str]` (String(200)),
      `waitlisted: Mapped[bool]` (default False), `composition_reminded_at:
      Mapped[datetime | None]`, `created_at` (server default `now()`). Relationships:
      `registration` back-populating a new `Registration.teams`, `discipline`, and
      `members` ordered by `TeamMember.ordinal`. Docstring: one team entered by one
      fencer, billed on that fencer's registration, no VS of its own (design D1)
- [x] 1.5 Add `TeamMember`: `id`, `team_id` (FK, cascade delete), `ordinal:
      Mapped[int]`, `name: Mapped[str]` (String(200)), `hr_id: Mapped[int | None]`
      (indexed), `club: Mapped[str | None]` (String(200)), `nationality: Mapped[str |
      None]` (String(100)). No FK to `fencers`, no uniqueness constraint — comment why
      (design D4): `Fencer.email` is unique and non-nullable, so a roster member cannot be
      an account, and `hr_id` null is the expected case
- [x] 1.6 Add `teams: Mapped[list[Team]]` to `Registration`, beside `entries` and
      `extra_selections`
- [x] 1.7 Alembic revision: the three discipline/tournament columns (kind defaulting to
      `individual` for every existing row, bounds and deadline null) plus the two new
      tables. Downgrade drops them. Docstring notes nothing is backfilled and no existing
      tournament changes behaviour (design Migration Plan)
- [x] 1.8 Run the migration against the dev database; confirm every existing discipline
      reads as individual and every existing total is unchanged

## 2. Pricing and availability

- [x] 2.1 In `backend/app/pricing.py`, extend `_itemized_selection_breakdown` to take the
      priced teams and add each team's `discipline_fee(...)` to the `DISCIPLINE_CATEGORY`
      subtotal once per team (design D3). Do **not** add them to the `disciplines` list
      that feeds `_condition_met(discipline_count=...)` — leave a comment saying so, since
      that separation is the whole reason `Team` is not a `RegistrationDiscipline`
- [x] 2.2 Thread teams through `_itemized_selection_total`, `selection_total`,
      `selection_totals`, and `selection_discounts` as an optional argument defaulting to
      empty, so every existing caller is unchanged
- [x] 2.3 In `registration_total`, price `[t for t in registration.teams if not
      t.waitlisted]` alongside the existing `active` non-substitute entries — waitlisted
      teams are excluded exactly as substitute placements are (`pricing.py:319`)
- [x] 2.4 Legacy path: a tournament using the legacy fixed fees and offering a team
      discipline still prices the team fee from the discipline row. Add a test pinning
      this rather than special-casing it
- [x] 2.5 In `backend/app/availability.py`, add `taken_team_slots(session, discipline)`
      and `team_queue_length(session, discipline)` counting `Team` rows joined to
      `Registration` under the same paid-or-unexpired-reservation predicate as
      `taken_seats`. Keep the module docstring's explanation of why these live here
- [x] 2.6 Make `taken_seats`/`queue_length` and the team counters mutually exclusive by
      kind — assert or early-return, so a team discipline never gets counted in fencers

## 3. Setup, availability gates, and the deadline

- [x] 3.1 In `backend/app/schemas.py`, add `kind`, `team_min`, `team_max` to the
      discipline create/update/out models with cross-field validation: bounds required and
      `1 <= team_min <= team_max` when kind is team, both rejected when kind is individual
- [x] 3.2 In `backend/app/setup.py`, add `MISSING_TEAM_BOUNDS` and report it from
      `setup_missing()` for every team discipline lacking valid bounds. The composition
      deadline is explicitly **not** a completeness item — comment it
- [x] 3.3 Add `team_composition_deadline` to `TournamentUpdate`/`TournamentOut`, validated
      only as a date on or before the tournament date. Add **no** ordering constraint
      against `registration_closes` or `amendments_close`: independence in both directions
      is the point (design D6)
- [x] 3.4 In `backend/app/routers/tournaments.py`, reject a discipline kind change when any
      `RegistrationDiscipline` or `Team` references the discipline (409)
- [x] 3.5 Exclude team disciplines from `hr_category_map` on write and from whatever
      builds the map's options; add a test that a team discipline never appears in it

## 4. Registration, teams, and rosters

- [x] 4.1 Schemas: a team input carries `discipline_id` and `name`; a team output carries
      id, discipline, name, `waitlisted`, fee in each configured currency, and members. A
      member input carries `name`, optional `hr_id`, `club`, `nationality`; validate
      `name` as non-empty trimmed text within the length limit, and nothing else — an
      unbound member is complete (spec: *A roster member is a named person*)
- [x] 4.2 In `backend/app/routers/registrations.py`, accept teams on the create path:
      validate each named discipline is a team discipline of this tournament, require a
      name, set `waitlisted = taken_team_slots(...) >= capacity`, create the `Team` rows,
      and include the non-waitlisted ones in the total. Multiple teams in one discipline
      are allowed — no dedup, no uniqueness check (design D1). Do not add a unique
      constraint on `(discipline_id, name)`: duplicate names are accepted deliberately
      (design D9), so add a test that two "Wolves" both persist unchanged
- [x] 4.3 Amendment path: replace the registration's teams as the selection is replaced.
      Removing a team deletes its members with it; re-entering an unchanged team keeps its
      roster where the client sends the team id, and starts empty where it does not.
      Recompute the total, keep VS and expiry, send the amendment confirmation as today
- [x] 4.4 Roster endpoints on their own path (`/registrations/{id}/teams/{team_id}/members`
      or a whole-roster PUT): authorize the entering fencer, refuse on a cancelled or
      expired registration, enforce at most `team_max` members, allow fewer than
      `team_min`, and persist order as `ordinal`. Assert in the handler — and in a test —
      that no pricing, VS, email, capacity, or refund path is touched (design D6)
- [x] 4.5 Roster editing must **not** consult `setup.amendment_availability`. Add a test
      that a roster save succeeds after `amendments_close` has passed
- [x] 4.6 Prefill: the create-team response (or the registration detail) carries the
      entering fencer's name, `hr_id`, club, and nationality as a suggested first member.
      Do not persist it server-side as a role — the client writes it as an ordinary member
- [x] 4.7 Price preview: accept team entries as `discipline_id` only, with no name and no
      roster required, and price each once (spec: *Price preview*)
- [x] 4.8 Registration availability response: report team disciplines with
      entered/capacity in teams, the waitlist length, roster bounds, and the tournament's
      composition deadline

## 5. Emails and the reminder

- [x] 5.1 In `backend/app/emails.py`, extend `_summary_lines` to emit one line per team —
      team name, discipline, per-team fee, and a waitlisted marker reusing the existing
      substitute marker's shape. Two teams in one discipline are two lines, never a
      quantity
- [x] 5.2 Confirm the `queued` shortcut in `send_registration_confirmation` and
      `send_amendment_confirmation` (`emails.py:71`, `emails.py:275`) still reads
      correctly when the registration carries only waitlisted teams — extend the condition
      to cover teams
- [x] 5.3 Add `send_composition_reminder(...)`: names the short teams, the shortfall per
      team, the deadline, and links to the roster editor. Localized like every other mail
- [x] 5.4 In `backend/app/scheduler.py`, add `process_composition_reminders(session,
      tournament, mailer)` beside `process_reminders`: skip when the tournament has no
      deadline; select teams on non-cancelled, non-expired registrations, not waitlisted,
      with `composition_reminded_at` null and fewer members than `team_min`, whose
      deadline is within the reminder window; send once and stamp
      `composition_reminded_at`. Wire it into `run_tournament_tick`
- [x] 5.5 Test that a second tick sends nothing, that a completed roster is never
      reminded, and that a tournament with no deadline reminds nothing

## 6. Export

- [x] 6.1 In `backend/app/export_json.py`, raise `SCHEMA_VERSION` to 6 and add 5 to the
      accepted set at line 216
- [x] 6.2 Export discipline `kind`/`team_min`/`team_max` in `_record(d, [...])`, the
      tournament's `team_composition_deadline` in `_TOURNAMENT_FIELDS`, and a `teams`
      block per registration carrying name, discipline code, waitlisted, and the ordered
      members with name, hr_id, club, nationality
- [x] 6.3 Restore: recreate teams against the remapped registration ids and the
      tournament's disciplines by code; recreate members in order. Never create a `Fencer`
      from a member (design D4) — add a test asserting the account count is unchanged
- [x] 6.4 Upgrade path: a v1–v5 document restores with every discipline individual, no
      teams, and no deadline. Test with a fixture captured before this change
- [x] 6.5 Leave `backend/app/sheet.py` and `sheets_export.py` untouched; add a test that a
      tournament with teams produces the same worksheets as one without

## 7. Organizer teams view

- [x] 7.1 Backend: a read-only console endpoint returning, per team discipline, its teams
      with name, entering fencer, ordered roster with bindings, member count against the
      bounds, waitlist position, and a `below_minimum` flag computed as "deadline set, in
      the past, and members < `team_min`"
- [x] 7.2 Frontend: a read-only teams view in the console. No admit, no edit, no cancel —
      not disabled controls, absent ones (spec: *Organizer's read-only teams view*)
- [x] 7.3 Distinguish below-minimum teams with `--stamp`; unbound members render as plain
      names with no warning treatment

## 8. Frontend — Setup and preview

- [x] 8.1 Disciplines table: a kind control per row; roster-bound inputs shown only on team
      rows; capacity and price column labels switching per row kind (design D2)
- [x] 8.2 Composition deadline field below the table, shown only while a team row exists in
      the current draft (including unsaved), written by the tab's single save control
- [x] 8.3 `SetupPreview.tsx`: both fencer-facing faces render team disciplines — teams
      counted in teams, per-team fee, roster bounds, deadline
- [x] 8.4 Verify against `CLAUDE.md`: no emoji, no filled icons, no shadows, no radius
      above 2px, `--stamp` as the only saturated colour, no hex outside `tokens.css`

## 9. Frontend — registration and roster editor

- [x] 9.1 Team section on the registration form: discipline row stating bounds and per-team
      fee, an add-team action requiring a name, one line per added team with removal, and
      the deadline note. Each added team priced separately, never as a quantity
- [x] 9.2 Roster editor on the registration view: add/remove/rename/rebind/reorder,
      bounded by `team_max`, saving through the roster endpoint alone
- [x] 9.3 HR picker reusing `GET /accounts/hr/search` with the nationality filter — the
      same component the profile page uses. Free text when nothing is selected, presented
      exactly like a bound member afterwards
- [x] 9.4 Prefill the entering fencer as the first member when a roster is opened empty for
      the first time; editable and removable like any other row
- [x] 9.5 Keep the roster editor visible after the amendment window closes, while the
      add-team and remove-team controls disappear
- [x] 9.6 `api.ts` additions and `i18n/cs.json` + `i18n/en.json` for every new string,
      including the two senses of "substitute": individual waitlist versus a team on the
      waitlist. Czech renders both as *náhradník* — pick distinct wordings
      (e.g. *náhradník* for the fencer queue, *tým v pořadí* for a waitlisted team) and
      note the choice in the locale files

## 10. Tests

- [x] 10.1 Pricing: per-team fee counted once regardless of roster size; two teams counted
      twice; waitlisted team excluded; team fee inside a `discipline`-scoped discount;
      team entry not satisfying a `discipline_count` condition
- [x] 10.2 Capacity: team discipline counted in teams; waitlisting at capacity; a full
      individual discipline unaffected by teams
- [x] 10.3 Registration: team-only registration accepted, priced, and confirmed; two teams
      by one fencer; team removal on amendment dropping its roster
- [x] 10.4 Roster: bounds enforced at the maximum and not at the minimum; ordering
      preserved; unbound member accepted; editing after `amendments_close`; editing
      refused on an expired registration; no total, VS, email, or refund movement
- [x] 10.5 Deadline: below-minimum flag appears only after the deadline; nothing is
      cancelled, waitlisted, or freed; roster still editable the day before the tournament;
      no deadline means no flag and no reminder
- [x] 10.6 Export: v6 round-trip with teams and rosters; v5 fixture restores with none;
      no account created from a member; Sheets output unchanged
- [x] 10.7 Regression: a tournament with no team discipline produces byte-identical
      pricing, availability, email, and export output to before the change
