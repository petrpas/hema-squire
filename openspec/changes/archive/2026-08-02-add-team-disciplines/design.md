## Context

The data model is fencer-shaped end to end. `Registration` is unique on
`(tournament_id, fencer_id)`; capacity is consumed by `RegistrationDiscipline` rows
(`availability.py`); price is a sum over one fencer's disciplines and extras
(`pricing.py`); a VS, an expiry, a QR code, a reminder, a refund state and every bank
matching path hang off one registration (`matching.py`, `emails.py`, `scheduler.py`).

Three facts about team events, established with the owner during exploration, decide
almost the whole design:

1. The fee is **per team**, not per member.
2. Only the fencer who enters the team must be registered. Roster members are named
   people who mostly are not and will not become Squire users.
3. The roster is legitimately unknown at entry time, and needs a deadline of its own.

Two hard constraints from the existing code:

- `Fencer.email` is unique and non-nullable (`models.py:113`). There is no account-less
  fencer, and manufacturing one — placeholder emails, a nullable email — would leak into
  auth, login, dedup, the participant list and every export. A roster member therefore
  cannot be a `Fencer`.
- `hr_index.search(query, nationality)` already exists and is already exposed as
  `GET /accounts/hr/search` (`accounts.py:21`) — deterministic, diacritics-insensitive,
  nationality-filterable, no LLM. The roster editor needs exactly this and nothing more.

## Goals / Non-Goals

**Goals:**

- Express a team discipline, a team entry, and a roster without disturbing payments.
- Keep every existing money path — VS allocation, totals, QR, matching, reminders,
  refunds, the payments console — literally unaware that teams exist.
- Make roster editing a cheap operation with no pricing, capacity, or email consequence.
- Reuse the HR picker rather than growing a second name-matching path.
- Guarantee that a canonical export/restore does not lose rosters.

**Non-Goals:**

- Per-member pricing. Ruled out: it is incompatible with a roster that is unknown when
  the fee is paid, and it would break `total_amount` being frozen at registration.
- Roster members as accounts, or as registrations, or as participants.
- Admitting a waitlisted team, editing a roster on the entrant's behalf, cancelling a
  team as an organizer action.
- Team results, the public participant list, the Google Sheets export, HR submission of
  team outcomes.

## Decisions

### D1 — A team is its own line item, not a `RegistrationDiscipline`

`Team` hangs off `Registration` in parallel with `RegistrationDiscipline`, rather than
reusing it with a nullable team pointer.

```
Registration ──< RegistrationDiscipline ──> Discipline (kind=individual)
     │             is_substitute
     │
     └──< Team ────────────────────────────> Discipline (kind=team)
            name, waitlisted                  team_min, team_max
            │                                 fee = per team
            └──< TeamMember (ordinal, name, hr_id?, club?, nationality?)
```

Three things follow for free, which is the reason for the choice:

- **Discounts stay individual by construction.** `_condition_met` counts
  `len(disciplines)` from `RegistrationDiscipline` rows (`pricing.py:161`). Teams are not
  in that list, so a team entry cannot trip a "two disciplines, 10 % off" discount. No
  flag, no exclusion rule, no way to get it wrong later.
- **The substitute vocabulary does not collide.** `is_substitute` keeps meaning
  "individual waitlist placement". A waitlisted team gets its own field. The domain's
  other meaning of "substitute" — the fourth roster member — is not modelled at all
  (D5), so the word is used for exactly one thing in the schema.
- **Multiple teams per fencer per discipline are expressible.**
  `RegistrationDiscipline` is unique on `(registration_id, discipline_id)`, which would
  have capped a fencer at one team per discipline. `Team` carries no such constraint.

*Alternative considered:* a `TeamRegistration` with its own VS, expiry and payment.
Rejected — it duplicates VS allocation, reservation expiry, SPAYD/QR generation, the
reminder job, refund state and bank matching, for a fee that one fencer pays anyway.

### D2 — `capacity` and `fee` are reinterpreted, not duplicated

A team discipline reuses `capacity` (now counting teams) and `fee`/`fee_early`/`fee_eur`/
`fee_early_eur` (now per team). No `team_capacity` or `team_fee` columns.

The organizer types one number into one column and the discipline's kind says what it
means. Duplicate columns would leave two sources of truth for "how much does entering
this cost", and every pricing, preview, email and export path would have to pick.

*Cost:* the words "capacity" and "fee" mean different units on different rows, so the
Setup UI must label them per kind, and the spec must state the unit explicitly wherever
either is read.

### D3 — Team fees join the discipline subtotal, not a new pricing category

In `_itemized_selection_breakdown`, a team entry contributes its per-team fee to the
existing `DISCIPLINE_CATEGORY` subtotal. It does **not** get its own `ExtraCategory`.

A discount scoped to disciplines therefore covers team fees, which is the behaviour an
organizer would predict from the wording. A discount *conditioned* on discipline count
still ignores teams (D1). Condition and scope diverge deliberately: "how many things did
you enter" is a question about the fencer, "what is this money for" is a question about
the item.

Waitlisted teams are excluded from the priced set, mirroring `pricing.py:319`, which
already excludes substitute placements from a registration's total.

### D4 — Roster members are rows, not entities

`TeamMember` carries `name`, `hr_id`, `club`, `nationality`, `ordinal`. It has no
foreign key to `fencers`, no uniqueness constraint, and no identity beyond its row.

Two teams naming the same person are two rows. A member who is *also* an individually
registered fencer is not linked to that registration. `hr_id` is the only thing that
could ever join them, and it is stored, so a future change can do that reconciliation —
but nothing in this change depends on it, and nothing breaks when `hr_id` is null.

`hr_id` null is the expected case for the population these events actually draw, not a
degraded one. No spec, UI state, or export path may treat an unbound member as an error
or as incomplete.

