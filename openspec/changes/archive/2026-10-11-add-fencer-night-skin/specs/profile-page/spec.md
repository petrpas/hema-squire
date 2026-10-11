## ADDED Requirements

### Requirement: The Profile page wears the night skin
The Profile page SHALL render in the night skin (`design-system`, Skins), for every account that opens it, organizer or fencer: a fencer reaches it from the account menu of a night screen, and the skin follows the route, not the role. Its form fields SHALL keep their 2px geometry and bottom-rule treatment, as every form does in either skin.

#### Scenario: A fencer opens the profile from the list
- **WHEN** a fencer selects My Profile from the account menu on the tournament list
- **THEN** the Profile page renders night, with no day paper visible

#### Scenario: An organizer opens the profile from the console
- **WHEN** an organizer selects My Profile from the account menu in a console
- **THEN** the Profile page renders night, and returning to the console renders it day
