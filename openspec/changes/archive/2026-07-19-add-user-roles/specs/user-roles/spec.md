# user-roles Specification (delta)

## ADDED Requirements

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
The system SHALL provide an admin panel, accessible to Admins and the Owner, showing the account list with emails, display names, and roles; role controls (per the granting rules); and the pending plea queue. Fencer-facing and organizer-facing surfaces SHALL NOT expose the panel.

#### Scenario: Non-admin blocked
- **WHEN** an account below Admin requests the admin panel or its API
- **THEN** access is denied
