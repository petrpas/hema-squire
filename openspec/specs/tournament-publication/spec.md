# tournament-publication

## Purpose

Govern the explicit, one-time act of publishing a tournament: the draft/published
distinction and its visibility and registration consequences, the publish action's
authorization and irreversibility, its precondition on complete mandatory setup, the
guarantee that a published tournament can never be edited back into incompleteness,
the `PUBLISH` tab that surfaces all of this, and the confirmation required before
publishing takes effect.

## Requirements

### Requirement: A tournament is a draft until it is published
Every tournament SHALL carry a publication record: the moment it was published and the
account that published it, both empty until publication. A tournament with an empty
publication record is a draft. Completing mandatory setup SHALL NOT publish a
tournament, and no tournament SHALL become published by any means other than the
publish action.

A draft SHALL be invisible to fencers — absent from every fencer-facing list — and
SHALL reject new registrations with the not-yet-published reason, regardless of how
complete its setup is or where the current date falls in its registration window. Its
console and its detail record SHALL remain reachable to its organizers.

#### Scenario: Newly created tournament is a draft
- **WHEN** an organizer creates a tournament
- **THEN** its publication record is empty, it appears in no fencer-facing list, and a registration attempt is rejected with the not-yet-published reason

#### Scenario: Completing setup does not publish
- **WHEN** the organizer fills the last mandatory setup item of a draft and saves it
- **THEN** the tournament is still a draft, still absent from the fencer-facing lists, and still rejects registration with the not-yet-published reason

#### Scenario: Draft console stays reachable
- **WHEN** an organizer opens the console of a draft tournament
- **THEN** the console and the tournament's detail record are served as for any other tournament

### Requirement: Publishing is a one-time, irreversible action
Publishing SHALL be an explicit action available to any account with console access to
the tournament. It SHALL stamp the publication record with the current moment and the
acting account, after which the tournament is published for good: no action SHALL clear
the publication record or return a published tournament to draft. Retiring a published
tournament SHALL remain cancellation, which leaves the publication record intact.

A second publish attempt on a published tournament SHALL be refused as already
published, without re-stamping the record. Publishing a cancelled tournament SHALL be
refused. An account without console access SHALL be refused as it is for every other
console action.

#### Scenario: Publication recorded
- **WHEN** a console team member publishes a setup-complete draft
- **THEN** the publication record carries that moment and that account, and the tournament is published

#### Scenario: No way back
- **WHEN** the tournament is published
- **THEN** no console action offers to unpublish it or clears its publication record

#### Scenario: Second publish refused
- **WHEN** a published tournament is published again
- **THEN** the attempt is refused as already published and the recorded moment is unchanged

#### Scenario: Cancelled tournament cannot be published
- **WHEN** a cancelled draft is published
- **THEN** the attempt is refused

#### Scenario: Console access required
- **WHEN** an account with no console access to the tournament attempts to publish it
- **THEN** the attempt is refused exactly as any other console action by that account would be

### Requirement: Publication requires complete mandatory setup
Publishing SHALL be refused while any mandatory setup item is unconfigured, and the
refusal SHALL name every item still missing, using the same item vocabulary the Setup
phase presents. Mandatory setup is defined by `tournament-admin` and is unchanged by
publication.

#### Scenario: Incomplete setup refuses publication
- **WHEN** a tournament with no location and an unpriced discipline is published
- **THEN** the attempt is refused and names the missing location and the missing discipline price

#### Scenario: Complete setup allows publication
- **WHEN** the last missing item is configured and the tournament is published
- **THEN** the publication succeeds

### Requirement: A published tournament cannot be edited into incompleteness
Once a tournament is published, any save that would leave a mandatory setup item
unconfigured SHALL be rejected, naming the item that would be missing, and SHALL write
nothing. This SHALL hold for every route by which a mandatory item can be changed —
clearing a price, removing the last discipline or the last titular organizer, emptying
the location, or switching to a currency mode whose newly required prices are not all
filled. A draft SHALL NOT be restricted this way: any of its mandatory items may be
emptied or removed freely.

The invariant SHALL therefore be that a published tournament always has complete
mandatory setup, and the registration gate SHALL NOT re-check completeness.

#### Scenario: Clearing a price on a published tournament
- **WHEN** the organizer clears a discipline's unit price on a published tournament and saves
- **THEN** the save is rejected naming the missing discipline price, the stored price is unchanged, and the tournament is still published and visible to fencers

