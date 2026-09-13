## ADDED Requirements

### Requirement: Substitution is offered on the fencer list
The fencer table SHALL offer a substitution action at the end of each row, beside the removal action and not in its place. The two are different decisions and both are needed: removal is a seat given up, substitution a seat handed on.

It SHALL be offered on the **fencer list alone**, and not on Import. The Import view is the record of what a file contained, and rewriting a person on it would make it say the file held something it did not; the fencer list is where the roster is settled, and a substitution is a decision about the roster.

The action SHALL open a dialog titled for choosing a substitute, rather than making the row's name cell editable: a substitution is a name, a profile, an address and a notice about mail taken together, and is entered whole or not at all.

The action SHALL carry an outline icon and an accessible name, as every row action does, and SHALL be distinguishable from removal at a glance without reading the tooltip.

Phases after the fencer list SHALL offer no substitution, for the reason they offer no removal: an action at the end of a row about money reads as an action on the money.

#### Scenario: Two actions at the end of a row
- **WHEN** the organizer opens the Fencers tab
- **THEN** each live row offers both substitution and removal, and the two are told apart by their icons

#### Scenario: Import offers removal only
- **WHEN** the organizer opens the Import tab
- **THEN** rows offer removal and restoration as before, and no substitution

#### Scenario: Later phases offer neither
- **WHEN** the organizer opens Matching on HR, Payments or Export
- **THEN** no row offers substitution

#### Scenario: The dialog is a dialog
- **WHEN** the organizer triggers substitution on a row
- **THEN** a dialog opens for choosing the substitute, and the row's cells remain as they were until it is confirmed

### Requirement: A substituted row states that it was substituted
A row whose fencer has been replaced SHALL state it in the fencer table, so that a reader of the list knows this seat changed hands rather than wondering why a paid fencer's name is unfamiliar. The mark SHALL name the fencer replaced, on the row itself or on demand from it, and SHALL use the table's existing marker idiom rather than a colour of its own.

The mark SHALL be a statement about the row and SHALL NOT strike it through, grey it, or otherwise read as a removal: the row is fully live.

#### Scenario: The row says whose seat it was
- **WHEN** the organizer reads the fencer list after a substitution
- **THEN** the substituted row is marked, the mark names the replaced fencer, and the row is otherwise shown as any live row is
