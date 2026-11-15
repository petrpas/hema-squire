## ADDED Requirements

### Requirement: A feed token is kept encrypted
A bank feed token SHALL be stored only in encrypted form, under a key that is
part of the deployment's configuration and is never stored in the database. A
copy of the database, its replica or any of its snapshots SHALL NOT be enough to
recover a token. The key SHALL be the token's own and not derived from any other
secret of the deployment, so that replacing another secret does not lose the
feeds.

Where the deployment has no key configured, recording a token SHALL be refused
with a stated reason saying this deployment cannot keep a feed token, and
nothing SHALL be stored. A token SHALL never be stored readable as a fallback.

Where a stored token cannot be decrypted, the bank account section SHALL state
that a token is recorded but cannot be read and has to be entered again, rather
than that a feed is configured. The poll action SHALL state the same reason
rather than failing, and the scheduler SHALL skip that tournament's feed and log
it, without touching anything else of the tournament.

#### Scenario: The database alone does not yield the token
- **WHEN** a token is recorded and the stored value is read straight from the database
- **THEN** the value is not the token and does not contain it

#### Scenario: A recorded token still reads the account
- **WHEN** a token is recorded and the organizer polls the bank, or the scheduler sweeps
- **THEN** the bank is called with the token as it was given

#### Scenario: No key, no token
- **WHEN** the organizer records a token on a deployment with no key configured
- **THEN** recording is refused with the reason stated, and no token is stored

#### Scenario: A token the key no longer opens
- **WHEN** a token was stored under a key the deployment no longer has
- **THEN** the bank account section states that the recorded token cannot be read and has to be entered again, the poll action states the same, and the scheduler skips the feed without failing its sweep

#### Scenario: Entering it again recovers the feed
- **WHEN** the organizer records a new token on a tournament whose stored token cannot be read
- **THEN** the new token is stored under the current key and the feed reads again
