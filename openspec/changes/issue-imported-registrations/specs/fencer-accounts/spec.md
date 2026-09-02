## ADDED Requirements

### Requirement: A fencer record may exist without an account
A fencer record SHALL be able to exist without an account. Where the organizer
enrols a tournament's own roster — issuing registrations for rows that state who
is competing — the fencer records those registrations need SHALL be created on
the tournament's behalf.

Such a record SHALL hold no credentials and SHALL NOT be usable to log in. Its
creation SHALL send no mail: no invitation, no welcome, no notice that a record
exists. A person SHALL learn of it, if at all, from the organizer.

Creating one SHALL NOT claim a HEMA Ratings profile on the person's behalf
unless a human has already confirmed that the row is that fighter. A proposed or
unresolved match SHALL leave the record unbound, for the same reason self-service
signup binds only on an explicit ownership confirmation: a profile is claimed by
someone who says it is theirs, never by a similarity.

A person whose record was created this way SHALL be able to sign up for an
account afterwards on the ordinary terms, and doing so SHALL NOT be obstructed by
the record existing.

#### Scenario: Record created without credentials or mail
- **WHEN** the organizer issues registrations for rows that have no fencer records
- **THEN** fencer records are created, none can be logged into, and no mail of any kind is sent

#### Scenario: An unconfirmed HR match is not claimed
- **WHEN** a record is created for a row whose HEMA Ratings match has only been proposed
- **THEN** the record carries no HR id

#### Scenario: A confirmed HR match carries over
- **WHEN** a record is created for a row whose HEMA Ratings match the organizer has confirmed
- **THEN** the record carries that HR id

#### Scenario: Signing up afterwards is not obstructed
- **WHEN** a person for whom such a record exists signs up for an account with that email
- **THEN** the signup is accepted on the ordinary terms
