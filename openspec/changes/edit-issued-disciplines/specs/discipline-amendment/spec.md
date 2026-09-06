## ADDED Requirements

### Requirement: An organizer may change the disciplines of a registration that exists
The disciplines cell on the fencer list SHALL open for every row the phase
lists, whether or not a registration stands behind it.

Where no registration stands behind the row, the edit SHALL remain a correction
to the row, carried into the registration when the row is issued.

Where one does, the edit SHALL change the registration itself: its discipline
entries SHALL be replaced by the disciplines named, and its stored total SHALL
be recomputed from the replaced selection. The cell SHALL NOT be allowed to
change only what the table displays — a row saying one thing while the
registration bills another is the condition this requirement exists to prevent.

The recomputation SHALL be the one the fencer's own amendment uses, so that the
two paths cannot drift, and SHALL price **at the registration's own registration
moment**. Early-bird pricing therefore applies exactly as it applied when the
fencer registered, and correcting a discipline SHALL NOT reprice the rest of the
registration to today's fees (`imported-registrations`, What an issued
registration is worth).

#### Scenario: The cell opens on a registration that exists
- **WHEN** the organizer opens the fencer list of a roster whose registrations have been issued
- **THEN** the disciplines cell of every row opens for editing

#### Scenario: The money follows the table
- **WHEN** the organizer replaces a registration's single discipline with one priced differently
- **THEN** the registration's entries are the discipline named, and its total is that discipline's fee

#### Scenario: Early bird survives the correction
- **WHEN** a registration made before the early-bird deadline has a discipline corrected after that deadline has passed
- **THEN** its recomputed total uses early-bird prices

#### Scenario: A fee change is still not a repricing
- **WHEN** a discipline's fee is raised, and afterwards an unrelated registration has its disciplines corrected
- **THEN** the corrected registration is priced at the fees that applied at its own registration moment

### Requirement: An edited registration keeps its seat where issuing gave it one
How a newly named discipline is placed SHALL follow the registration's own
origin, so that neither of the two rules already fixed for placement is broken
by reaching the registration from the console instead.

Where the registration's clocks are dormant by virtue of its origin — an issued
registration, made from an imported or manually entered row — every discipline
named by the edit SHALL be entered as a **seated** placement, whatever that
discipline's capacity says. A fencer list is a record of who is competing, and a
substitute placement is not billed: queueing a correction would make the fencer
free (`imported-registrations`, Capacity does not apply to an issued
registration).

Where the registration was made in the application by the fencer, a newly named
discipline that is full SHALL be joined as a **substitute placement in place**,
exactly as the fencer's own amendment joins one, and every other named
discipline SHALL be unaffected by it. The edit SHALL NOT be refused whole
because one discipline is full.

Removing a discipline SHALL free whatever placement it held, seated or
substitute.

#### Scenario: A correction to an issued roster is seated
- **WHEN** the organizer adds to an issued registration a discipline that is already at capacity
- **THEN** the placement is seated and billed, not queued

#### Scenario: An in-app registration follows the amendment rule
- **WHEN** the organizer adds to a fencer's own registration a discipline that is already at capacity
- **THEN** that placement is a substitute placement and the registration's other placements are unchanged

#### Scenario: One full discipline does not refuse the rest
- **WHEN** an edit names two disciplines, one of them full
- **THEN** both are entered, and only the full one is placed as the registration's origin dictates

### Requirement: The fencer is told only where the correction costs them
Squire SHALL notify the fencer of an organizer's discipline edit **only where
the edit leaves them owing more than before**, by the same surcharge notice the
fencer's own amendment sends.

An edit that lowers what is owed, or leaves it unchanged, SHALL send nothing. An
organizer straightening an imported roster is correcting a record, not
corresponding with a competitor, and a letter per corrected row would make the
correction cost more than the error.

Where the edit leaves a paid registration owing less than it has paid, the
registration SHALL be marked as owing a refund, exactly as the fencer's own
amendment marks it — the money is the organizer's to return, and the mark is how
they are told there is money to return.

A registration whose clocks are dormant SHALL be notified on the same terms as
any other: what dormancy suspends is the passage of time, not a statement about
money that has just changed (`imported-registrations`, An issued registration's
clocks never start).

#### Scenario: A dearer correction is announced
- **WHEN** the organizer adds a discipline to a registration, raising what it owes
- **THEN** the fencer receives the surcharge notice

#### Scenario: A cheaper correction is silent
- **WHEN** the organizer removes a discipline from an unpaid registration
- **THEN** no mail is sent, and the registration's total is lowered

#### Scenario: Correcting a whole imported roster sends no post
- **WHEN** the organizer corrects the disciplines of forty imported rows, none of which then owes more
- **THEN** no fencer is mailed

#### Scenario: Overpayment becomes a refund to make
- **WHEN** a paid registration has a discipline removed, leaving it having paid more than it owes
- **THEN** it is marked as owing a refund

### Requirement: The organizer's correction is not bound by the fencer's window
The edit SHALL be available whatever the tournament's amendment window says and
whatever makes the registration's clocks dormant.

The amendment window governs what a fencer may do to their own registration. The
organizer straightening the roster is doing something else, and the moment they
most need to do it — the days before the export, once the entries have settled —
is exactly when that window is shut. Refusing them there would take the
correction away at the only time it is wanted.

The edit SHALL still be refused for a registration in a state that no longer
describes a competitor: one that has expired or been cancelled returns through
re-registration, not through a cell.

#### Scenario: Corrected after the amendment deadline
- **WHEN** the organizer corrects a registration's disciplines after the tournament's amendment deadline has passed
- **THEN** the edit is applied

#### Scenario: A dormant registration is still correctable
- **WHEN** the organizer corrects the disciplines of an issued registration whose clocks are dormant
- **THEN** the edit is applied and the registration's total is recomputed

#### Scenario: An expired registration is not corrected in the table
- **WHEN** the organizer attempts to correct the disciplines of an expired registration
- **THEN** the edit is refused, stating that the registration is no longer live
