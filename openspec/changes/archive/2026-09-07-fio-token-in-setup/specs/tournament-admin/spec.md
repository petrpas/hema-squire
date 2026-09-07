## ADDED Requirements

### Requirement: The bank feed token is recorded beside the account it reads
The bank feed token SHALL be recorded from the bank account section on `PAYMENTS`,
by an action on the account field's own line rather than by a second field beneath
it. The account and the feed that reads it are one subject, and the token has no
meaning apart from the account it polls.

The section SHALL state whether a token is recorded, so that a configured feed is
distinguishable from an unconfigured one without opening anything.

This is the only place a bank feed token is recorded. No console phase panel SHALL
offer one, in keeping with `setup-navigation`'s one field, one editor.

#### Scenario: The action sits beside the account
- **WHEN** the organizer opens the bank account section on `PAYMENTS`
- **THEN** the feed token action stands on the same line as the account field, at its trailing edge, and no separate token field appears beneath it

#### Scenario: A configured feed is legible without opening the form
- **WHEN** the organizer opens the section on a tournament that already has a token
- **THEN** the section states that a feed token is recorded, without showing the token

#### Scenario: No second editor
- **WHEN** the organizer looks for the feed token in the console's payments-phase panels
- **THEN** it is not offered there, and the bank account section in Setup is the only place it can be recorded

### Requirement: The feed token is offered only on a Fio account
The feed token action SHALL be available only while the bank account is a Fio
account, and SHALL otherwise be shown unavailable with the reason stated, rather
than hidden. Squire polls Fio's API and no other bank's, so a token recorded
against another bank would be a setting that could never be read.

Availability SHALL be decided from the account the organizer is **typing**, not from
the last saved one, so that an account which has just become a Fio account enables
the action at once rather than after a save. The decision SHALL be made on the
account's bank code, in either accepted account form — an IBAN or the Czech domestic
form — so that the same account enables the action however it is written.

Because the action shares the account field's line, its becoming available SHALL NOT
move anything else on the page.

#### Scenario: A Fio account enables the action while typing
- **WHEN** the organizer types a Fio account into the field and has not saved
- **THEN** the feed token action becomes available immediately, and nothing else on the page moves

#### Scenario: Another bank states why not
- **WHEN** the account is a bank other than Fio
- **THEN** the action is shown unavailable and states that the feed reads Fio accounts only

#### Scenario: Either account form is recognised
- **WHEN** the organizer writes the same Fio account in the Czech domestic form rather than as an IBAN
- **THEN** the action is available on both forms alike

#### Scenario: An empty or unfinished account offers nothing
- **WHEN** the account field is empty, or holds a value that is not yet a whole account
- **THEN** the action is shown unavailable, and no error is raised on the incomplete value

#### Scenario: A recorded token survives the account changing
- **WHEN** the organizer edits a Fio account into a non-Fio one on a tournament with a token recorded
- **THEN** the action becomes unavailable, and the stored token is retained rather than cleared

### Requirement: The feed token is written, never read back
The token SHALL be recorded through a small form opened by the action, holding a
field for the token, a short statement of how to make a **read-only** token in Fio
internet banking, and — where one is recorded — a way to remove it.

The stored token SHALL NOT be returned to the console in any form, neither as its
value nor as a stand-in for its length. The console SHALL be told only whether one
is configured. Submitting the form with an empty field SHALL leave the stored token
unchanged rather than clearing it: clearing is what the removal control is for, so
that a feed is never lost by an organizer who opened the form to read what was there.

Recording and removing a token SHALL both take effect when the form is submitted,
rather than being staged into the section's save. A token is checked against the bank
as it is given, and a refusal has to be readable at the field that caused it; a
tournament left with no token SHALL behave exactly as one that never had one. The
rest of the bank account section SHALL keep its ordinary staged save, and an unsaved
account SHALL neither block the form nor be written by it.

#### Scenario: Opening the form on a configured tournament
- **WHEN** the organizer opens the form on a tournament with a token recorded
- **THEN** the field is empty rather than filled or masked, the form states that a token is recorded, and a removal control is offered

#### Scenario: The advice is present where it is needed
- **WHEN** the organizer opens the form
- **THEN** it states that the token must be a read-only one and where in Fio internet banking it is made

#### Scenario: An empty submission changes nothing
- **WHEN** the organizer opens the form on a configured tournament and submits it with the field left empty
- **THEN** the stored token is unchanged

#### Scenario: Removing a token
- **WHEN** the organizer removes the token from the form
- **THEN** no token is stored, the console reports the feed as unconfigured, and the poll action and the deposit mode are withheld as they are on a tournament that never had one

#### Scenario: The form does not save the account beside it
- **WHEN** the organizer edits the account field, leaves it unsaved, and records a token
- **THEN** the token is stored and the edited account is still unsaved, awaiting the section's own save

### Requirement: A feed token is verified before it is stored
Recording a token SHALL verify it against the bank's API before storing it. A token
the bank rejects SHALL be refused at the field, naming the refusal, and nothing SHALL
be stored. An unverifiable token would otherwise be discovered weeks later by a
scheduler sweep the organizer never sees, on a tournament whose reservations were
expiring against a feed that was never arriving.

Where the bank cannot be reached at all — as against a token it actively rejects —
the token SHALL NOT be refused on that ground alone. The organizer SHALL be told the
token could not be checked and the token SHALL be stored, since a bank being
unreachable is not evidence about the token, and refusing would make recording a
correct token depend on Fio's availability at that minute.

Verification SHALL read the account rather than write to it, and SHALL NOT ingest
any transaction: it establishes that the token works, and intake stays the
organizer's own action.

#### Scenario: A mistyped token is refused
- **WHEN** the organizer records a token the bank rejects
- **THEN** the save is refused at the token field with the bank's refusal stated, and no token is stored

#### Scenario: A working token is stored
- **WHEN** the organizer records a token the bank accepts
- **THEN** the token is stored, the section reports a feed as recorded, and the poll action and the deposit mode become available

#### Scenario: Verification ingests nothing
- **WHEN** a token is verified on a tournament with transactions waiting in the bank's feed
- **THEN** no transaction is ingested, no registration is settled, and the payments console is unchanged

#### Scenario: The bank is unreachable
- **WHEN** the bank's API cannot be reached while a token is being recorded
- **THEN** the organizer is told the token could not be checked, and the token is stored
