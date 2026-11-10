## ADDED Requirements

### Requirement: An account holder can request deletion of their account
A signed-in account SHALL be able to request its deletion. Before confirming, the system SHALL state the impact: the registrations that will be cancelled with what has been credited on them, the number of held rosters where the name, HR ID, club and nationality will stay, that copies held by organizers are out of reach, and any reason deletion is refused. The request SHALL require the current password. A message SHALL confirm the request and its execution date.

#### Scenario: Confirmed by password
- **WHEN** an account confirms deletion with its correct password
- **THEN** the request is recorded and the account is mailed the date it takes effect

#### Scenario: Wrong password
- **WHEN** the password is wrong
- **THEN** no request is recorded

### Requirement: Deletion takes effect after seven days and can be withdrawn
A requested deletion SHALL execute 7 days after the request. Until then the account SHALL work normally and its holder SHALL be able to withdraw the request. A withdrawal SHALL leave no effect on data and SHALL be confirmed by mail.

#### Scenario: Withdrawn
- **WHEN** the holder withdraws on day 3
- **THEN** no deletion happens and the account is unchanged

#### Scenario: Executed
- **WHEN** a scheduler pass runs after day 7 with no request withdrawn
- **THEN** the deletion executes and a final message is sent to the address it had

### Requirement: Deletion is refused while the account holds responsibility
A deletion SHALL be refused while the account owns any tournament, is the last Admin, or is the Deployment Owner. The refusal SHALL state what has to change first. Where such a condition arises during the seven days, execution SHALL wait, the request SHALL stay pending and SHALL be shown among the Admin's pending tasks.

#### Scenario: Owner of a tournament
- **WHEN** an account owning a tournament requests deletion
- **THEN** it is refused, naming the tournament and that ownership must be transferred first

#### Scenario: Ownership acquired during the grace period
- **WHEN** the account has become an owner by the execution date
- **THEN** nothing is deleted and the request appears in the Admin's pending tasks

### Requirement: Execution ends the account and removes what identifies a login
On execution the system SHALL remove the address, password, language preference and pending password reset, end every session, delete the profile audit trail and organizer requests, remove console team memberships, return the role to fencer and mark the record deleted. A later signup with the same address SHALL create a new account unconnected to the deleted record.

#### Scenario: A session stops working
- **WHEN** a token issued before execution is presented
- **THEN** it is refused

#### Scenario: Signing up again
- **WHEN** the same address signs up after execution
- **THEN** a new account exists, holding none of the earlier registrations

### Requirement: A name stays only where a held roster lists it
A deleted record with a live registration on a tournament dated before today SHALL keep its name, HR ID, club and nationality. A deleted record with none SHALL have those fields blanked and SHALL read as a deleted account.

#### Scenario: Fenced last year
- **WHEN** an account that competed last year is deleted
- **THEN** that tournament's roster still lists its name, HR ID, club and nationality

#### Scenario: Never competed
- **WHEN** an account with no held registration is deleted
- **THEN** no name, HR ID, club or nationality remains on the record

### Requirement: Registrations not yet held are cancelled and the organizer is told
On execution, every live registration of the account on a tournament dated today or later SHALL be cancelled as any other cancellation is. The tournament's owner SHALL be sent a message naming the person, the variable symbol and the amount credited. Money SHALL NOT be moved and no one SHALL be promoted.

#### Scenario: Paid entry
- **WHEN** an account with a paid entry to a future tournament is deleted
- **THEN** the seat is freed and the owner's message states the person, variable symbol and credited amount

### Requirement: The address is removed from the copies it can be found in
On execution the system SHALL remove every address the account has held from imported rows, manual rows, rule payloads, the rule journal, the account's own registrations and outgoing messages, and from actor labels in the payment journals, whose name part SHALL remain. The account's own registrations SHALL lose their notes, accommodation and contact address. Amounts, variable symbols and journal entries SHALL remain. A contact address on another person's seat SHALL NOT be removed.

#### Scenario: Former address
- **WHEN** an account changed its address once and is deleted
- **THEN** neither address remains in imported rows, rules or journals

#### Scenario: Organizer's journal label
- **WHEN** a former organizer's deleted account recorded a payment
- **THEN** the entry stays and names them without an address

### Requirement: An Admin can erase an identity on request
An Admin SHALL be able to erase the name, HR ID, club and nationality of any fencer record, with explicit confirmation, for an upheld objection or a request from a person without an account. It SHALL also remove rules correcting that record's name and journal copies of them, and SHALL leave money untouched. Rosters SHALL then show the record as a deleted account.

#### Scenario: Objection upheld
- **WHEN** an Admin erases a deleted record's identity
- **THEN** every roster shows the deleted label and no HR link for that row

### Requirement: Deleted records are distinguished from accounts
A deleted record SHALL NOT count toward shared HR IDs and SHALL appear on the admin people list marked as deleted, so that it can be found for erasure and is not mistaken for an account. A deleted record SHALL NOT be reused by enrolment or matching onto a new tournament.

#### Scenario: Returning fencer binds the same profile
- **WHEN** a new account binds the HR ID a deleted record holds
- **THEN** no shared HR ID task appears

### Requirement: A restore reapplies erasures
Each erasure SHALL be recorded without personal data. Restoring the database to an earlier point SHALL reapply every erasure recorded in the latest available state before the service reopens.

#### Scenario: Restore to last week
- **WHEN** the database is restored to a point before an execution
- **THEN** the account is erased again before anyone can reach it
