## Context

`Tournament` is the one record for anything organized. Four things assume it has
disciplines:

- `setup_missing` reports `MISSING_DISCIPLINES` (`setup.py:109`), which blocks
  publication and, through `guard_published_completeness`, deleting the last discipline.
- Registering and amending refuse a selection with no discipline and no team
  (`routers/registrations.py:493`, `:777`).
- `pricing.selection_total` returns 0 for no disciplines and no teams, and the
  discount-code breakdown repeats that guard. That is deliberate: a fully queued
  registration owes nothing, extras included, until it is admitted.
- `Registration.fully_queued` is vacuously true of a registration with no entries and no
  teams (`models.py`, `fully_queued`). The first mail, the window, the reminder and the lapse all
  read it, so an items-only registration would be told it is queued and asked for nothing.

Extra items carry no capacity. The word "turnaj" is in about 105 strings of `cs.json` and
5 of the mail locale; Czech inflects both the noun and whatever agrees with it.

## Goals / Non-Goals

**Goals:**
- An organizer can publish an event with no disciplines and sell its items through the
  ordinary registration and payment path.
- No tournament changes behaviour.
- One predicate decides the kind, so no surface can disagree with another.

**Non-Goals:**
- Capacity on extra items, which `add-item-capacity` adds for events and tournaments
  alike, as sold out with no queue.
- Hand entry and table import of items.
- Items-only registration on a tournament.
- A public participant list for an event.
- Renaming `Tournament`, routes, API paths or capabilities.

## Decisions

### D1. The kind is derived from disciplines, never stored

`Tournament.is_event` is `not self.disciplines`, exposed on `TournamentOut`. The frontend
reads that field and does not recount. Team disciplines count: a team-only record is a
tournament, because the owner's rule is "at least one discipline".

**Alternative rejected:** an organizer-chosen type. It could contradict the disciplines,
and every guard would have to say which wins.

### D2. The tournament's kind gates new selections; the registration's content gates pricing

Two questions look alike and have different answers once a published event gains a
discipline.

- *May this selection be submitted?* On an event, it needs at least one item. On a
  tournament, a discipline or team, unchanged. This reads `is_event`.
- *Do this registration's items stand alone?* `Registration.items_only` is true when it
  has no entries and no teams, and has extra selections. This reads the row, so a
  registration made while the record was an event keeps its total and its window after
  the first discipline is added. Reprice, window, lapse and mail read this.

An amendment to an `items_only` registration may stay items-only on a tournament, so that
adding a discipline never strands somebody who has paid for a seminar.

The refusal stays one code on the wire, renamed `nothing_selected` because the old
`no_disciplines_or_teams` is untrue on an event. The form gates its submit button on the same
rule.

### D3. `selection_total` gains an explicit `items_stand_alone`

The guard becomes `if not disciplines and not team_disciplines and not items_stand_alone`.
`reprice` passes `registration.items_only`; registration and the preview pass
`tournament.is_event`. An explicit parameter keeps the function pure, which the discount
code design also relies on.

**Alternative rejected:** dropping the guard. A queued registration would be billed its
extras before admission.

### D4. `fully_queued` stops being vacuous about items

Empty registrations stay vacuously queued as today; only a registration holding items
answers false. `waiting_in_queue` and its SQL twin need no change, as both already require
a placement. This one change fixes the first mail, `expires_at`, the reminder filter and
the second-amendment path together.

### D5. An items-only registration pays as `immediate`, whatever mode is stored

`reservation` holds a seat until the seating deadline; `deposit` holds it on a flat
deposit. Both exist for seats, and the seating moment is settled from the Queue phase,
which an event has not got. Left alone, an event in `reservation` mode would never open a
window. So an `items_only` registration opens the ordinary window at registration and owes
its whole total. The stored mode is not rewritten: it applies again once a discipline
makes the record a tournament, which is also why the mode stays editable.

`setup.owing_mode` is the one answer, and every reader of `payment_mode` that asks about a
registration reads it. `setup_missing` skips
`deposit_amount` and `payment_feed` while `is_event`.

The lapse branch in `scheduler.py:176` also needs it: past `settled_seating` it demotes
rather than expires, and an items-only registration has nothing to demote, so it would
sit reserved forever. `items_only` takes the ordinary expiry path.

### D6. Word choice is i18next context, not interpolation

`{{noun}}` cannot work: "tento turnaj je zveřejněný" / "tato akce je zveřejněná". `{{noun}}` cannot work: "tento turnaj je zveřejněný" / "tato akce je zveřejněná". A string
that can appear on an event gets a `_event` variant. `EventWording` wraps a record's pages in
an `I18nextProvider` holding a clone of the instance whose `t` passes `context: "event"`, so
no call site changes and a component owning the record reads the same clone through
`wordingI18n`. i18next falls back to the base key, so strings that only exist beside
disciplines (teams, rosters, substitutes, the queue) stay untouched.

Strings not about one record have no record to ask, so they change outright to the
umbrella term (`Založit akci`, `Moje akce`, admin `Akce`). English uses "event" in the same
places. The backend `t()` takes the same variant by a helper around the mail keys.

`table.action: "Akce"` (a console column) and the item category `other_action: "Jiná akce"`
keep their meaning. The second reads oddly next to the new term in Setup, and stays
because it only appears in the item editor.

### D7. An event hides what has no meaning, and its console stays otherwise whole

`phasesFor` drops Queue when `is_event`; Import is dropped on an event too, along with the
hand-entry control. Fencers, Payments and Export stay: Export's band is the fencer list and
item categories, and the discipline tabs are already derived. The detail page omits the
Entrants tab, whose rosters are of disciplines.

## Risks / Trade-offs

- [A missed string says "turnaj" on an event] → Cosmetic and easily fixed. Task 6.3 scans
  the rendered event pages for the word.
- [A reader of `entries` assumes non-empty] → Item-only rows are new to Souhrn, Příjmy, the
  export and the JSON round trip; each gets a test in task 5.
- [Adding a discipline changes the word on a live event's public page] → Intended by the
  owner's rule. Adding one to a published event is held to completeness like any save.
- [A published tournament can lose its last discipline] → Only when no registration
  references it, since `discipline_referenced` still refuses otherwise.
- [Items oversell until `add-item-capacity` lands] → Apply that change first or alongside.
