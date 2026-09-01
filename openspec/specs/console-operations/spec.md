# console-operations Specification

## Purpose
Govern long-running console work — LLM table parsing, HR matching, deduplication — as
records owned by the tournament rather than as requests owned by a browser tab, so that
progress, refusal, outcome and recovery survive a reload, a second organizer, and a
restart of the process.

## Requirements

### Requirement: An operation is a record, not a request
Console work that calls an LLM — parsing an imported table, matching against the fighters index, deduplicating — SHALL be recorded as an operation of the tournament before it begins. The record SHALL state which tournament it belongs to, which kind of work it is, how many units of work it expects, how many it has completed, when it started, and which organizer started it.

The request that starts an operation SHALL return as soon as the record exists, without waiting for the work. The work SHALL proceed independently of that request, and SHALL neither stop nor change when the client abandons the response.

Everything the console knows about an operation SHALL come from the record. No part of the console's report on running work SHALL depend on holding the response that started it, on the page that started it remaining open, or on the browser session that started it.

#### Scenario: Reload during a long import
- **WHEN** the organizer starts an import of a large table and reloads the console while it runs
- **THEN** the console reports that the import is running and how far it has come

#### Scenario: Reported on a phase that did not start it
- **WHEN** matching is running and the organizer steps to the Payments phase
- **THEN** the console still reports that matching is running

#### Scenario: Visible to a second organizer
- **WHEN** one organizer starts a deduplication and another opens the same tournament's console
- **THEN** the second organizer sees that deduplication is running

#### Scenario: Abandoned response does not stop the work
- **WHEN** the organizer closes the tab while an import is parsing
- **THEN** the parsing continues to its end and the record shows it concluded

### Requirement: Progress is counted and stated in units of work
An operation SHALL state its total when it starts and SHALL raise its completed count as work lands. The total SHALL count the work the operation will actually do, not the size of what it was pointed at: rows whose decision is already stored are reused rather than worked on and SHALL NOT be counted.

A completed count SHALL only ever describe work whose result is stored. An operation SHALL NOT report a unit complete before the result of that unit is durable.

The completed count SHALL be a count of finished units and SHALL NOT be a position in a sequence, so that it remains correct however units are ordered or interleaved.

Progress SHALL be reported to the organizer as counted text. It SHALL NOT be reported by a spinner, an animated progress bar, or any other device that moves while the count stands still.

#### Scenario: Count rises during a parse
- **WHEN** an import of two hundred and twenty unparsed rows is running
- **THEN** the console states how many of the two hundred and twenty have been parsed, and the number rises as batches complete

#### Scenario: Reused rows are not work
- **WHEN** the organizer re-uploads a file whose rows are all unchanged
- **THEN** the operation's total counts no rows, and the operation concludes without reporting a long parse that did nothing

#### Scenario: The count never runs ahead of the results
- **WHEN** an operation reports sixty units complete
- **THEN** the results of those sixty units are stored and survive the operation being interrupted

### Requirement: One operation at a time for a tournament
A tournament SHALL have at most one running operation. Starting an operation while one is running SHALL be refused, and the refusal SHALL name the kind of work already running.

The refusal SHALL rest on the record, so that it holds equally for a second browser tab, a second organizer, and a repeated request — not on the state of the page that offers the action.

Operations of different tournaments SHALL NOT block one another.

#### Scenario: Second tab refused
- **WHEN** an import is running and the organizer starts another from a second tab
- **THEN** the second start is refused and names the running import

#### Scenario: Two organizers, one operation
- **WHEN** one organizer has matching running and another starts deduplication
- **THEN** the second start is refused and names the running matching

#### Scenario: Another tournament is unaffected
- **WHEN** one tournament has an import running and an organizer of a different tournament starts one
- **THEN** the second import starts normally

### Requirement: An operation concludes with its outcome recorded
An operation SHALL conclude as done or as failed, and the record SHALL hold the outcome either way — for a completed operation, everything the console needs to report what the work produced; for a failed one, what went wrong.

An operation SHALL NOT be left running by any ending. Work that raises SHALL conclude the record as failed rather than abandon it.

The most recent concluded operation of each kind SHALL remain readable after it ends, so that an organizer who was not watching when it landed can still see what it did.

#### Scenario: Outcome outlives the page
- **WHEN** an import concludes while the organizer is on another phase, and they return to Import
- **THEN** the panel states what the import produced

#### Scenario: Failure is reported, not silent
- **WHEN** the LLM is unreachable partway through a matching operation
- **THEN** the operation concludes as failed, the console says so, and nothing reports matching as still running

#### Scenario: Nothing stays running after it stops
- **WHEN** an operation raises an unexpected error
- **THEN** its record is concluded and a new operation may be started

### Requirement: Work interrupted by a restart is recovered at startup
An operation cannot outlive the process running it. On startup, every operation left unconcluded SHALL be concluded as interrupted.

An interrupted operation SHALL keep everything it completed before it stopped. Starting the same work again SHALL reuse those results and SHALL do only the remainder.

Interruption SHALL be reported as work that stopped partway and can be finished by running it again, distinctly from failure, and SHALL NOT be presented to the organizer as an error.

#### Scenario: Restart clears a phantom
- **WHEN** the server restarts while an import is parsing and the organizer opens the console
- **THEN** the import is reported as interrupted and nothing is reported as running

#### Scenario: Re-running finishes the remainder
- **WHEN** an import that had parsed sixty of two hundred and twenty rows was interrupted, and the organizer uploads the same file again
- **THEN** the sixty are reused and the operation's total counts only the remaining rows

#### Scenario: Interruption is not failure
- **WHEN** an interrupted operation is reported
- **THEN** the console states that the work stopped partway and that running it again will finish it
