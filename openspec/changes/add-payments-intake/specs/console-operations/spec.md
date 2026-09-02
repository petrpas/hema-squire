## MODIFIED Requirements

### Requirement: An operation is a record, not a request
Console work that calls an LLM — parsing an imported table, interpreting an imported bank statement, matching against the fighters index, deduplicating — SHALL be recorded as an operation of the tournament before it begins. The record SHALL state which tournament it belongs to, which kind of work it is, how many units of work it expects, how many it has completed, when it started, and which organizer started it.

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

#### Scenario: A statement interpreted in the background
- **WHEN** the organizer uploads a bank statement the system must interpret
- **THEN** it is recorded as an operation before the interpreting begins, and reported like any other
