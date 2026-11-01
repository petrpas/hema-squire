## MODIFIED Requirements

### Requirement: Tournament deletion and cancellation
The Tournament Owner SHALL be able to hard-delete a tournament only while it has no registrations of any state. Once registrations exist, the owner SHALL instead be able to cancel the tournament. A cancelled tournament is hidden from public listings, rejects new registrations, and retains all data including financial history; its console remains accessible.

A global Admin SHALL be able to hard-delete any tournament from the admin panel, whatever its state (draft, published or cancelled) and whether or not the Admin is on its team. A tournament with no registrations SHALL be deleted at the Admin's single action, as the owner's delete is. A tournament with registrations of any state SHALL be deleted only after explicit confirmation. The confirmation SHALL state the number of registrations and the amount live-credited to them in each currency it was credited in, and SHALL say that an organizer's real event is cancelled rather than deleted. The server SHALL refuse a delete of a tournament with registrations that does not carry the confirmation, so the guard does not rest on the client alone. The count SHALL be read at the moment of deletion: a delete sent without confirmation for a tournament that was empty when listed SHALL be refused if a registration arrived in between.

An Admin's delete SHALL remove the tournament and everything recorded under it, in one transaction: its configuration, its registrations with their disciplines, extras and teams, its payment history (events, credits, waivers, manual payments, bank transactions), its imports, rules and journal, its manual rows and row numbers, its operations, and its organizer team. Accounts SHALL NOT be removed: a person registered for or organizing the tournament keeps their account. The delete SHALL send no mail. Mail already queued in the outbox SHALL be left to go out, since a message records nothing that the deleted tournament still needs.

#### Scenario: Delete while empty
- **WHEN** the Tournament Owner deletes a tournament with no registrations
- **THEN** the tournament and its configuration are removed

#### Scenario: Delete blocked by registrations
- **WHEN** the Tournament Owner attempts to hard-delete a tournament that has registrations
- **THEN** deletion is rejected and cancellation is offered instead

#### Scenario: Cancelled tournament
- **WHEN** the Tournament Owner cancels a tournament with registrations
- **THEN** the tournament disappears from public listings, new registrations are rejected, and the console and all existing data remain accessible

#### Scenario: Admin deletes an empty tournament
- **WHEN** an Admin who is not on the team deletes a draft tournament with no registrations
- **THEN** the tournament is removed without a confirmation step

#### Scenario: Admin delete of a tournament with registrations asks first
- **WHEN** an Admin chooses delete on a tournament with 12 registrations, 3 800 CZK of it credited
- **THEN** a confirmation dialog states the 12 registrations and the credited 3 800 CZK, and nothing is deleted until the Admin confirms

#### Scenario: Confirmed admin delete removes everything under the tournament
- **WHEN** an Admin confirms the delete of a tournament with registrations, payments and imports
- **THEN** no row referring to that tournament or to any of its registrations remains, and every fencer and organizer account still exists

#### Scenario: Unconfirmed delete refused on the server
- **WHEN** an Admin's delete request without confirmation reaches a tournament that has registrations
- **THEN** the request is refused with `has_registrations` and nothing is deleted

#### Scenario: Admin delete sends no mail
- **WHEN** an Admin deletes a tournament with registrations
- **THEN** no message is queued to its registered fencers or its organizers
