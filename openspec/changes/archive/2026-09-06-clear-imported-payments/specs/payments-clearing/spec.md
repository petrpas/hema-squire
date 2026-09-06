## ADDED Requirements

### Requirement: Clearing the payments a tournament imported
The organizer MAY clear the payments a tournament has taken in. Clearing SHALL
remove every bank transaction the tournament holds and every stored
interpretation of a statement row behind them. The removal SHALL be a deletion
of the data, not a marking of it: nothing cleared SHALL remain visible,
countable or restorable anywhere in the console afterwards, and the tournament
SHALL read as one that has received no money.

Clearing SHALL remove transactions whatever their state — unresolved, flagged,
or set aside — and SHALL NOT be offered as an undo of a single statement: it
removes the imported money at once, so that clearing never leaves an earlier
statement's rows behind to become the tournament's payments again.

Payment links the organizer made SHALL be removed with the transactions they
name, since they speak about money that no longer exists.

#### Scenario: A misread statement is removed altogether
- **WHEN** the organizer imports a statement that was read wrongly and then clears
- **THEN** no transaction remains, every resolution queue is empty, and the tournament reports no money received

#### Scenario: Several statements go together
- **WHEN** the organizer has imported three statements and clears
- **THEN** no transaction from any of the three remains

#### Scenario: A link to a cleared transaction goes with it
- **WHEN** the organizer had linked a transaction by hand and the payments are cleared
- **THEN** the link is gone along with the transaction it named

### Requirement: A cleared statement is read afresh on re-import
Clearing SHALL remove the stored interpretations of the statement rows, not only
the transactions they produced. Re-importing the same file after a clear SHALL
read every row again from the file.

Without this the clear would be a half-measure that hides itself: a statement's
rows are interpreted once and stored against the row's own fingerprint so that
re-importing a corrected file costs nothing for the rows that did not change. A
clear that removed only the transactions would leave those interpretations
standing, and an organizer clearing after a misreading would re-import and
receive the same wrong answer, with nothing on screen to explain why.

The count a clear reports SHALL be the transactions removed. The interpretations
are the mechanism, not the subject, and an organizer SHALL NOT have to know they
exist.

#### Scenario: Re-import after a clear starts clean
- **WHEN** the organizer clears and imports the same statement again
- **THEN** every row is interpreted afresh, with nothing carried over from before the clear

#### Scenario: A corrected file is read as corrected
- **WHEN** a statement was read wrongly, the organizer clears, and imports a corrected export of the same statement
- **THEN** the rows are read from the corrected file rather than from what was stored for the first one

### Requirement: Clearing is refused where money has been credited
Clearing SHALL be refused where any transaction has been credited to a
registration, and SHALL state how many have. A refused clear SHALL remove
nothing at all — not the uncredited transactions, not the stored
interpretations.

A transaction that has been credited is a payment the tournament acted on: a
fencer was marked paid, a balance moved, and mail may have been sent on the
strength of it. Deleting it would leave that claim standing with nothing behind
it. The same rule already governs deleting a tournament, which is refused once
registrations exist because financial history is not the console's to erase.

The organizer resolves those payments first — unlinking what was matched by hand
— after which the clear proceeds normally.

#### Scenario: Credited money stops the clear
- **WHEN** the organizer clears a tournament in which four transactions have been credited
- **THEN** the clear is refused, states that four transactions hold credit, and removes nothing

#### Scenario: A refusal is total, not partial
- **WHEN** a tournament holds forty unresolved transactions and one credited one and the organizer clears
- **THEN** all forty-one remain, and no stored interpretation is removed

#### Scenario: Unresolved money clears freely
- **WHEN** no transaction has been credited
- **THEN** the clear proceeds

#### Scenario: Clearing after the payments are unlinked
- **WHEN** the organizer unlinks the credited payments and clears again
- **THEN** the clear proceeds

### Requirement: What a clear leaves alone
Clearing the imported payments SHALL leave the tournament's fencers and their
registrations exactly as they were: their variable symbols, their totals, their
states and their history. It SHALL leave the imported fencer rows, the batches
they came from and every decision taken about them untouched.

The two clears are separate actions on separate subjects. Clearing the fencer
list SHALL NOT remove the tournament's payments, and clearing the payments SHALL
NOT remove the fencer list.

#### Scenario: The roster survives
- **WHEN** a tournament with an imported roster and imported payments has its payments cleared
- **THEN** every fencer row and every registration remains, with its variable symbol and total unchanged

#### Scenario: The bank poll configuration survives
- **WHEN** the payments are cleared on a tournament configured with a bank token
- **THEN** the token and every payment setting remain, and the bank can be polled again

### Requirement: Clearing the payments is warned about and irreversible
Clearing SHALL be confirmed before it happens. The confirmation SHALL state how
many payments are about to be removed and SHALL state plainly that the removal
cannot be undone. It SHALL be distinguishable from resolving or unlinking a
single transaction, which changes where one payment is directed and destroys
nothing.

Where the clear would be refused, the organizer SHALL be told so before
confirming rather than after — the refusal is a fact about the tournament, not
an outcome of trying.

#### Scenario: The organizer is told the size of the action
- **WHEN** the organizer opens the clear on a tournament holding forty-three payments
- **THEN** the confirmation states that forty-three payments will be removed and that this cannot be undone

#### Scenario: A refusal is stated before it is attempted
- **WHEN** transactions have been credited
- **THEN** the console states that clearing is unavailable and why, rather than offering an action that fails
