## MODIFIED Requirements

### Requirement: The floor roster names disciplines by id and states the tournament's day facts
Every discipline on the floor roster SHALL carry the discipline's stable id beside its
slug.

**Why the id.** A slug is editable until someone enters the discipline
(`discipline-identity`). Floor tables refer to a discipline by its id, so they survive a
slug edit made before anyone has entered.

**The weapon.** Every discipline on the floor roster SHALL also state its weapon, as the
office stores it. The floor compares weapons without regard to case. It uses the weapon
to offer a take-over only between disciplines of one weapon (`floor-setup`).

**Day facts.** The floor roster SHALL state the tournament's date and its timezone.

#### Scenario: A slug edit keeps the floor's format
- **WHEN** the organizer saves a format for "LS" and then renames the slug to "LSO" before anyone has entered
- **THEN** the floor roster states the discipline under "LSO" with the same id, and its format is still found

#### Scenario: The weapon is stated
- **WHEN** a tournament offers Longsword Open and Longsword Teams, both with the weapon "Longsword"
- **THEN** the floor roster states the weapon "Longsword" for both
