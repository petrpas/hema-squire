## MODIFIED Requirements

### Requirement: One dormancy predicate governs the lifecycle passes
Whether Squire runs its lifecycle clocks against a registration SHALL be settled by a single predicate over the tournament and the registration, and every lifecycle pass SHALL consult that predicate and no other condition of its own. The passes so governed are the reminder pass, the expiry pass, the demotion carried out at seating settlement, and the count of pending demotions the console states before the organizer confirms one.

The predicate SHALL yield the **cause** of dormancy rather than a bare yes or no, drawn from a closed set of reasons, so that why a registration is not moving is readable rather than inferred. The causes SHALL be:

- the tournament is **unpublished**, so it is a tournament being written and holds nobody for a clock to run against (`tournament-publication`);
- the tournament's **payments feature is off**, so no money was ever requested;
- the registration was **issued from an imported row**, so its clocks are dormant by origin.

A cause SHALL be read from the tournament wherever it is a live setting, so that changing that setting takes effect at once and no stale copy governs a pass. A cause SHALL be stored only where it records an origin that cannot be recomputed from the registration's present contents.

**The selection of tournaments a pass considers SHALL exclude unpublished tournaments**, as it already excludes those a tournament's organizer keeps the roster for. The exclusion and the cause are both stated deliberately, and neither replaces the other: the exclusion means no pass ever reaches such a tournament, and the cause means the paths a person triggers by hand — the count the console states, the settlement an organizer asks for — answer alike. That is the difference between a guarantee and a guard, and the guarantee is what makes the property true of a registration created by any path, including one that neglects to mark it dormant.

Adding a further reason to leave a registration alone SHALL be an addition to this predicate and SHALL NOT be a condition placed in any pass.

#### Scenario: Every pass agrees
- **WHEN** a registration is dormant for any cause and the lifecycle runs
- **THEN** it receives no reminder, does not expire, is not demoted at settlement, and is not counted among the pending demotions

#### Scenario: The count and the settlement select alike
- **WHEN** the console states how many registrations settling seating would demote, and the organizer then settles
- **THEN** the registrations demoted are exactly those counted, with no registration counted that settlement leaves alone

#### Scenario: A live cause is read live
- **WHEN** a tournament's payments feature is turned on
- **THEN** its registrations cease to be dormant for that cause from that moment, without any registration being rewritten

#### Scenario: The cause is stated
- **WHEN** a registration is dormant
- **THEN** which of the reasons made it dormant is available, rather than only the fact that it is

#### Scenario: A draft is not among the tournaments a pass considers
- **WHEN** the lifecycle pass selects the tournaments it will run against
- **THEN** no unpublished tournament is among them

#### Scenario: Publication starts the clocks
- **WHEN** a tournament is published
- **THEN** its registrations cease to be dormant for that cause from that moment, without any registration being rewritten
