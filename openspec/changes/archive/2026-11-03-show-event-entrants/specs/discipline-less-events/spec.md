## MODIFIED Requirements

### Requirement: An event omits what only disciplines give meaning
An event SHALL NOT offer the console's Queue phase, the Import phase, or hand entry of a fencer, and its public detail SHALL NOT state seat counts or show a disciplines section, which on an event would be empty. A manual event SHALL publish with its external registration address like any manual record and SHALL NOT accept any registration through Squire. The console's Fencers, Payments and Export phases SHALL work for an event, with Export offering the fencer list and the item categories the event offers, and the summary and revenue tables counting items-only registrations.

An event's public detail SHALL offer the Entrants tab exactly when the event offers at least one item that has a public roster (`public-entrants`, Side events have rosters, the afterparty does not), whether or not anyone holds a place at it yet. The tab SHALL then list those rosters and nothing else. An event offering no such item SHALL NOT offer the tab, since it would have nothing to list.

#### Scenario: Phases on an event
- **WHEN** an organizer opens the console of an event
- **THEN** neither Queue nor Import is offered and no hand-entry control is shown

#### Scenario: Public detail of an event
- **WHEN** anyone opens the public detail of an event offering only an afterparty and a T-shirt
- **THEN** no Entrants tab, no seat count and no disciplines section is shown

#### Scenario: Public detail of an event with a seminar
- **WHEN** anyone opens the public detail of an event offering a seminar and an afterparty
- **THEN** the Entrants tab is offered and lists the seminar's roster alone

#### Scenario: A seminar nobody has taken yet
- **WHEN** anyone opens the public detail of an event whose only seminar has no entrant
- **THEN** the Entrants tab is offered and the seminar's roster states that nobody is entered yet

#### Scenario: Items-only money in the exports
- **WHEN** an event holds a paid items-only registration
- **THEN** the fencer list, the item's table, the summary and the revenue table all state it, and the JSON export restores it

#### Scenario: Phases return with a discipline
- **WHEN** an event gains a discipline
- **THEN** the phases and tabs of a tournament are offered
