# tournament-admin Specification (delta)

## MODIFIED Requirements

### Requirement: In-app tournament creation
An account holding the global Organizer role or higher SHALL be able to create a tournament from the tournament picker via a minimal dialog asking display name and date. The slug SHALL be auto-derived from name and date and be editable before submission. The creator SHALL become the tournament's Tournament Owner and land in the console's Setup phase. Accounts below the Organizer role SHALL NOT be able to create tournaments.

#### Scenario: Create from picker
- **WHEN** an account with the Organizer role submits the "New tournament" dialog with a name and date
- **THEN** the tournament is created with the derived slug, the account becomes its Tournament Owner, and the console opens on the Setup phase

#### Scenario: Slug collision
- **WHEN** the derived slug is already taken
- **THEN** creation is rejected with a clear error and the user can edit the slug

#### Scenario: Fencer cannot create
- **WHEN** an account with only the Fencer role attempts to create a tournament
- **THEN** creation is rejected with an authorization error

### Requirement: Organizer authorization
Each tournament SHALL have exactly one Tournament Owner (initially the creator) and a team of Tournament Organizers. Console access SHALL be restricted to the Tournament Owner and team members. The Tournament Owner SHALL manage the team: adding any existing account by email (no global role required) and removing members. Team membership grants full console access; ownership additionally grants team management, ownership transfer, and delete/cancel.

#### Scenario: Unauthorized user
- **WHEN** a signed-in account that is neither the Tournament Owner nor a team member opens the tournament's console
- **THEN** access is denied

#### Scenario: Owner adds a team member
- **WHEN** the Tournament Owner adds a fencer's account to the team by email
- **THEN** that account gains full console access to the tournament without needing any global role

#### Scenario: Team member cannot manage the team
- **WHEN** a Tournament Organizer who is not the owner attempts to add or remove team members
- **THEN** the request is rejected with an authorization error

## ADDED Requirements

### Requirement: Tournament ownership transfer
The Tournament Owner SHALL be able to transfer ownership to a team member; on transfer the previous owner SHALL remain on the team. A global Admin SHALL be able to assign or reassign a tournament's owner as a fallback (for example when the owner's account is gone or the tournament has no owner).

#### Scenario: Owner hands over
- **WHEN** the Tournament Owner transfers ownership to a team member
- **THEN** that member becomes the Tournament Owner and the previous owner remains a Tournament Organizer

#### Scenario: Admin fallback
- **WHEN** a global Admin assigns a new owner to a tournament whose owner account is unavailable
- **THEN** the designated account becomes the Tournament Owner

### Requirement: Tournament deletion and cancellation
The Tournament Owner SHALL be able to hard-delete a tournament only while it has no registrations of any state. Once registrations exist, the owner SHALL instead be able to cancel the tournament: a cancelled tournament is hidden from public listings, rejects new registrations, and retains all data including financial history; its console remains accessible.

#### Scenario: Delete while empty
- **WHEN** the Tournament Owner deletes a tournament with no registrations
- **THEN** the tournament and its configuration are removed

#### Scenario: Delete blocked by registrations
- **WHEN** the Tournament Owner attempts to hard-delete a tournament that has registrations
- **THEN** deletion is rejected and cancellation is offered instead

#### Scenario: Cancelled tournament
- **WHEN** the Tournament Owner cancels a tournament with registrations
- **THEN** the tournament disappears from public listings, new registrations are rejected, and the console and all existing data remain accessible
