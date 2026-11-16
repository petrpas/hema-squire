## ADDED Requirements

### Requirement: A row stating no currency is in the tournament's currency
A row of an interpreted statement that states no currency SHALL be read in the tournament's local currency. The interpreter SHALL report a currency only where the row states one, and SHALL NOT supply a default of its own. A statement from a bank that prints no currency column is an export of the account the tournament collects into, and that account's money is the tournament's own.

#### Scenario: A EUR tournament's statement with no currency column
- **WHEN** a statement with no currency column is imported on a tournament whose local currency is EUR
- **THEN** its credits are ingested as EUR and matched against the EUR totals, and none is flagged as an unaccepted currency

#### Scenario: A stated currency is kept
- **WHEN** a row states EUR on a tournament whose local currency is CZK
- **THEN** it is ingested as EUR

### Requirement: Identical payments in one statement are distinct
Where a statement holds two or more rows identical in every field and the bank supplies no identifier, each SHALL be ingested as a transaction of its own. The identifier derived from a row's content SHALL also carry how many identical rows precede it in the same statement, so that the second of two identical payments is not taken for the first read twice. The first occurrence SHALL keep the identifier its content alone gives it.

Re-importing the same statement SHALL still credit nothing twice: each row meets the identifier it was given the first time.

#### Scenario: Two identical payments on one day
- **WHEN** a statement from a bank that numbers nothing holds two identical rows of 1000 Kč with the same variable symbol
- **THEN** both are ingested, and the registration is credited 2000 Kč

#### Scenario: The same statement uploaded twice
- **WHEN** that statement is uploaded again
- **THEN** both rows are counted as duplicates and nothing more is credited