#### Scenario: Removing the last discipline
- **WHEN** the organizer deletes the only discipline of a published tournament
- **THEN** the deletion is rejected naming the missing discipline, and the discipline still exists

#### Scenario: Currency switch that would leave prices missing
- **WHEN** the organizer enables EUR on a published tournament that has an extra item with no EUR price
- **THEN** the save is rejected naming the missing EUR price, and the currency mode is unchanged

#### Scenario: Ordinary edits still allowed
- **WHEN** the organizer changes the location text, adds a second discipline with a price, or edits the description of a published tournament
- **THEN** the save succeeds as it would on a draft

#### Scenario: A draft may be emptied
- **WHEN** the organizer deletes the only discipline of a draft tournament
- **THEN** the deletion succeeds and the tournament reports the missing discipline among the items blocking publication

### Requirement: PUBLISH tab
The Setup phase SHALL offer a `PUBLISH` tab that is the only place in the console where
the items blocking publication are listed. It SHALL be available to every account with
console access, and it SHALL carry no save control — it holds an action, not settings.

While the tournament is a draft, the tab SHALL state that the tournament is not
published and is not visible to fencers, SHALL list every item still blocking
publication using the same item names the checklist used, and SHALL offer the publish
control. The control SHALL be inert while any item is listed, and SHALL state that the
listed items must be configured first. When nothing is listed, the control SHALL be
active.

Once the tournament is published, the tab SHALL state that it is published and when,
and SHALL offer no control. When the tournament is cancelled, the tab SHALL state that
and offer no control.

The tab SHALL act on the tournament's saved state. When any Setup tab holds unsaved
changes, the `PUBLISH` tab SHALL say so and state that publication uses the saved
state; it SHALL NOT save those changes, and it SHALL NOT let them satisfy or block
publication.

#### Scenario: Draft with blocking items
- **WHEN** the organizer opens `PUBLISH` on a draft missing its location and a discipline price
- **THEN** the tab states the tournament is not published, lists the missing location and discipline price, and the publish control is inert with a hint that those items must be configured first

#### Scenario: Draft ready to publish
- **WHEN** the organizer opens `PUBLISH` on a setup-complete draft
- **THEN** the tab lists no blocking items and the publish control is active

#### Scenario: Published state
- **WHEN** the organizer opens `PUBLISH` on a published tournament
- **THEN** the tab states that the tournament is published and the date it was published, and offers no control

#### Scenario: No save control
- **WHEN** the organizer opens `PUBLISH`
- **THEN** the tab carries no save control and nothing on it counts as an unsaved change

#### Scenario: Unsaved changes elsewhere
- **WHEN** the organizer has unsaved changes on `DISCIPLINES` and opens `PUBLISH`
- **THEN** the tab states that changes are unsaved and that publication uses the saved state, and the listed blocking items reflect the saved state only

#### Scenario: Unrecognized blocking item
- **WHEN** the server reports a blocking item the client has no name for
- **THEN** it is still listed, the publish control is still inert, and the tab renders normally

### Requirement: Publication is confirmed before it happens
The publish control SHALL NOT publish on its first activation. It SHALL first ask for
confirmation, stating that the tournament will become visible to fencers, that
registration will follow its registration window, and that publication cannot be
undone. Confirming SHALL publish; declining SHALL leave the tournament a draft with
nothing written. The confirmation SHALL be presented in place, without a modal overlay
and without entrance animation, in the same treatment as the tournament cancellation
confirmation.

A refused publication SHALL be reported on the tab, stating why, and SHALL leave the
tournament a draft.

#### Scenario: Confirmation asked
- **WHEN** the organizer activates the publish control
- **THEN** a confirmation appears in place stating that fencers will see the tournament, that registration follows the registration window, and that this cannot be undone

#### Scenario: Declining changes nothing
- **WHEN** the organizer declines the confirmation
- **THEN** the tournament is still a draft, the publication record is still empty, and the tab shows the publish control again

#### Scenario: Confirming publishes
- **WHEN** the organizer confirms
- **THEN** the tournament is published, the tab switches to its published state, and the tournament appears in the fencer-facing list

#### Scenario: Refusal reported
- **WHEN** the publish attempt is refused by the server
- **THEN** the tab states why, and the tournament is still a draft
