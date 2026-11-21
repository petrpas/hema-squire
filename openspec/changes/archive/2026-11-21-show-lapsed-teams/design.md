## Context

`availability.live_teams` is the single reader of a team discipline's teams. It serves the
Teams view (`console_teams`), the Queue phase (`console_queue_teams`) and the Export team
tabs (`exporttables`), and it keeps only the teams on live registrations. A team on an
expired or cancelled registration therefore vanishes from all of them, and it is meant to
vanish from capacity and the waitlist. A cancelled team is not deleted. The `Team` row and
its members stay on the registration, so everything needed to show it still exists.

`sheet.py` projects the fencer list from every registration that is not cancelled and adds
member rows for each of its teams. An expired registration is not cancelled, so its
members are still listed as fighters.

The moments are already stored. A cancellation has `Registration.cancelled_at`. An expiry is
recorded by the scheduler as a `PaymentEvent` of kind `reservation_expired` or
`expired_holding_payment`. Money still held is `registration.credited_in(lane)`, which is
how `sheet.py` already states "Vypršela s platbou".

## Goals / Non-Goals

**Goals:**
- The organizer can see, in Teams and in Queue, every team that is gone because its
  registration lapsed, along with why, when, and any money still held.
- The fencer list stops listing fighters of a lapsed team.

**Non-Goals:**
- No reinstate or restore action on a lapsed team. Reinstatement stays a payment-intake
  matter (`payments`, Payments arriving after expiry).
- No change to the Export team tabs or the public entrants roster.
- No notification to the organizer when a team lapses. Seeing it in place is what was asked.

## Decisions

**D1 — A second reader, `lapsed_teams(session, discipline)`, beside `live_teams`.** It
returns the discipline's teams whose registration is expired or cancelled, each paired with
its reason and moment, most recent first. `live_teams` stays exactly as it is, so capacity,
the waitlist and the export cannot start counting lapsed teams by accident. The alternative
was a flag on `live_teams` that returns everything. It was rejected because every existing
caller would then have to filter, and the next caller would forget to.

**D2 — The moment.** A cancelled registration uses `cancelled_at`. An expired one uses the
`created_at` of its latest expiry event, falling back to `expires_at` where no event exists
(registrations that expired before the event was recorded). Using the latest event, not the
first, covers a registration that was reinstated and later expired again. Expiry events are
read once per request, grouped by registration, the way `payments.py` already reads
`expired_holding_payment`.

**D3 — One `LapsedTeamOut`, carried as a list apart from the live rows.**
`ConsoleTeamDisciplineOut` gains `lapsed: list[LapsedTeamOut]`. The Queue phase reads the
same shape from `GET /{slug}/queue/teams/{discipline}/lapsed`, because its roster response is
a bare list of live rows whose order is the waitlist's, and wrapping it would change a
contract the frontend and its tests already rely on. A lapsed row carries name, entering
fencer, entering address, roster members, `reason: "expired" | "cancelled"`, `lapsed_at`,
and the held amount and currency or none. A list apart keeps the live rows' shape and the
gutter and capacity logic untouched, and keeps `paid` and `waitlist_position` off a row that
has neither.

**D4 — Frontend: one shared section component per view, below the existing table body.**
The capacity line is already drawn between seated and waitlisted rows. The lapsed section
uses the same kind of line, labelled ("Propadlé a zrušené registrace" / "Expired and
cancelled registrations"). Its rows are faded the way queued rows already are, have no
gutter number and no action cells, and the reason cell reads e.g. "propadla 12. 11." or
"zrušena 3. 11.". Held money appears in the same idiom as `console.expiredHolding`. The
existing roster disclosure is reused in read-only mode. All colours come from existing
tokens, with no new saturated colour.

**D5 — The fencer list builds member rows only for live registrations.** In `sheet.py`,
roster members are collected only where the registration is live, which is the same
predicate as `live_registration()`, applied in Python on the loaded registration. The
registration row itself is unaffected. A row disappearing this way is what already happens
to a cancelled team's members, so the rules that reference `mem:<id>` rows already tolerate
their absence. Fixed numbers are kept by `rownumbers`, so a reinstated member returns under
the same number.

## Risks / Trade-offs

- [A long-running tournament piles up lapsed teams below the line] → Most recent first keeps
  the fresh ones on top. Typical counts are single digits, so nothing is folded away.
- [Reserved-but-past-`expires_at` registrations not yet processed by the scheduler are neither
  live nor expired] → They are listed nowhere for at most one scheduler tick, which is the
  same window they already spend out of capacity. Not addressed.
- [A rule (manual edit, HR verdict) on a lapsed member's row stops applying while the row is
  absent] → Same behaviour as a cancelled team's members today. The rule returns with the row
  on reinstatement.

## Migration Plan

No schema change. The work ships as one commit, and reverting the commit is the rollback.
