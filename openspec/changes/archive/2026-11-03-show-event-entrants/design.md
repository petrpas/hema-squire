## Context

An event is a record with no discipline (`discipline-less-events`). Three public surfaces say who is coming, and all three are silent on an event today:

- **Detail, Entrants tab.** `TournamentDetail.tsx` renders the tab only under `!isEvent`. The backend is already right: `entrants.rosters()` returns discipline rosters followed by one roster per `PUBLIC_EVENT_CATEGORIES` item (seminar, other program), so an event's answer is its program rosters, or an empty list.
- **Card counts and familiar faces.** `list_counts.seated_entrants` joins `RegistrationDiscipline` and keeps individual placements only, so an event's `entrant_count` is always 0 and the foot hides. `familiar.familiar_entrants` selects among the same `seated` map and finds nobody.
- **Card meters.** `TournamentCard` maps `tournament.disciplines` to `CapacityMeter`. An event has none.

Item capacity (`item-capacity`) gave an item a nullable `capacity`; a full item is sold out and keeps no queue. `entrants._event` still returns `line=False` unconditionally, from the time an item had no capacity.

Owner decisions of 2026-11-03 fix the behavior: tab when the event offers a rostered item even if empty; meters for capped seminar/program items on events only; counts and familiar faces from the same attendees; the item line drawn on any record.

## Goals / Non-Goals

**Goals:**
- An event's program is as visible as a tournament's disciplines: roster, fill, count.
- One definition of "who is at an event" shared by the counts, familiar faces, meters and rosters.
- A tournament's card and figures do not change.

**Non-Goals:**
- Meters or rosters for the afterparty or goods, capped or not.
- Item meters on a tournament's card, or on the detail page's discipline list.
- A queue for items.
- Any change to how item capacity is enforced at registration.

## Decisions

### D1. The tab condition is computed on the client from the detail's items

The detail already carries `extra_items` with their category. The tab is offered when `!isEvent || extra_items.some(i => PUBLIC_ROSTER_CATEGORIES.has(i.category))`. Seminar and other program are the categories; the frontend keeps the list beside a comment naming `entrants.PUBLIC_EVENT_CATEGORIES` as its source.

*Alternative:* a `has_rosters` boolean on the detail payload. It would keep the category list in one place, but adds a field to settle something the client can read from data it already holds. Chosen against; a test pins the two lists together instead (see tasks).

Reaching the entrants address of an event that offers no tab behaves as it does today.

### D2. The item line reuses the discipline line's conduct

`_event` sets `line = conduct.queue and item.capacity is not None`. `conduct.queue` is already "automatic and not held", the same condition under which a discipline roster draws its line, so a held record and a manual one draw none for items as for disciplines. The frontend `IndividualRoster` already draws `CapacityLine` from `roster.line`. Labelled as a plain capacity line, though, it read in the eye check as "the places are these three" under a 3/10 seminar. So `Roster` and `RosterOut` carry `capacity` for a side event whose line is drawn (null otherwise), and `CapacityLine` takes it and states `kapacita N` / `capacity N` in place of the plain label. Discipline lines keep their labels: a queue may stand below them, and the band and cards already state the discipline's capacity.

### D3. An event's "seated" entrants come from program items, in the same function

`list_counts.seated_entrants` splits its tournaments by `is_event`. Tournaments keep today's query. For events a second query joins `RegistrationExtra` → `ExtraItem` with `ExtraItem.category in PUBLIC_EVENT_CATEGORIES`, `live_registration()`, distinct by registration, and drops `removed` registrations exactly as the discipline branch does. Both branches fill the same `dict[int, list[SeatedEntrant]]`, so `entrant_counts` and `familiar_entrants` need no change in what they select among.

Keeping it one function with two queries (not one per entry) holds the "computed for all entries together" requirement: at most two queries for the whole list.

*Alternative:* derive event attendees from `entrants.rosters()`. That runs the rule replay per record, which the list was built to avoid.

`SeatedEntrant` reads name, club and nationality from `Fencer`, as the discipline branch does; the rosters read them from the replayed export rows. That divergence already exists for tournaments and is not widened here.

### D4. No rating order on an event

`familiar._ratings` reports a tournament as rated whenever a snapshot exists, and an event may keep one from a time it had disciplines. With no individual discipline the code set is empty and every fencer is unrated, yet `ranked` would read true. `_ratings` skips a tournament with no individual discipline, so the order falls back to name and `ranked` is false. This also corrects a tournament whose only disciplines are team ones, which has the same empty code set.

### D5. `program_meters` on the list entry

`OpenTournamentOut` gains `program_meters: list[ProgramMeterOut]`, default empty, with `id` (the item's id, only as a list key), `name`, `entered` and `capacity`. It is filled only for events, for capped items in `PUBLIC_EVENT_CATEGORIES`, ordered by item id (the roster order). `entered` counts the distinct live, non-removed registrations holding the item, computed for the whole list in one grouped query over the same join as D3. Program items have `max_qty` 1, so registrations and pieces agree.

`entered` is the roster's count, not `availability.item_taken`, which also counts rows the organizer took off the public table. This mirrors how a discipline's card figure `entered` differs from its `taken` (`public-entrants`, A count states who is shown above the line).

### D6. The card draws an item meter with the discipline meter

`CapacityMeter` takes an `OpenDiscipline` today but reads only `name`, `entered`, `capacity` and `queue_length`. Its prop narrows to that shape (a `Meter` type), the card maps disciplines and program meters through it, and a program meter passes `queue_length: 0`. The full / `plno` rendering and the track are therefore identical by construction. `TournamentCard` renders the disciplines' list when there are disciplines and the program meters' list otherwise; the two never both apply, since an event has no discipline and a tournament's `program_meters` is empty.

## Risks / Trade-offs

- [Removed row holding a capped seat] A meter can read `19/20` while the form says sold out, because a removed row still holds its piece. → Same as a discipline today; the owner accepted that split for disciplines, and the roster agrees with the meter.
- [Category list duplicated in the frontend] → A frontend test asserts the tab appears for each public category and not for afterparty and goods; the backend constant's comment points at the frontend copy.
- [Event later gains a discipline] Its card switches to discipline meters, its counts to seated fencers, and its program attendees drop out of the figures. → Intended: the kind is derived (`discipline-less-events`), and a tournament's figures are its disciplines'.

## Migration Plan

Additive API field, no schema migration. Deploy backend and frontend together as usual; an older frontend ignores `program_meters`.

## Open Questions

None. All points were decided by the owner on 2026-11-03.
