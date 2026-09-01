## ADDED Requirements

### Requirement: Import, matching and deduplication are started rather than awaited
Uploading a table, running matching, and running deduplication SHALL each start an operation of the tournament and return at once, rather than hold their request open for the length of the work. Each SHALL be subject to the tournament's one-operation-at-a-time rule and SHALL be reported on through its record.

Uploading SHALL record the uploaded file and its rows before returning, so that a batch reaches the tournament whole even where the organizer abandons the response. Only the parsing of those rows SHALL proceed in the background.

Where no LLM is configured, an upload SHALL still record its batch and rows and SHALL report that the rows are unparsed, as it does today, without starting an operation that has nothing to do.

#### Scenario: Upload returns before the parse
- **WHEN** the organizer uploads a table of two hundred rows
- **THEN** the upload returns immediately, the batch and its rows exist, and parsing runs as an operation

#### Scenario: Batch survives an abandoned upload response
- **WHEN** the organizer navigates away the moment after uploading
- **THEN** the batch and all its source rows are recorded, and the parse continues

#### Scenario: Matching started while an import parses
- **WHEN** an import operation is running and the organizer starts matching
- **THEN** the start is refused and names the running import

#### Scenario: No LLM configured
- **WHEN** the organizer uploads a table on a deployment with no LLM configured
- **THEN** the batch and its rows are recorded, the rows are reported unparsed, and no operation is started

## MODIFIED Requirements

### Requirement: Decision persistence and incrementality
LLM outputs — parses, match proposals, merges, classifications — SHALL be materialized as decisions. Reruns SHALL reuse stored decisions; only rows without decisions SHALL invoke the LLM.

A decision SHALL become durable as soon as the work that produced it completes, not only when the whole run completes. A run that stops partway — interrupted, failed, or abandoned — SHALL leave every decision it had already produced standing, and running the same work again SHALL reuse them and invoke the LLM only for what remains.

Decisions stored before disciplines carried slugs SHALL remain readable: a stored decision describing a discipline as a weapon, gender, and material SHALL resolve to the discipline whose classification matches, and SHALL be treated as ambiguous — as an unresolved parse is — where more than one offered discipline matches. Such decisions SHALL NOT be re-parsed merely because their shape is older; they are replaced when their row changes and is parsed afresh.

#### Scenario: Cheap rerun
- **WHEN** the organizer reruns after changing a display parameter
- **THEN** no LLM call is made for already-decided rows

#### Scenario: Partial parse survives an interruption
- **WHEN** an import has parsed sixty of two hundred and twenty rows and the server restarts
- **THEN** the sixty parses stand as decisions, and re-uploading the same file parses only the remaining rows

#### Scenario: Partial parse survives a failure
- **WHEN** an import fails partway because the LLM becomes unreachable
- **THEN** the rows parsed before the failure keep their decisions

#### Scenario: Older decision still resolves
- **WHEN** a row parsed before disciplines carried slugs is read after the migration, and its classification matches exactly one offered discipline
- **THEN** it resolves to that discipline without a new LLM call

#### Scenario: Older decision made ambiguous by a later split
- **WHEN** a row parsed before a tier split is read after the organizer has split that weapon into two disciplines
- **THEN** it is reported as unresolved for the organizer to decide, and is not silently attached to either
