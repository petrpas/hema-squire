## Why

Squire can only publish something that has at least one discipline, so an organizer
cannot use it for a seminar, a sparring day or an afterparty that stands on its own.
The name is wrong for the same reason: everything is called a tournament, though
nothing competitive happens at such an event.

## What Changes

- **An event is the umbrella term, and a tournament is an event with at least one
  discipline.** The kind is derived from the event's disciplines and is not stored,
  so adding the first discipline makes it a tournament and removing the last makes it
  an event.
- Setup completeness no longer requires a discipline. An event with no disciplines
  publishes on the same terms otherwise; with no items it is a plain announcement.
- A fencer can register for an event's items alone, priced and paid as usual. Items
  alone remain refused on a tournament, as they are today.
- A registration of items alone is not a queued registration: it owes its total, gets
  payment instructions and a payment window, and expires when unpaid.
- An event owes in full at registration whatever payment mode is stored, since a
  deposit and a seating deadline exist to hold a seat and an event has none. Deposit
  amount and bank feed are not required on it.
- An event has no Queue phase, no entrant rosters and no public seat counts. Hand entry
  and the table import are not offered on it; a manual event only points at its
  external registration address.
- Copy says "event" (`akce`) on anything with no disciplines, and on every surface not
  about one particular record: "Založit akci", "Moje akce", "Nová akce", the admin tab
  `Akce`. Mails follow the same rule.
- **BREAKING (spec)** A published tournament whose last discipline is unreferenced may
  now lose it and become an event; completeness used to refuse that.

## Capabilities

### New Capabilities
- `discipline-less-events`: what makes something an event or a tournament, what each
  may be registered for, how an items-only registration is priced and paid, what an
  event's console and public page omit, and which word every surface uses.

### Modified Capabilities
- `tournament-admin`: Setup completeness stops requiring a discipline, and stops
  requiring the deposit items on an event.

## Impact

- `backend/app`: `setup.py` (completeness), `pricing.py` (the zero-total guard),
  `models.py` (`fully_queued`, a new items-only predicate), `routers/registrations.py`
  (selection guards, window), `scheduler.py` (lapse), `amendment.py`, `emails.py`,
  `locales/`.
- `frontend/src`: `Console.tsx` (phases), `TournamentDetail.tsx`, `TournamentFace.tsx`,
  the Setup sections, `i18n/cs.json` and `en.json`.
- No schema migration and no export schema bump: the kind is derived.
- Identifiers stay: `Tournament`, `/t/:slug`, the API paths and spec capability names.
- Overlaps `add-discount-codes`, which is being implemented in the working tree, in
  `pricing.py` and `settled`. Apply this change after that one lands.
