## Context

A discipline's capacity is counted by `taken_seats` over `live_registration()`, and an
overflow goes to the queue, so a race on the last seat costs nothing. A refusal has no such
cushion. `add-discount-codes` D3 solves the same problem for a code's limit by updating the
code's row first, which takes the write lock on SQLite and the row lock on PostgreSQL.

`RegistrationExtra` holds `qty`. Queued registrations keep their selections but are billed
nothing for them until admitted.

## Goals / Non-Goals

**Goals:**
- A limit that holds under concurrent registration.
- Admission from the queue and an amendment never fail because of an item the fencer
  already holds.

**Non-Goals:**
- A queue for items.
- Capacity shared between items, or per option (shirt sizes).
- Notifying anyone that a place freed.

## Decisions

### D1. `ExtraItem.capacity` is a nullable integer

NULL is unlimited. `item_taken(session, item)` sums `qty` over `live_registration()`, in
`availability.py` beside its discipline twin, so a lapsed reservation frees its pieces in the
same moment a seat is freed.

### D2. A queued registration counts

`live_registration()` already includes it, and the owner chose that: admission then never
meets a full item, and no branch drops an item, reprices and mails on promotion. The cost
is that unpaid substitutes can block paying fencers.

### D3. Full means refused, per item, with a code naming the items

`item_sold_out` with the item ids, which the form turns into names. The whole submission is refused, so the fencer decides what
to do; unlike disciplines there is no placement to fall back on. The form disables full rows
from the availability payload, and the refusal covers the race.

### D4. Check before writing, claim after

The submission first checks for room while nothing is written, which spares a variable
symbol. The check that holds under a race comes after the flush, as `discount_codes.claim`
has it: touching the capped items' rows in id order takes the lock, so two submissions
cannot deadlock, and the count then includes the registration itself. It cannot come
earlier, because `next_vs` commits and would release the lock. Refusing rolls back.
Uncapped and unraised items take no lock, so a tournament not using capacity behaves
exactly as before.

### D5. Amendment needs room only for an increase

The check compares the wanted quantity with the quantity held. A fencer over a capacity
lowered later keeps what they hold, and may not raise it.

### D6. Reinstatement extends `seats_free`

Grace reinstatement asks for room on held items too, counted without the registration
itself, as it is expired. Otherwise it takes the path a taken seat takes today, flagged for
the organizer.

### D7. The organizer's own entry is not refused

Hand entry and issuing state what already happened, so they count and may overrun. The Setup
item editor shows taken against capacity, so the overrun is visible.

## Risks / Trade-offs

- [Substitutes block paying fencers] → Accepted by the owner; taken/capacity is visible to
  the organizer, who can cancel a substitute.
- [Lock wait on a very popular item] → Serialised only for capped items, held for one short
  transaction.
- [A hidden feature] → With extra services off, the limit still applies, as `tournament-features`
  says of every hidden setting.

## Migration Plan

An additive nullable column with no backfill; every existing item stays unlimited. Export
schema version is raised; older documents load with no capacity.
