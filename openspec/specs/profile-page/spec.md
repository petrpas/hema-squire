# profile-page Specification

## Purpose
Provide a Profile page where every logged-in account can view and manage its account information, role and organizer plea status, and HEMA Ratings binding, reachable from every logged-in page via a shared account menu.

## Requirements

### Requirement: Profile page access
Every logged-in account SHALL have a Profile page presenting three sections: account information, role, and HEMA Ratings profile. The page SHALL be reachable from every logged-in surface via the account menu.

#### Scenario: Fencer opens profile
- **WHEN** any logged-in account selects My Profile from the account menu
- **THEN** the Profile page opens showing account information, role, and HEMA Ratings sections

### Requirement: Account information section
The account section SHALL display the account's email and full (display) name and SHALL allow editing them through the existing account-update contract, with changes audited per fencer-accounts.

#### Scenario: Rename
- **WHEN** the user edits the full name and saves
- **THEN** the account's display name is updated and the change is recorded in the profile audit trail

### Requirement: Role section
The role section SHALL display the account's effective role as one of Fencer, Organizer, Admin, or Owner. The deployment Owner (config-computed) SHALL be shown as Owner regardless of stored role. For accounts whose effective role is plain Fencer, the section SHALL embed the organizer plea flow: a request button with optional message, pending status, and denied status with re-plead, per the user-roles plea workflow.

#### Scenario: Owner sees Owner
- **WHEN** the account whose email equals the configured owner email opens the Profile page
- **THEN** the role section shows Owner

#### Scenario: Fencer pleads from profile
- **WHEN** a Fencer without a pending plea submits the organizer request from the role section
- **THEN** the plea is created and the section shows pending status

#### Scenario: Organizer sees no plea
- **WHEN** an account with Organizer role or higher opens the Profile page
- **THEN** the role section shows the role without any plea controls

### Requirement: HEMA Ratings section — bound state
WHEN the account is bound to a HEMA Ratings profile, the section SHALL display the HRID, HR canonical name, club, and nationality, and a link to the fighter's hemaratings.com profile page. No rebinding controls SHALL be offered (binding is write-once from the fencer's side per fencer-accounts).

#### Scenario: Bound profile shown with link
- **WHEN** an account with a bound hr_id opens the Profile page
- **THEN** the HEMA Ratings section shows HRID, name, club, nationality, and a working link to the hemaratings.com profile

### Requirement: HEMA Ratings section — find and match
WHEN the account has no bound HR profile, the section SHALL offer a find-and-match flow: the user first narrows by nationality, then searches by name; candidates are listed with HRID, name, club, and nationality, ranked by name similarity. Confirming a candidate SHALL bind it through the existing binding contract (one account per hr_id; audited).

#### Scenario: Find, match, bind
- **WHEN** an unbound user picks a nationality, enters a name, and confirms one of the listed candidates
- **THEN** the account stores that hr_id with the HR canonical name, club, and nationality, and the section switches to the bound state

#### Scenario: Candidate already bound elsewhere
- **WHEN** the user confirms a candidate whose hr_id is already bound to another account
- **THEN** the binding is rejected and the section explains the conflict

### Requirement: Account menu
Every logged-in page SHALL show an account menu ("⋯") in the top-right corner containing: My Profile; Admin Panel (only for Admin and Owner); To Fencer (fencer landing — placeholder until that page exists); To Organizer (tournament picker); and Logout. Account actions SHALL be consolidated in this menu.

#### Scenario: Menu navigation
- **WHEN** a logged-in user opens the account menu and selects My Profile
- **THEN** the Profile page opens, from any logged-in surface

#### Scenario: Admin entry hidden for fencers
- **WHEN** an account below Admin (and not Owner) opens the account menu
- **THEN** no Admin Panel entry is shown

### Requirement: Bootstrap owner account
The deployment bootstrap SHALL create the account petr.pascenko@gmail.com (Petr Paščenko) with the Organizer role and the configured password, and the dev environment SHALL set the owner email configuration to petr.pascenko@gmail.com, making the account the deployment Owner with Organizer and inherent Fencer capabilities. Seeding SHALL be idempotent.

#### Scenario: Owner logs in
- **WHEN** petr.pascenko@gmail.com logs in with the seeded password in the dev environment
- **THEN** the Profile page role section shows Owner and tournament creation is available
