## MODIFIED Requirements

### Requirement: Communication language vs UI language
Emails to fencers SHALL use the tournament's communication language. The console and fencer-facing UI language SHALL follow the user's preference.

The tournament's communication language SHALL be fixed when the tournament is created and SHALL NOT be exposed as an editable setting in the console. It remains a stored property of the tournament, read by every email path exactly as before; it is simply not something the organizer changes after the fact.

#### Scenario: Czech tournament, foreign organizer
- **WHEN** a tournament is configured with Czech communication and an organizer prefers another UI language
- **THEN** fencers receive Czech emails while the organizer's console renders in their preferred language once available

#### Scenario: Communication language not editable
- **WHEN** the organizer looks for the communication language in the console
- **THEN** no screen offers it for editing, and the language assigned at creation continues to govern every email the tournament sends
