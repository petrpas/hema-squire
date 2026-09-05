# external-registration Specification

## Purpose
Define where a tournament's registration lives when Squire does not hold it:
the address it records, what requires that address, how every surface that
would offer a fencer a registration form sends them there instead, and what a
participant list means when Squire maintains neither the roster nor a payment
state behind it.

Squire links out and knows nothing more. It never fetches the address, never
checks that it resolves and never reports it as dead: what it points at is not
Squire's to know, and a check made when the organizer saves proves nothing about
the moment a fencer follows it.
## Requirements
### Requirement: A tournament records where its registration is held
A tournament SHALL be able to record the address of the registration held for it outside Squire, as a single optional web address. It SHALL be validated as an absolute `http` or `https` address and SHALL otherwise be stored as given.

Squire SHALL NOT fetch the address, SHALL NOT check that it resolves, and SHALL NOT report it as unreachable. What the address points at is not Squire's to know; a check made when the organizer saves proves nothing about the moment a fencer follows it.

The address SHALL be a single value rather than a list or a labelled set of links. Where an organizer needs to say more about how their registration works, the tournament description already carries prose with links, as fixed by `organizer-prose`.

The address SHALL be offered on every tournament and SHALL be mandatory only where the organizer keeps the registrations, as fixed by `tournament-admin`.

#### Scenario: Address recorded
- **WHEN** the organizer records an external registration address on a tournament
- **THEN** it is stored and presented wherever the tournament sends a fencer to register

#### Scenario: A malformed address is refused
- **WHEN** the organizer submits an address that is not an absolute web address
- **THEN** the save is rejected with a validation error on that field and nothing is stored

#### Scenario: An unreachable address is not the system's business
- **WHEN** the recorded address points at a page that does not exist
- **THEN** the save succeeds, no warning is raised, and Squire keeps presenting it

### Requirement: The public surfaces send the fencer where the registration is
WHEN a tournament's registrations are kept by the organizer, every surface that would offer a fencer a way to register SHALL instead offer a way to reach where the registration is held. It SHALL be offered in the place the registration action occupies, and SHALL NOT be offered beside one: a Register action that explains itself when pressed is a promise the tournament cannot keep.

Every such surface SHALL state that registration is held elsewhere. None SHALL state that registration is closed, is not yet open, or has ended, since no window ever existed on this tournament and each of those is a false account of why the fencer cannot register here.

WHERE such a tournament records no address, the surface SHALL state that registration is held elsewhere and SHALL offer no action, rather than offering one that leads nowhere. This is a state a published tournament SHALL NOT be in, the address being mandatory for publication, but a draft may be.

The link leads away from Squire on a page that is otherwise entirely Squire's, so it SHALL be presented as a destination that is visibly not part of this site, within the design system's own means.

#### Scenario: The detail page offers the way out
- **WHEN** a fencer opens the detail page of a published tournament whose registrations the organizer keeps
- **THEN** the registration tab offers a way to reach the external registration and offers no registration form

#### Scenario: No false account of why
- **WHEN** that tournament's registration-closes date has passed
- **THEN** the surface still states that registration is held elsewhere and does not state that registration has closed

#### Scenario: An unpublished tournament with no address
- **WHEN** an organizer previews a draft organizer-kept tournament with no address recorded
- **THEN** the surface states that registration is held elsewhere and offers no action

### Requirement: A participant list Squire does not maintain says so
WHERE the roster shown publicly is one Squire does not maintain — the organizer keeps the registrations and the entrants reached Squire by import — the participant list SHALL state the moment the roster last reached it.

The statement SHALL be a fact about when, and SHALL NOT be a judgement about currency: it SHALL NOT claim the list is up to date and SHALL NOT warn that it may be stale. Both are assessments Squire cannot make, and the second would be wrong the moment the organizer imports again.

What such a list shows about payment is fixed by `registration`'s **Public participant list**: entrants plainly, with no confirmed or unconfirmed distinction, because no payment state stands behind one.

#### Scenario: The list dates itself
- **WHEN** a visitor views the participant list of an organizer-kept tournament whose roster was last imported four days ago
- **THEN** the list states that it stands as of that moment

#### Scenario: No judgement is offered
- **WHEN** the roster was last imported three months ago
- **THEN** the list states that moment and does not warn that it may be out of date

#### Scenario: A fresh import moves the moment
- **WHEN** the organizer imports an updated roster
- **THEN** the stated moment becomes the new one

