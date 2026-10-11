## Why

Squire has specified a public participant list since `add-external-registration`,
and `GET /api/tournaments/{slug}/participants` answers it, but no screen has
ever shown it. In the meantime the organizer is asked in Setup how unpaid
entrants should appear on that list. A fencer can therefore find out who else is
entered only from a roster image the organizer chose to post. It is time for the
lists to be readable on the tournament's own page.

The endpoint is also not yet fit to carry a screen. It returns one flat list of
people in registration order rather than a roster per discipline. It drops the
queue, names the entering fencer where a team discipline should name the team,
carries no HEMA Ratings identity or rank, and answers for a draft or a cancelled
tournament, while the public detail already refuses both.

## What Changes

- The tournament detail page gains an **Entrants** tab (`Přihlášení`), offered on
  every published tournament. Inside it, a band holds one roster per discipline,
  individual and team, in the tournament's discipline order.
- An individual roster lists **No., Fencer, Nat., Club, HRID, Paid**: the printed
  roster's columns without the rank. The HRID links to the fighter's HEMA Ratings
  profile, and the band of disciplines states no counts. Its rows are the Export discipline tab's own: the
  organizer's corrections and deletions applied, and HEMA Ratings' nationality and
  club over the fencer's. They are ordered paid first, then by registration order.
- Unpaid entrants are **always shown, greyed**, where Squire collects the money.
  Where it does not, only the organizer's hand tick is shown, and an unticked
  entrant carries no mark (unchanged).
- **BREAKING** The unpaid-list setting (`unpaid_list_treatment`) is removed from
  the model, the API, Setup and the export document. Hiding unpaid entrants left
  a queue standing behind seats that looked free.
- In **automatic mode**, a capacity line divides seated from queued, and the
  queue follows it in queue order. Each queued row states its position (the
  number the fencer is shown on their own registration), carries a mark where it
  waits under a participation condition, and leaves its Paid cell empty.
- In **manual mode**, the roster shows no queue and draws no capacity line,
  because import may seat beyond capacity. It still states the moment the roster
  last reached Squire (unchanged).
- **Seminars and other side events** get a roster each after the disciplines, at
  `/t/:slug/entrants/events/:item`. The **afterparty does not**, and goods have none.
- A team discipline's roster lists **each team by name with its members**. In
  automatic mode the team waitlist follows the capacity line, as the queue does.
- On a **tournament already held**, the rosters remain and the queue and the
  team waitlist are no longer shown.
- The Entrants tab, and a discipline within it, **have their own address**
  (`/t/:slug/entrants`, `/t/:slug/entrants/:discipline`), so a roster can be
  linked to. Every other tab of the detail page stays unaddressed.
- On the information screen, each discipline's registered count **links to that
  discipline's roster**. The home card itself stays a single link: a link inside
  it would be a link within a link, which `fencer-home` already rules out.
- The public list answers **not-found for a draft or a cancelled tournament**, as
  the public detail does.

## Capabilities

### New Capabilities
- `public-entrants`: the public, per-discipline rosters. Covers what a roster
  lists and in what order, the capacity line and the queue by mode, teams, held
  tournaments, the tab and its address, and the payload's limits.

### Modified Capabilities
- `registration`: **Public participant list** is replaced. Its payment rules move
  into `public-entrants` without the hidden/greyed choice.
- `external-registration`: **A participant list Squire does not maintain says
  so** now points at `public-entrants` for where that statement stands.
- `fencer-home`: the detail page shell gains the Entrants tab and its address,
  and the information screen's discipline counts become links to the rosters.
- `public-browsing`: the entrant rosters join the reads answered without a
  credential, under the same publication line. The unpaid-list treatment leaves
  the list of withheld organizer fields.
- `routing`: `/t/:slug/entrants` and `/t/:slug/entrants/:discipline` are added to
  the URL table.
- `tournament-admin`: the unpaid-list treatment editor is removed.
- `payments`: the unpaid-list treatment leaves the list of Setup parameters that
  payments-off hides.

## Impact

- **Backend**: `routers/registrations.py` (`/participants` is replaced by a
  per-discipline entrants endpoint), a new projection module built on
  `sheet.base_rows` + `rules.replay` + `exporttables.table_rows`, `availability`
  queue order, `Team`/`TeamMember`. Removal of `UnpaidListTreatment`, of
  `Tournament.unpaid_list_treatment` (Alembic migration), of the schema fields,
  and of the `export_json` key, with the document version bumped.
- **Frontend**: `TournamentDetail.tsx` (new tab, routed), a new `entrants/`
  directory for the roster band and tables, `routes.ts` (`entrants()`), `App.tsx`
  routes, `TournamentFace.tsx` (count links), removal of the treatment from
  `setup/PaymentModeSection.tsx`, i18n in cs and en.
- **Tests**: `test_participants.py` is rewritten against the new contract.
  Frontend tests cover the tab, its address, the greyed and empty cells, and the
  queue by mode.
- No change to the console, the Export tables or the printed roster
  (`roster-print` keeps its yes/no on queued rows by owner decision).
