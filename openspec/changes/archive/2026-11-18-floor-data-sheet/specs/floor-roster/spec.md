## MODIFIED Requirements

### Requirement: A team entry names its team and its members
A team entry SHALL state a key, the discipline's slug, the team's name, the person keys
of its current members in roster order, and whether it is paid. The team key is the
team's own identity, `team:<team id>`, and never its name. One registration may enter
two teams with the same name.

**Members' ratings.** For each member, in the same order, a team entry SHALL also state
the rating and rank that the member's replayed row states for the team discipline. The
office's team tab states the same figures. Where the row states none, the member's
figure is none.

Every member of a listed team SHALL appear among the roster's persons.

#### Scenario: Two teams of one name stay two teams
- **WHEN** one registration entered two teams both named "Ostrava" into one team discipline
- **THEN** the floor roster lists two team entries with distinct keys

#### Scenario: A member's rating travels with the team
- **WHEN** a team's second member is rated 1480 at rank 210 in the team discipline's category
- **THEN** the team entry states 1480 and 210 for its second member
