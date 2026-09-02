## MODIFIED Requirements

### Requirement: Manual entry of a fencer
The organizer MAY add a fencer to the fencer list by hand, without a file and without the fencer registering. The action SHALL be offered on the Fencers tab and nowhere else, and SHALL open a dialog rather than an editable blank row — a row is entered whole or not at all.

A manually entered row SHALL be a source record of the tournament in its own right, a third population beside in-app registrations and imported rows. It SHALL take a fixed number when it is entered, SHALL sort by the registration moment it states, SHALL carry its note, and SHALL travel through matching, deduplication and export exactly as an imported row does. It SHALL be editable and deletable by the same means as any other row.

A manually entered row SHALL NOT create an account for the fencer, and SHALL NOT cause any mail to be sent. **It SHALL NOT be given a variable symbol or a payment instruction when it is entered.** It states who is competing; entering it does not enrol them in the application.

A row SHALL become billable only by the separate, explicit action that issues registrations for the fencer list, offered after deduplication and described in `imported-registrations`. That action SHALL apply to manually entered rows and imported rows alike — both state who is competing, and neither is enrolled until the organizer says so. Being issued a registration SHALL NOT cause mail to be sent either, and SHALL NOT create an account.

A manually entered row SHALL NOT appear on the Import view, in any state. The Import view records what a file contained, and a manual entry came from no file.

#### Scenario: Fencer entered at the door
- **WHEN** the organizer enters a fencer by hand on the Fencers tab
- **THEN** one new row joins the fencer list, carrying a fixed number of its own, in the chronological place its registration moment gives it

#### Scenario: Manual entry absent from Import
- **WHEN** the organizer enters a fencer by hand while an imported batch is present
- **THEN** the Import view is unchanged and lists only the file's rows

#### Scenario: Manual entry is not offered on Import
- **WHEN** the organizer opens the Import tab
- **THEN** no manual entry action is offered there

#### Scenario: Manual row deduplicates like any other
- **WHEN** a manually entered fencer shares an hr_id with an imported row
- **THEN** the pair is queued for the organizer's review as a duplicate pair

#### Scenario: Manual row is editable afterwards
- **WHEN** the organizer corrects the club of a manually entered fencer in the table
- **THEN** the correction is recorded in the fencer list's manual-edits log, as it would be for any other row

#### Scenario: No account is created
- **WHEN** a fencer is entered by hand
- **THEN** no account exists for them, no confirmation mail is sent, and no payment instruction is issued

#### Scenario: Entry alone issues no variable symbol
- **WHEN** a fencer is entered by hand on a tournament whose payments feature is on
- **THEN** the row carries no variable symbol until registrations are issued for the list

#### Scenario: Manual rows are issued alongside imported ones
- **WHEN** the organizer issues registrations for a list holding both imported and manually entered rows
- **THEN** both populations are issued registrations, and neither is sent mail