*Alternative considered:* reusing `ImportedRow` and the ETL matching machinery.
Rejected — that path is LLM-backed, batch-oriented, decision-cached, and built for
reconciling a spreadsheet of strangers. A roster is five names typed by someone who knows
them; the deterministic index search is the right tool and is already exposed.

### D5 — The roster is an ordered list with no roles

No captain flag, no reserve flag. `team_min`/`team_max` bound the count and `ordinal`
fixes the order. Who fences and who sits out is a race-day decision that the system
never observes, and modelling it would create a field that is wrong by the time it
matters.

The entering fencer is prefilled as ordinal 0 in the editor. That is UI convenience
only — no stored role, fully editable, removable (a club officer may enter a team they
do not fence in).

### D6 — Roster editing is not an amendment

Because the fee is per team, a roster edit provably cannot change a total. Roster
mutation therefore runs on its own endpoint and MUST NOT recompute price, reissue a VS,
resend a confirmation, alter refund state, or check capacity — and is not gated by
`amendment_availability` (`setup.py:92`).

Adding or removing a *team* does change the total, so it is an amendment and is gated as
one.

This is the decision that keeps the change moderate rather than large: it removes roster
editing from the amendment machinery entirely, and it makes the composition deadline
orthogonal to `amendments_close` in both directions. Money may close early while names
stay open late.

### D7 — The composition deadline checks; it never enforces

`tournaments.team_composition_deadline`, nullable, meaningful only when a team discipline
exists.

```
  entry ─────────────► deadline ──────────────► tournament date
  (name + entrant,       │                       │
   roster optional)      │                       │
                         │  under minimum?       │  roster still editable
                         │  → flagged for the    │  the whole way
                         │    organizer          │
                         │  → nothing cancelled  │
                         │  → no capacity freed  │
```

It does not lock the roster, does not cancel, does not free capacity, and does not block
anything. Under-minimum teams are marked in the organizer's teams view after it passes;
the organizer decides, using controls that already exist.

Rationale: for the population these rosters draw, being short at the deadline will be
common rather than exceptional, so an automatic consequence would fire mostly on cases
the organizer wanted to handle by hand. And swapping an injured fencer the night before
is normal, so a lock would be worked around rather than obeyed.

A reminder to the entering fencer before the deadline, for teams still short, follows the
shape of the unpaid-reservation reminder (`reminder_day` / `reminded_at`): one send, a
timestamp on the row so it is not repeated.

### D8 — Export version 6 is mandatory; the Sheets export is untouched

`export_json.py` is the restore document, not a report — its own docstring calls it
everything needed to reconstruct a deployment. Teams and rosters must round-trip or a
restore silently loses them. `SCHEMA_VERSION` 5 → 6; the reader keeps accepting 1–5 and
restores them with no teams.

`sheet.py` and the public participant list are deliberately untouched. A roster member
has no registration to occupy a row in the legacy Fencers worksheet, and how team
participation should surface publicly is a product question with no forced answer yet.

### D9 — Team names are not unique and are not checked

Two teams in one discipline may carry the same name. No uniqueness constraint, no
warning, no disambiguating suffix.

The system has no way to know whether two "Wolves" are a mistake, two squads from one
club, or two unrelated clubs that picked the same animal. An organizer looking at the
teams view sees both, with their entering fencers and their rosters, and can write to
somebody — which is a better instrument than a constraint that would block a legitimate
entry to prevent a cosmetic one. The teams view exists partly for this.

### D10 — Setup allocation

The disciplines table gains kind and roster-bound columns on the `DISCIPLINES` tab. The
composition deadline also goes on `DISCIPLINES`, below the table and shown only when at
least one team discipline is configured — it is meaningless without one, and
`TOURNAMENT` is already the busiest tab.

## Risks / Trade-offs

- **Overloaded `capacity`/`fee` units** → the spec states the unit at every point of
  reading, and the Setup UI labels the columns per row kind. The alternative (parallel
  columns) was judged worse: two sources of truth for one number.
- **A team fee is charged to one fencer's registration, so an unpaid entrant kills the
  team** → accepted. It follows directly from "per-team fee, entered by one fencer" and
  is how the money actually moves; splitting it would require the members to be payers,
  which they are not.
- **Multiple teams per entrant complicates the registration summary and confirmation
  email** → team lines are itemized by team name, so two teams in one discipline read as
  two lines rather than a quantity.
- **A roster member duplicating an individually registered fencer is invisible** →
  accepted for now; `hr_id` is stored precisely so a later change can reconcile without a
  migration.
- **The deadline enforcing nothing means a tournament can reach its date with short
  teams** → intended. The organizer is told, and decides. Making it automatic was
  considered and rejected in D7.
- **A team discipline in `hr_category_map` would produce a meaningless HR category** →
  team disciplines are excluded from the map rather than mapped to nothing.

## Migration Plan

1. Alembic: add the discipline columns with `kind` defaulting to individual for every
   existing row, add `tournaments.team_composition_deadline` as null, create `teams` and
   `team_members`. No data is backfilled and no existing tournament changes behaviour.
2. Ship the backend with team support inert: no tournament has a team discipline, so no
   pricing, availability, email, or export path changes its output.
3. Export version 6 goes out with the backend. A v5 document produced before this change
   still restores.
4. Rollback: dropping the new tables and columns loses only team data, which no v5
   deployment has. No existing table is altered in a way an older build cannot read.

## Open Questions

- Should the composition deadline be per tournament or per team discipline? Per
  tournament is specified here, matching the brief. A tournament running two team events
  on different days could want two dates; no evidence yet that it is needed.
- Does a team need a club affiliation of its own, separate from the members' clubs?
  Deferred — the team name is free text and can carry it today.
