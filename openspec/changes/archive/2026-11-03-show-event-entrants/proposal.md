## Why

An event (a record with no discipline) shows nobody publicly. Its detail offers no Entrants tab, and its card states no fill and no count, so a seminar run as an event looks empty even while it fills up. The same seminar added to a tournament has a public roster. The backend already builds seminar and other-program rosters for an event; the rule in `discipline-less-events` that hides the whole Entrants tab was meant to drop seat counts and the queue, which only disciplines have, and took the program rosters with it. Item capacity (`item-capacity`) has since given seminars a limit worth showing.

## What Changes

- An event's public detail offers the Entrants tab exactly when the event offers at least one seminar or other-program item, whether or not anyone has taken a place yet. An event offering only an afterparty or goods still offers no tab.
- A side-event roster whose item has a capacity draws the capacity line under its last row, on events and tournaments alike. Nothing is listed below it, since an item keeps no queue. A roster of an uncapped item, and any roster of a held record, still draws none.
- An event's card carries one fill meter per seminar or other-program item that has a capacity, drawn as a discipline's meter is. Uncapped program items, the afterparty and goods get no meter. A tournament's card keeps its discipline meters only.
- On an event the list entry's fencer and club counts, and the familiar faces, are taken from the people holding a place at its seminars and other program, the same people its public rosters list. A tournament's figures are unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `discipline-less-events`: an event offers the Entrants tab when it offers a publicly rostered item; it still states no discipline seat counts and offers no queue.
- `public-entrants`: a side event with a capacity draws the capacity line; "an event has no capacity" no longer holds.
- `public-browsing`: on an event, `entrant_count`, `club_count` and `familiar` are drawn from program attendees, and a list entry carries the event's program meters.
- `fencer-home`: an event's card shows its program meters where a tournament's card shows discipline meters.

## Impact

- Backend: `app/entrants.py` (`_event` draws the line from the item's capacity), `app/list_counts.py` (an event's seated entrants come from program items), `app/familiar.py` (no rating order on an event), `app/schemas.py` and `app/routers/tournaments.py` (program meters on the list entry).
- Frontend: `TournamentDetail.tsx` (tab condition), `TournamentCard.tsx` and `CapacityMeter.tsx` (item meters), `api.ts` (the new list field).
- API: `OpenTournamentOut` gains an additive field; no field changes meaning on a tournament.
- No migration.
