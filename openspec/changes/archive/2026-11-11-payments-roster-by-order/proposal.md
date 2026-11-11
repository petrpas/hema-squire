## Why

On a team tournament the Payments phase lists the start field, and the start field
is mostly roster members: TTT Test shows 75 rows, of which 16 carry money and 59
are roster members reading dashes in every money cell. A captain appears twice,
once for the order and once as a member. Neither the row nor the pairing dialog
says what an order bought, so a club paying for "the team" cannot be found by the
team's name. Money is a question about orders. One variable symbol is one order,
and an order may hold several teams, an individual entry and rentals together.
The table should therefore list orders and say what each one holds.

## What Changes

- The Payments phase's registration table lists **every row except roster member
  rows**: registrations, imported rows and hand-entered rows. Member rows hold no
  contract and leave this table. They stay on Fencers, Matching and Export.
  **BREAKING** for the etl-console guarantee that every tab after Fencers lists the
  same set: Payments now lists orders, not fighters.
- The first-band tab **"Šermíři" / "Fencers" is renamed "Registrace" /
  "Registrations"**.
- A new **Obsah / Contents** column states in short what the order holds, counting
  only what is billed. A single team is named; otherwise it reads like
  `2 týmy · LS · 3 položky`.
- **Every row unfolds in place** into its priced lines: one per individual
  discipline, one per team entered (named, with its discipline), one per extra item
  with its quantity, and each discount as a negative line. The idiom is the one the
  Teams console uses for rosters.
- Lines are stated in the tournament's **local currency**, which is EUR on an
  EUR-local tournament.
- Placements in a queue (substitute entries, waitlisted teams) appear among the
  lines **greyed and in italic** and are counted neither in the summary nor in the
  sum.
- Where the lines disagree with the frozen issued total, because the organizer
  changed a price after issuing, an extra **difference line** states the gap. The
  organizer closes it with the tools that already exist: waiver, recorded payment
  and amendment. No breakdown is frozen.
- The **pairing dialog** finds a registration by **team name and club name** as well
  as by the holder's name, and each candidate shows the same contents summary. The
  automatic name-resolver proposal is unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `etl-console`: Payments lists orders rather than the start field. Member rows are
  not listed there.
- `payments-console`: the first-band tab is renamed, and the table gains the
  Contents column and the unfolding priced lines.
- `name-assisted-matching`: the link dialog's text lookup also reaches team and
  club names and shows each candidate's contents.

## Impact

- Backend: a new pricing function that itemises a persisted registration with team
  identities and queued placements (built over `registration_breakdown`). A new
  read endpoint returns the lines of a tournament's registrations. The transaction
  roster gains club and team names.
- Frontend: `rowsForPhase` for `payments`, the payments phase columns,
  `PaymentTabs` labels, a new unfolding lines component, and the search in
  `LinkDialog`. i18n cs/en.
- No data model change and no migration. Totals, credits and settled states are
  untouched.
- Items stay per registration (see the team-items-per-team-gap note); per-team
  items are a later change.
