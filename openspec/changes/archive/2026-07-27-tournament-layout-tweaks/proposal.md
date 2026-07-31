## Why

The signup form asks for a name twice (once as a field, again inside the HR
search), and it binds an account to a HEMA Ratings identity without an explicit
"this is me" confirmation — a heavy, hard-to-undo link made too casually. The
tournament list cards and the tournament detail page have also outgrown their
first layout: cards run the date and place into one cramped line with no room
for a logo or subtitle, and the detail page mixes "read about the tournament"
with "fill in a registration form" on a single screen. These are small,
self-contained UI and data tweaks that make the fencer-facing flow calmer and
give organizers a few expected fields (logo, subtitle, schedule, ruleset).

## What Changes

- **Signup form:** the form's own name field doubles as the HR search query —
  no second name line. Before an HR profile is bound, a confirmation box shows
  the candidate's full details and a link to their hemaratings.com page and
  asks the fencer to confirm the account is theirs. The confirmed line reads
  `HEMA Ratings profile confirmed: Petr Lukeš (8956)` (name with HR id).
- **Tournament data:** a tournament gains an optional **subtitle** (may be
  longer than the name, often empty) and an optional **logo** (image stored as
  bytes in SQLite, capped and downscaled on upload). Each **discipline** gains
  optional `when`/`where` and an optional ruleset (short name + external link).
  Each **extra service** (`ExtraItem`) gains optional `when`/`where`/`remark`.
- **Tournament list cards:** 1 em left/right padding inside the card, the logo
  on the left when present, the subtitle under the name, and date + place laid
  out as responsive columns instead of one long line — degrading cleanly when
  subtitle, logo, or location are absent.
- **Tournament detail split into two screens:** (1) an information screen
  opened from the list — disciplines (name, capacity as `registered/capacity`,
  optional when/where and ruleset) and other actions (seminars, afterparties,
  after-sparrings, accommodation) as info-only groups, with **no** mention of
  gear lending or merch; (2) a dedicated **Register** screen, reachable only
  when the tournament is open and something has an open slot, presenting every
  purchasable item as one long list grouped into sections (tournament,
  actions, gear lending, merch & other).

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `fencer-accounts`: signup reuses the name field as the HR search query and
  requires an explicit ownership confirmation (with profile details and a
  hemaratings.com link) before binding; confirmed line shows the HR id.
- `tournament-admin`: tournament definition gains subtitle and logo; disciplines
  gain optional schedule (when/where) and ruleset (name + link); extra services
  gain optional when/where/remark.
- `fencer-home`: tournament list cards gain logo, subtitle, and a responsive
  date/place layout; the tournament detail is split into an information screen
  and a separate register screen, the information screen grouping disciplines
  and non-purchasable actions without gear/merch.
- `registration`: the register step becomes its own screen, available only when
  the tournament is open and a slot is free, listing every purchasable item
  grouped by section; the fencer-facing tournament list carries logo and
  subtitle.

## Impact

- **Backend:** `Tournament` (subtitle, logo bytes + mime), `Discipline`
  (schedule/ruleset fields), `ExtraItem` (schedule/remark fields) in
  `models.py`; matching Pydantic schemas in `schemas.py`; a logo upload/serve
  endpoint and the fencer-list/detail payloads in `routers/tournaments.py`; one
  Alembic migration. Logo uploads are size-capped and re-encoded.
- **Frontend:** `Login.tsx` (name reuse + confirmation box), `FencerHome.tsx`
  (card layout, logo, subtitle, responsive date/place), `TournamentDetail.tsx`
  (split into information + register screens), `SetupPanel.tsx` (logo, subtitle,
  discipline schedule/ruleset, extra when/where/remark inputs), `api.ts` types,
  i18n `en.json`/`cs.json`, and `tokens.css`/styles — all within the Bureau
  1952 prohibitions in `CLAUDE.md` (no gradients, shadows, rounded cards, etc.).
- **No breaking changes:** every new field is optional; existing tournaments,
  registrations, and totals are unaffected.
