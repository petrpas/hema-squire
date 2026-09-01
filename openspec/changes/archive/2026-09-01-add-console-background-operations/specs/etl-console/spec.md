## ADDED Requirements

### Requirement: A standing indicator of the tournament's running work
The console SHALL carry an indicator, in the bottom right, present on every phase, stating the tournament's running operation: what kind of work it is and how far it has come. The indicator SHALL belong to the console rather than to any phase, so that stepping between phases neither creates nor hides it.

The indicator SHALL be absent when nothing is running. On conclusion it SHALL state the outcome briefly and then leave by fade-out.

The indicator SHALL be static text that changes when the count changes. It SHALL carry no spinner, no animated bar, and no motion of its own.

The indicator SHALL be shown in the console only. Screens outside a tournament's console SHALL NOT carry it.

#### Scenario: Running work follows the organizer between phases
- **WHEN** the organizer starts an import and steps to Payments
- **THEN** the indicator is still present, naming the import and its progress

#### Scenario: Absent when idle
- **WHEN** no operation is running for the tournament
- **THEN** no indicator is shown

#### Scenario: Leaves after concluding
- **WHEN** a running operation concludes
- **THEN** the indicator states the outcome and then fades out

### Requirement: A phase panel reports its own phase's operation
The rail panel of a phase that starts work — Import, Matching, Dedup — SHALL take both its readiness and its report from the tournament's record of that work, not from what the panel itself has done. Its action SHALL be unavailable while any operation of the tournament is running, and SHALL state what is running. Its result line SHALL state the outcome of the most recent operation of its own kind.

A panel SHALL report the same thing after a remount as before it. Leaving the phase and returning, or reloading the console, SHALL NOT clear a running operation's progress or a concluded one's outcome.

#### Scenario: Action unavailable while other work runs
- **WHEN** an import is running and the organizer opens the Matching phase
- **THEN** the matching action is unavailable and the panel names the running import

#### Scenario: Report survives leaving the phase
- **WHEN** an import concludes, and the organizer steps away from Import and returns
- **THEN** the panel still states what the import produced

#### Scenario: Progress survives a reload
- **WHEN** the organizer reloads the console while deduplication is running
- **THEN** the Dedup panel shows the operation running with its progress, and its action unavailable

### Requirement: The fencer list follows a concluded operation
When an operation concludes, the console SHALL reload the fencer list on its own. The organizer SHALL NOT have to refresh the console to see what an operation produced.

The manual refresh action SHALL remain available; it SHALL stop being the only way to see the result of finished work.

#### Scenario: Results appear without a refresh
- **WHEN** an import concludes while the organizer is looking at the Import phase
- **THEN** the parsed rows appear in the table without the organizer pressing Refresh

#### Scenario: Results appear on the phase the organizer is on
- **WHEN** matching concludes while the organizer is on the Fencers phase
- **THEN** the fencer list reloads and shows what matching decided
