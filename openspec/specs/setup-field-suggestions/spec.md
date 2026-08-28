# setup-field-suggestions Specification

## Purpose

Offers an organizer, as they fill in a Setup field, the values they themselves put
in that field on their earlier tournaments — so a club name, a venue and an account
number are recalled rather than retyped, and stay consistent across the events one
organizer runs year after year.

## Requirements

### Requirement: Setup fields that recall prior values
The Setup screen SHALL offer previously used values on the titular organizer entry
(ORGANIZERS), the tournament location (IDENTITY) and the tournament bank account.
No other Setup field carries the affordance. A field with nothing to recall SHALL
behave exactly as a plain field: no empty list, no placeholder entry, and no
indication that the feature exists.

#### Scenario: Organizer's second tournament
- **WHEN** an organizer who has already run one tournament begins typing in the location field of a new one
- **THEN** the location they used on that earlier tournament is offered

#### Scenario: A field outside the three
- **WHEN** the organizer types in the tournament's subtitle, description or any other Setup field
- **THEN** nothing is offered, and the field behaves as it did before this capability existed

#### Scenario: The very first tournament
- **WHEN** an organizer with no earlier tournaments opens Setup and types in any of the three fields
- **THEN** no list appears and the field shows no sign that suggestions exist

### Requirement: Suggestions come from the organizer's own tournaments
Offered values SHALL be drawn only from tournaments the requesting account owns or
holds console access to, and SHALL be derived from those tournaments' current stored
values at the time of the request rather than from a separate record of what was
once typed. An account SHALL never be offered a value originating from a tournament
it has no access to.

#### Scenario: One organizer's values stay their own
- **WHEN** two organizers with no tournaments in common each type in the location field
- **THEN** neither is offered a location belonging to the other's tournaments

#### Scenario: A corrected value stops being offered
- **WHEN** an organizer fixes a misspelled club name on the tournament it came from, then opens a different tournament's Setup
- **THEN** the corrected spelling is offered and the misspelling is not

#### Scenario: Tournaments that predate the capability
- **WHEN** an organizer who has run tournaments since before this capability existed opens Setup
- **THEN** values from those tournaments are offered, with no action required to record them first

#### Scenario: Access granted after the fact
- **WHEN** an account is given console access to an existing tournament
- **THEN** that tournament's values join the account's suggestions

### Requirement: Offering, choosing and overriding
A suggestion SHALL be offered, never applied on the organizer's behalf: no field is
prefilled, and no value changes without the organizer choosing it. The list SHALL be
navigable and choosable by keyboard as well as by pointer, and SHALL be dismissible
without choosing, leaving whatever was typed untouched. A chosen value SHALL be
subject to the field's own validation exactly as a typed value is.

#### Scenario: Nothing fills itself in
- **WHEN** the organizer opens Setup on a new tournament
- **THEN** the three fields hold what the tournament holds — empty if it is empty — and no suggestion has been written into them

#### Scenario: Typing past the list
- **WHEN** the organizer types a value that matches nothing in the list
- **THEN** the typed value stands and is saved as typed

#### Scenario: Dismissing the list
- **WHEN** the organizer dismisses the list without choosing
- **THEN** the text they had typed remains exactly as they left it

#### Scenario: Keyboard choice
- **WHEN** the organizer moves through the offered values with the keyboard and confirms one
- **THEN** that value is placed in the field, the list closes, and focus stays in the field

#### Scenario: A recalled value that no longer validates
- **WHEN** the organizer chooses a suggestion that fails the field's validation
- **THEN** the field reports the error the same way it would for that value typed by hand, and the save is refused

### Requirement: The organizer entry recalls its link with its name
The titular organizer suggestion SHALL carry the name and its link together:
choosing a remembered organizer SHALL fill both. Where one remembered name has been
used with more than one link, each name-and-link pairing SHALL be offered separately
so the organizer can tell them apart and pick the intended one.

#### Scenario: Name and link arrive together
- **WHEN** the organizer chooses a remembered club whose earlier entry carried a link
- **THEN** both the name and that link are filled in, without the link being typed again

#### Scenario: A remembered name that never had a link
- **WHEN** the organizer chooses a remembered club that was used with no link
- **THEN** the name is filled and the link field is left empty rather than filled with a stale value

#### Scenario: One name, two links
- **WHEN** a club name has been used with two different links across the organizer's tournaments
- **THEN** both pairings are offered as distinguishable entries

### Requirement: Ordering and bounds of the offered values
Offered values SHALL be distinct — one entry per value, however many tournaments
carry it — and SHALL be ordered with the most recently used first, so the value an
organizer is most likely to want is the one nearest to hand. The number offered at
once SHALL be bounded, so an organizer with a long history is not given a list that
must be scrolled to be read.

#### Scenario: A value used on many tournaments
- **WHEN** an organizer has used the same venue on five tournaments
- **THEN** it is offered once, not five times

#### Scenario: Most recent first
- **WHEN** an organizer has used two different venues, one of them more recently
- **THEN** the more recently used one is offered above the other

#### Scenario: A long history
- **WHEN** an organizer has used more distinct values than the list is allowed to show
- **THEN** the list shows the most recent ones up to its bound rather than growing without limit

### Requirement: Suggestions are read-only and leave no trace
Requesting or choosing a suggestion SHALL NOT modify any tournament other than the
one being edited, SHALL NOT create a record of the organizer's typing, and SHALL NOT
change what any other user is offered. A value reaches a tournament only through the
Setup screen's ordinary save.

#### Scenario: Opening the list changes nothing
- **WHEN** the organizer opens a suggestion list and dismisses it without choosing
- **THEN** no tournament has been modified and nothing has been stored about the interaction

#### Scenario: Choosing without saving
- **WHEN** the organizer chooses a suggestion and then leaves Setup without saving
- **THEN** the tournament is unchanged, exactly as if they had typed the value and left
