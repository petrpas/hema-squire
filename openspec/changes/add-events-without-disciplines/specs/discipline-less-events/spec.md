## ADDED Requirements

### Requirement: An event is a tournament only once it has a discipline
Every record an organizer creates SHALL be an **event**, and an event SHALL be a **tournament** exactly while it has at least one discipline, individual or team. The kind SHALL be derived from the record's disciplines, SHALL NOT be stored, and SHALL NOT be chosen by anyone. Adding the first discipline SHALL make the record a tournament and removing the last SHALL make it an event, at any point in its life, with no other write. A discipline hidden by the team feature SHALL still count, since the kind reads contents and not features.

#### Scenario: A new record is an event
- **WHEN** an organizer creates a record and adds no discipline
- **THEN** it reads as an event

#### Scenario: First discipline makes a tournament
- **WHEN** the organizer adds a discipline to an event
- **THEN** it reads as a tournament everywhere, with nothing else written

#### Scenario: A team discipline counts
- **WHEN** a record has one team discipline and no individual discipline
- **THEN** it is a tournament

#### Scenario: A referenced discipline still cannot be removed
- **WHEN** the organizer removes the last discipline of a published tournament and a registration references it
- **THEN** the removal is refused and the record stays a tournament

#### Scenario: An unreferenced last discipline can be removed
- **WHEN** the organizer removes the last discipline of a published tournament and no registration references it
- **THEN** the removal succeeds and the record reads as an event

### Requirement: What a registration must carry follows the kind
On an event a registration SHALL carry at least one extra item. On a tournament a registration SHALL carry at least one discipline or team, and items alone SHALL be refused. A refused selection SHALL be refused the same way in a registration and in an amendment; a price preview SHALL go on pricing whatever is selected, as the form asks it on every change. An event with no items SHALL offer no `Register` tab, and a fencer SHALL find its description and nothing to register for.

A registration carrying only items, made while its record was an event, SHALL stay valid after a discipline is added. Such a registration SHALL keep its total and its payment window, and SHALL be amendable while it stays items-only.

#### Scenario: Items alone on an event
- **WHEN** a fencer submits one seminar on an event
- **THEN** a registration is created for that seminar

#### Scenario: Nothing selected on an event
- **WHEN** a fencer submits nothing on an event
- **THEN** the submission is refused and no registration exists

#### Scenario: Items alone on a tournament
- **WHEN** a fencer submits only an afterparty on a tournament
- **THEN** the submission is refused

#### Scenario: An announcement takes no registration
- **WHEN** a fencer opens an event with no items
- **THEN** no `Register` tab is offered

#### Scenario: A discipline added after an items-only registration
- **WHEN** an event holding an items-only registration gains its first discipline
- **THEN** that registration keeps its total, its window and its items, and its holder may amend its items without choosing a discipline

### Requirement: An items-only registration is priced and owed in full
An items-only registration — one holding items and neither a discipline placement nor a team — SHALL be priced from its items, through the same pricing evaluation as any registration, with discounts applied as configured. It SHALL NOT read as queued. It SHALL receive the ordinary confirmation mail with payment instructions, and with payments off the ordinary confirmation without them. A registration that waits in the queue SHALL still owe nothing for its items until it is admitted.

An items-only registration SHALL owe its whole total at registration and SHALL hold the ordinary payment window from that moment, whatever payment mode the record stores. No deposit SHALL be asked of it. When the window lapses unpaid it SHALL expire, including after seating has settled. The stored payment mode SHALL NOT be rewritten, and SHALL apply again to registrations carrying disciplines once the record is a tournament.

#### Scenario: Items are billed
- **WHEN** a fencer registers for a 500 Kč seminar on an event with payments on
- **THEN** the total is 500 Kč, the first mail carries payment instructions and says nothing of a queue, and the payment window is open

#### Scenario: Preview matches
- **WHEN** a preview is requested for items on an event and the same selection is then registered
- **THEN** the totals are equal in every configured currency

#### Scenario: A queued registration still owes nothing for its items
- **WHEN** a tournament registration holding one item waits wholly in the queue
- **THEN** its total is zero until it is admitted, as before

#### Scenario: Reservation mode stored on an event
- **WHEN** an event storing the `reservation` payment mode takes an items-only registration
- **THEN** the full total is owed within the ordinary payment window, not by a seating deadline

#### Scenario: Deposit mode stored on an event
- **WHEN** an event storing the `deposit` payment mode takes an items-only registration
- **THEN** no deposit is asked and the whole total is owed

#### Scenario: An unpaid registration expires
- **WHEN** an items-only registration's window lapses without payment
- **THEN** it expires and is not left reserved

### Requirement: An event omits what only disciplines give meaning
An event SHALL NOT offer the console's Queue phase, the Import phase, or hand entry of a fencer, and its public detail SHALL NOT offer the Entrants tab or state seat counts. A manual event SHALL publish with its external registration address like any manual record and SHALL NOT accept any registration through Squire. The console's Fencers, Payments and Export phases SHALL work for an event, with Export offering the fencer list and the item categories the event offers, and the summary and revenue tables counting items-only registrations.

#### Scenario: Phases on an event
- **WHEN** an organizer opens the console of an event
- **THEN** neither Queue nor Import is offered and no hand-entry control is shown

#### Scenario: Public detail of an event
- **WHEN** anyone opens the public detail of an event
- **THEN** no Entrants tab and no seat count is shown

#### Scenario: Items-only money in the exports
- **WHEN** an event holds a paid items-only registration
- **THEN** the fencer list, the item's table, the summary and the revenue table all state it, and the JSON export restores it

#### Scenario: Phases return with a discipline
- **WHEN** an event gains a discipline
- **THEN** the phases and tabs of a tournament are offered

### Requirement: The word follows the kind
Text about one particular record SHALL call it an event (`akce`) while it has no disciplines, and a tournament (`turnaj`) otherwise, in the UI and in mail, in Czech and in English, with the inflection and agreement correct in each. Text not about one particular record SHALL use the event term, since every tournament is an event: creating one, the organizer's list, the picker, and the admin tab and column. No system text on an event's pages or mail SHALL call it a tournament.

Identifiers SHALL NOT change: the `Tournament` model, routes, API paths and capability names keep their names, and none of them is shown to a reader.

#### Scenario: Czech agreement
- **WHEN** an organizer opens the `PUBLISH` tab of an unpublished event
- **THEN** it reads "Tato akce není zveřejněná", not a substituted noun in a tournament sentence

#### Scenario: Mail
- **WHEN** a paid registration on an event receives its confirmation
- **THEN** the mail speaks of the event and does not say "Uvidíme se na turnaji"

#### Scenario: Generic surfaces
- **WHEN** an organizer opens their list
- **THEN** the control reads "Založit akci" and the heading "Moje akce", and an individual tournament in it still reads as a tournament on its own page

#### Scenario: Word follows the discipline
- **WHEN** an organizer adds the first discipline and reopens `PUBLISH`
- **THEN** it reads "Tento turnaj není zveřejněný"
