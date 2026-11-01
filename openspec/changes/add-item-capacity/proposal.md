## Why

Extra items carry no capacity, so a seminar for twenty, an afterparty in a small venue
or thirty printed shirts can be oversold, on a tournament as much as on an event. With
`add-events-without-disciplines` items become the whole offer of an event, and there the
gap matters most.

## What Changes

- Any extra item, in every category including `other_action`, may carry an optional
  capacity in Setup. Empty means unlimited, as today.
- Capacity counts pieces: a selection of two shirts takes two.
- A full item is sold out: it cannot be selected, and there is no queue. A place freed
  by a cancellation or an expiry is open to whoever comes first.
- The form states the places left. The last place is taken under a lock, so two
  simultaneous submissions cannot both have it.
- A fencer waiting in a discipline queue holds their items' places, unpaid, so admission
  can never meet a full item.
- A fencer amending keeps what they hold; only an increase needs room.
- Late-payment reinstatement also requires room on the items.
- Lowering a capacity below what is taken takes nothing from anybody.
- Organizer hand entry is not refused by a full item, and it counts.

## Capabilities

### New Capabilities
- `item-capacity`: an item's optional limit, what counts against it, what a full item
  means on the form, in an amendment and at reinstatement, and how it round-trips.

### Modified Capabilities

None. The rules are additive; no existing requirement changes its meaning.

## Impact

- `backend/app`: `models.py` (`ExtraItem.capacity`), `availability.py`,
  `routers/registrations.py`, `routers/tournaments.py`, `amendment.py`, `matching.py`,
  `schemas.py`, `export_json.py` (schema version raised), an Alembic migration.
- `frontend/src`: `setup/ExtraItemsSection.tsx`, `TournamentFace.tsx`, `TournamentDetail.tsx`,
  `api.ts`, the locale files.
- Apply after `add-discount-codes`, which moves the migration head and the export version
  and introduces the locking pattern this reuses. Independent of
  `add-events-without-disciplines`, though its sold-out event relies on this.
