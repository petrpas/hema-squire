# user-roles Specification

## Purpose
Define the global authorization model: the role ladder (Owner, Admin, Organizer, Fencer), how roles are granted and revoked, the Organizer plea workflow, and the admin panel surface.

## Requirements

### Requirement: Global role model
Every account SHALL hold exactly one global role from the ladder: Fencer (default for every account), Organizer, Admin. Capabilities SHALL be rank-based: creating tournaments requires the Organizer role or higher; managing roles and pleas requires the Admin role or higher. Every account, regardless of role, SHALL retain all Fencer capabilities (registering for open tournaments); the roles are not mutually exclusive with fencing.

#### Scenario: Fencer cannot create a tournament
- **WHEN** an account with the Fencer role attempts to create a tournament
- **THEN** the request is rejected with an authorization error

#### Scenario: Admin retains fencer capabilities
- **WHEN** an account with the Admin role registers for an open tournament
- **THEN** the registration proceeds exactly as for any fencer

### Requirement: Deployment Owner from configuration
The account whose email equals the configured owner email SHALL be the deployment Owner: it holds all capabilities, including granting and revoking the Admin role, and its authority SHALL NOT be revocable in-app. The Owner designation SHALL be computed from configuration, not stored, so it applies even when the account is created after deployment. The system SHALL log a startup warning when no account matches the configured owner email.

#### Scenario: Owner grants admin
- **WHEN** the Owner sets an account's role to Admin
- **THEN** that account gains Admin capabilities immediately

#### Scenario: Admin cannot grant admin
- **WHEN** an Admin (not the Owner) attempts to set an account's role to Admin
- **THEN** the request is rejected with an authorization error

### Requirement: Organizer role granting and revocation
An Admin SHALL be able to grant and revoke the Organizer role. Revocation SHALL only remove the ability to create new tournaments: existing tournament ownership and team memberships SHALL remain untouched.

#### Scenario: Revoked organizer keeps a live tournament
- **WHEN** an Admin revokes the Organizer role from an account that owns a tournament
- **THEN** the account can no longer create tournaments but retains full console access to and ownership of its existing tournament

### Requirement: Organizer plea workflow
Any account SHALL be able to request the Organizer role with an optional message. An account SHALL have at most one pending plea; a denied account MAY plead again. Admins SHALL see the queue of pending pleas and grant or deny each; granting sets the account's role to Organizer. Plea history SHALL be retained.

#### Scenario: Plea granted
- **WHEN** an Admin grants a pending plea
- **THEN** the pleading account holds the Organizer role and the plea is recorded as granted with the deciding admin

#### Scenario: Duplicate plea rejected
- **WHEN** an account with a pending plea submits another plea
- **THEN** the second plea is rejected

### Requirement: Admin panel
The system SHALL provide an admin panel, accessible to Admins and the Owner. Fencer-facing and organizer-facing surfaces SHALL NOT expose the panel.

The panel SHALL be divided into three tabs, in this order: **pending tasks**, **people** and **tournaments**. Exactly one tab SHALL be shown at a time. The panel SHALL open on the pending-tasks tab. The pending-tasks tab label SHALL carry the number of open items.

The **pending-tasks** tab SHALL list what waits on an admin's decision:
- the queue of pending organizer pleas, with grant and deny controls (per the plea workflow);
- every HR ID bound by more than one account, each listed with the accounts holding it and an unbind control per account.

A group of tasks that has nothing open SHALL collapse to its heading with a line saying so. An item SHALL leave the tab as soon as it is resolved: a plea when it is decided, a shared HR ID when no more than one account still holds it.

The **people** tab SHALL list every fencer record, accounts and records an organizer enrolled without an address alike, with its email (where it has one), display name, role, HR ID and creation date, and SHALL carry the role controls (per the granting rules) and the HR unbind control.

The **tournaments** tab SHALL list every tournament, drafts and cancelled ones included. Each row SHALL show the tournament's name, date, owner, state (draft, published or cancelled) and number of registrations, together with the delete control fixed by `tournament-admin`.

The people and tournaments tabs SHALL each offer a search field and sortable columns:
- People SHALL be searchable by display name, email and HR ID. Tournaments SHALL be searchable by name, slug and owner (display name or email). The search SHALL ignore case and diacritics. A name (person's, tournament's or owner's) SHALL match the way roster search matches one: every typed word starts some word of the name, in any order. An email, slug or HR ID SHALL match on any substring.
- Every column that states a value SHALL be sortable, in either direction. Selecting the column already sorted SHALL reverse its direction. The active column and direction SHALL be shown in the header.
- People SHALL first be sorted by display name, ascending. Tournaments SHALL first be sorted by date, newest first.
- A search that matches nothing SHALL say so in place of the rows.

#### Scenario: Non-admin blocked
- **WHEN** an account below Admin requests the admin panel or its API
- **THEN** access is denied

#### Scenario: Panel opens on pending tasks
- **WHEN** an Admin opens the admin panel while two pleas are pending
- **THEN** the pending-tasks tab is shown and its label carries the count of open items

#### Scenario: Shared HR ID listed as a task
- **WHEN** two accounts are bound to the same HR ID
- **THEN** the pending-tasks tab lists that HR ID with both accounts, each with an unbind control

#### Scenario: Shared HR ID resolved by unbinding
- **WHEN** an Admin unbinds one of the two accounts sharing an HR ID
- **THEN** that HR ID leaves the pending-tasks tab and the open-item count drops by one

#### Scenario: Searching people ignores diacritics
- **WHEN** an Admin types `novacek` into the people search
- **THEN** an account named `Nováček` is listed and accounts matching neither name, email nor HR ID are not

#### Scenario: Reversing a sort
- **WHEN** an Admin selects the creation-date column on the people tab twice
- **THEN** the accounts are first ordered oldest first and then newest first, and the header shows the direction

#### Scenario: Tournaments list includes drafts and cancelled
- **WHEN** an Admin opens the tournaments tab
- **THEN** draft, published and cancelled tournaments are all listed, each with its state and registration count
