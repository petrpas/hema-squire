## MODIFIED Requirements

### Requirement: Organizer-triggered seating settlement
The organizer SHALL be able to settle seating from the console before the seating deadline arrives — closing seating early once the roster is as they want it. It SHALL do exactly what the deadline does: demote every registration still owing money to the substitute queue, and place every subsequent registration in the queue rather than a seat.

A registration whose lifecycle clocks are dormant SHALL NOT be demoted, by the deadline or by the organizer, as fixed by `registration`'s **One dormancy predicate governs the lifecycle passes**. The two triggers SHALL leave the same registrations alone, since they are one operation reached two ways.

It SHALL be available in every payment mode. In immediate mode it demotes nobody but still closes seating. Where every registration is dormant it likewise demotes nobody and still closes seating.

The count the console states before firing SHALL be the set the settlement then moves. The two SHALL be one selection, so that a confirmation SHALL NOT promise a demotion that settlement will not carry out.

It SHALL be refused on a tournament whose seating has already settled, so settlement happens once however it is triggered.

It SHALL NOT be reversible, and the console SHALL confirm before firing it, stating how many registrations will be demoted. The organizer's route to correct an individual case afterwards is promotion.

#### Scenario: Organizer settles early
- **WHEN** the organizer settles seating a week before the seating deadline
- **THEN** every registration still owing money is demoted to the queue, and the tournament is recorded as settled

#### Scenario: Confirmation states the effect
- **WHEN** the organizer opens the settle action on a tournament with eleven unpaid seated registrations
- **THEN** the confirmation states that eleven registrations will be moved to the queue and that the action cannot be undone

#### Scenario: The count excludes what settlement will not move
- **WHEN** the organizer opens the settle action on a tournament holding four unpaid seated registrations and six dormant ones
- **THEN** the confirmation states four, and settling then demotes exactly those four

#### Scenario: Settling twice refused
- **WHEN** the organizer attempts to settle a tournament whose seating has already settled
- **THEN** the action is refused and nothing changes

#### Scenario: Scheduled settlement does not follow a manual one
- **WHEN** the seating deadline passes on a tournament the organizer already settled by hand
- **THEN** no registration is demoted a second time, including any the organizer promoted in between

#### Scenario: Settling in immediate mode
- **WHEN** the organizer settles seating on an immediate-mode tournament
- **THEN** no registration is demoted and subsequent registrations join the queue

#### Scenario: Settling a tournament that asks for no money
- **WHEN** the organizer settles seating on a tournament whose payments feature is off
- **THEN** no registration is demoted, every seat is kept, and the tournament is recorded as settled
