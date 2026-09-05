## MODIFIED Requirements

### Requirement: A fencer record may exist without an account
A fencer record SHALL be able to exist without an account. Where the organizer
enrols a tournament's own roster — issuing registrations for rows that state who
is competing — the fencer records those registrations need SHALL be created on
the tournament's behalf.

Such a record SHALL hold no credentials and SHALL NOT be usable to log in. Its
creation SHALL send no mail: no invitation, no welcome, no notice that a record
exists. A person SHALL learn of it, if at all, from the organizer.

**Such a record SHALL be able to hold no e-mail address.** An address identifies
an account and is what a login is looked up by; a record that cannot be logged
into needs none, and requiring one forces the organizer to write an address that
is not the person's — most often a parent's or a club representative's, entered
once for several fencers. A record SHALL therefore be creatable with the address
absent, and its absence SHALL NOT be treated as an incomplete record.

**An e-mail address SHALL belong to at most one fencer record.** Where a row
carries an address a record already holds **and names the person that record
names**, that record SHALL be reused, and its name, credentials and HEMA Ratings
binding SHALL be left as they are. Where the names disagree the address is
somebody else's — a parent's, a club representative's — and the row SHALL be
given its own record with no address: an address is a way of reaching a person,
never a statement of who they are. Where a
second row of the same list repeats an address the enrolment has just claimed,
the second record SHALL be created without one: two rows sharing an address are
one person's address written against another, which deduplication has already
had its say about, and asserting it as the second person's would be a claim
nobody made. Which row keeps it SHALL be the order the rows are enrolled in.

**A message SHALL NOT be constructed without a recipient.** Attempting it SHALL
be refused rather than sent, skipped or delivered empty. A fencer with no
address is consequently sent nothing, but that SHALL hold as a property of the
mail path itself rather than as a consequence of every caller happening to
avoid it: a caller that would mail such a record is a fault to be raised where
it happens, not a message to be silently dropped.

Creating a record SHALL NOT claim a HEMA Ratings profile on the person's behalf
unless a human has already confirmed that the row is that fighter. A proposed or
unresolved match SHALL leave the record unbound, for the same reason self-service
signup binds only on an explicit ownership confirmation: a profile is claimed by
someone who says it is theirs, never by a similarity.

A person whose record was created this way SHALL be able to sign up for an
account afterwards on the ordinary terms, and doing so SHALL NOT be obstructed by
the record existing. Where the record carries no address there is nothing for the
signup to recognise, and a second record SHALL be created — the person's own,
carrying no history from the first. Reconciling the two is not addressed here.

#### Scenario: Record created without credentials or mail
- **WHEN** the organizer issues registrations for rows that have no fencer records
- **THEN** fencer records are created, none can be logged into, and no mail of any kind is sent

#### Scenario: Two rows entered on one address are both enrolled
- **WHEN** registrations are issued for a list holding two fencers whose rows carry the same e-mail address
- **THEN** both are enrolled, the first record carries the address, and the second carries none

#### Scenario: An existing account keeps its address and its identity
- **WHEN** a row carries the address of a fencer who already has an account, and names that fencer
- **THEN** that record is reused, and its name, credentials and HEMA Ratings binding are unchanged

#### Scenario: A parent's address does not enrol the child as the parent
- **WHEN** a roster carries a father and his two sons, all three on the father's address
- **THEN** three records exist, the father's keeps the address, and neither son is enrolled under his name

#### Scenario: A record with no address is not incomplete
- **WHEN** a record created on the tournament's behalf holds no address
- **THEN** it is a fencer of the tournament in every respect other than logging in and being written to, and no surface reports it as faulty

#### Scenario: Mail with no recipient is refused
- **WHEN** any path attempts to send a message to a fencer holding no address
- **THEN** the attempt is refused as a fault, and no message is sent, skipped or delivered empty

#### Scenario: An unconfirmed HR match is not claimed
- **WHEN** a record is created for a row whose HEMA Ratings match has only been proposed
- **THEN** the record carries no HR id

#### Scenario: A confirmed HR match carries over
- **WHEN** a record is created for a row whose HEMA Ratings match the organizer has confirmed
- **THEN** the record carries that HR id

#### Scenario: Signing up afterwards is not obstructed
- **WHEN** a person for whom such a record exists signs up for an account with that email
- **THEN** the signup is accepted on the ordinary terms

#### Scenario: Signing up where the record carries no address
- **WHEN** a person whose record carries no address signs up with their own
- **THEN** the signup is accepted and a second, separate record is created
