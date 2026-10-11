## ADDED Requirements

### Requirement: The entrant rosters are public
A published, non-cancelled tournament's entrant rosters (`public-entrants`) SHALL be readable without a credential, and SHALL be answered identically for an anonymous visitor and for any account. A roster carries nothing about the caller.

Publication SHALL be the line here as it is for the detail. A draft and a cancelled tournament SHALL yield a not-found answer on the rosters, worded as the public detail words it, and SHALL NOT hand out any entrant. A cancelled tournament's roster is not evidence of who would have fenced in it.

#### Scenario: Rosters without a credential
- **WHEN** a visitor holding no credential requests a published tournament's entrants
- **THEN** the rosters are returned, the same as for a signed-in fencer

#### Scenario: A cancelled tournament lists nobody
- **WHEN** the entrants of a cancelled tournament holding forty registrations are requested
- **THEN** the answer is not-found and names no entrant

#### Scenario: A draft lists nobody
- **WHEN** the entrants of a draft are requested
- **THEN** the answer is not-found

## MODIFIED Requirements

### Requirement: The public detail carries no organizer's business
The fencer-facing detail SHALL carry only what a fencer reads: the tournament's identity,
dates, city and address, qualification, organizers, disciplines with their fees and counts, extra
services with their prices, the registration window and its status, the currency, and the
feature flags that decide which of those are shown at all.

It SHALL NOT carry the organizer's own configuration: the bank account, whether a bank-feed
token is on file, the accounting sheet address, the variable-symbol series, reservation and
reminder parameters, the amount tolerance, the HR category map,
the setup-completeness report, or the owner's account identifier. Those belong to the
console, which reads them through its own authenticated path.

A field is withheld by being absent from the fencer-facing answer, not by being blanked:
what a fencer is never shown is not something a fencer's client should have to decide to
ignore.

#### Scenario: Bank details are not in the fencer's answer
- **WHEN** the fencer-facing detail of a tournament with a bank account and a stored feed token is read
- **THEN** the answer carries neither the account number nor any statement about the token

#### Scenario: Setup state is not in the fencer's answer
- **WHEN** the fencer-facing detail of a published tournament with incomplete optional setup is read
- **THEN** the answer carries no setup-completeness report

#### Scenario: The console still reads everything
- **WHEN** a member of a tournament's console team opens its Setup phase
- **THEN** every organizer-owned field is available to it, unchanged
