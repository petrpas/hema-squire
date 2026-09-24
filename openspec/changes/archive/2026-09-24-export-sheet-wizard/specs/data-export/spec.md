## ADDED Requirements

### Requirement: The export's destination is configured where the export is run
The spreadsheet the Sheets export writes to SHALL be configured in the Export phase, in
the same rail as the control that writes to it, and SHALL NOT be offered anywhere in
Setup.

The address is not a fact about the tournament — it does not govern publication, it is not
read by any rule, and no fencer is affected by it. It is where one tool puts its output,
and it is discovered at the moment that tool is used. An organizer who has just pressed
Export is the only person who has ever needed it.

The address SHALL remain one field in storage with one editor, so that the value the
export reads is the value the organizer last entered.

#### Scenario: Setup no longer offers the address
- **WHEN** the organizer opens Setup and visits every tab
- **THEN** no tab offers the export sheet address

#### Scenario: The address is edited beside the export
- **WHEN** the organizer opens the Export phase
- **THEN** the rail offers a control that opens the address for editing, on the same screen as the export control

### Requirement: Configuring the destination is a stated three-step procedure
The console SHALL offer the destination not as a bare address field but as a dialog
stating, in order, the three things that must be true for an export to succeed:

1. an empty spreadsheet exists;
2. it is shared for **writing** with the address the server's Google access acts as, which
   the dialog SHALL state in full and SHALL offer a control that puts on the clipboard;
3. its link is entered, in the field the dialog carries.

The second step is the one a procedure has to state: the service account is its own
identity, so an organizer's own access to their spreadsheet grants the export nothing, and
a spreadsheet that is merely visible is not writable. Without that sentence the export
fails on a permission the organizer has no way to guess at.

Confirming the dialog SHALL store the address. Dismissing it SHALL store nothing.

#### Scenario: The procedure is stated in order
- **WHEN** the organizer opens the destination dialog
- **THEN** it states the three steps in order, states the service account's address in full, and offers a field for the link

#### Scenario: The address is copied rather than transcribed
- **WHEN** the organizer uses the dialog's copy control
- **THEN** the service account's address is on the clipboard and the dialog states that it was copied

#### Scenario: Dismissal stores nothing
- **WHEN** the organizer types a link into the dialog and dismisses it without confirming
- **THEN** the tournament's stored address is unchanged

### Requirement: The console states the export's service account
The console SHALL be able to read, for an account with console access to a published
tournament, whether the server is configured for Google access at all and — where it is —
the address that access acts as.

The address SHALL be read from the credentials the server already holds, never entered
a second time as its own setting: an address that could disagree with the credentials
would send organizers to share their spreadsheets with an identity that cannot open them.

The address SHALL be stated only within the destination dialog, to an organizer of that
tournament. It is an operational address, not a public one.

#### Scenario: Configured server states its account
- **WHEN** an organizer of a published tournament opens the destination dialog on a server holding Google credentials
- **THEN** the dialog states the address those credentials act as

#### Scenario: No credentials, no export offered
- **WHEN** the server holds no Google credentials
- **THEN** the export control is not offered, and the dialog says in place of its second step that the server has no Google access configured

#### Scenario: The account is not public
- **WHEN** a request without console access to the tournament asks for the export's configuration
- **THEN** it is refused, as every other read of that tournament's console is

### Requirement: The export asks for a destination once
Pressing the export control on a tournament with no stored destination SHALL open the
destination dialog rather than reporting an error. Pressing it on a tournament that has one
SHALL run the export without asking.

A missing destination is not a failure the organizer caused; it is the next step, and the
console knows what that step is. The refusal the server raises for an absent address
SHALL remain, as the guarantee behind the console's behaviour rather than something an
organizer meets.

#### Scenario: First export opens the dialog
- **WHEN** the organizer presses export on a tournament that has never been exported
- **THEN** the destination dialog opens and no export is attempted

#### Scenario: A stored destination is not asked for again
- **WHEN** the organizer presses export again after confirming the dialog
- **THEN** the export runs without a dialog

#### Scenario: The server still refuses an address-less export
- **WHEN** an export is requested for a tournament with no stored address
- **THEN** the request is refused naming the missing address

### Requirement: A destination can be forgotten

Beside the stated destination the Export phase SHALL offer a control that clears it, after
which the tournament names none and the next export asks for one again through the
destination dialog.

Clearing SHALL NOT be confirmed. It ends nothing an organizer holds: the spreadsheet and
everything written into it are untouched, the tournament keeps every row it would export,
and undoing it costs pasting back a link the organizer still has. A confirmation would
weigh more than the act it guards.

The control SHALL be offered only where a destination is stored, since there is otherwise
nothing to forget.

#### Scenario: Forgetting returns the tournament to asking
- **WHEN** the organizer clears the stated destination and presses export
- **THEN** the tournament names no destination, the destination dialog opens, and no export is attempted

#### Scenario: Clearing is not confirmed
- **WHEN** the organizer uses the clearing control
- **THEN** the destination is gone at once, with no dialog asking them to confirm it

#### Scenario: Nothing to forget where nothing is stored
- **WHEN** the organizer opens the Export phase on a tournament that names no destination
- **THEN** no clearing control is offered

### Requirement: The rail states the destination as a link
Where the tournament has a stored destination, the Export phase's rail SHALL state it as a
link that opens the spreadsheet, below the export control.

While an export is running the link SHALL be withdrawn, and SHALL return when the run
concludes. The withdrawal is how a run states that it is a run: the export has no progress
to report and no interruption to offer, so the one honest signal of "working, then done" is
the destination going away and coming back. It SHALL return on failure as well as on
success — the spreadsheet is still where it is — with the failure stated separately.

#### Scenario: A stored destination is a link on arrival
- **WHEN** the organizer opens the Export phase on a tournament that has a destination
- **THEN** the rail states it as a link, before any export has been run in this visit

#### Scenario: The link withdraws for the run
- **WHEN** the organizer presses export
- **THEN** the link is absent while the export runs and present again once it concludes

#### Scenario: A failed run still leaves the link
- **WHEN** an export fails
- **THEN** the failure is stated and the destination is stated as a link beside it
