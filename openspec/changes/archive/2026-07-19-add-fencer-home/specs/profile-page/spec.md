## MODIFIED Requirements

### Requirement: Account menu
Every logged-in page SHALL show an account menu ("⋯") in the top-right corner containing: My Profile; Admin Panel (only for Admin and Owner); To Fencer (Fencer Home); To Organizer (tournament picker); and Logout. Account actions SHALL be consolidated in this menu.

#### Scenario: Menu navigation
- **WHEN** a logged-in user opens the account menu and selects My Profile
- **THEN** the Profile page opens, from any logged-in surface

#### Scenario: To Fencer opens Fencer Home
- **WHEN** a logged-in user selects To Fencer from the account menu
- **THEN** the Fencer Home page opens

#### Scenario: Admin entry hidden for fencers
- **WHEN** an account below Admin (and not Owner) opens the account menu
- **THEN** no Admin Panel entry is shown
