## MODIFIED Requirements

### Requirement: Account creation with HR binding
The system SHALL offer a self-service registration window, reachable from the login screen, with the fields: email, password, name, and preferred UI language (selected from the implemented localizations). The window SHALL include an optional HEMA Ratings step: it SHALL reuse the form's own name field as the search query (there SHALL NOT be a second name input inside the step), search the fighters index by name, and present candidate profiles (name, nationality, club). Before a candidate is bound, the system SHALL present an explicit ownership confirmation that shows the candidate's details (name, nationality, club, HR id) and a link to that fighter's hemaratings.com profile page opening in a new browser tab, and asks the fencer to confirm the account is theirs; binding SHALL occur only on that confirmation. On confirmation the HR canonical name SHALL become the account display name and be visible in the form before submitting, and a confirmed profile SHALL be clearable before submit. When a profile is confirmed, the form SHALL show a confirmation line carrying the canonical name and the HR id (for example `HEMA Ratings profile confirmed: Petr Lukeš (8956)`). The step SHALL be skippable; an account created without it can be bound later from the Profile page.

Submitting the window SHALL NOT create the account and SHALL NOT sign the fencer in. It SHALL record a pending signup and mail a verification link to the address given, and the window SHALL then state, in place of the form, that a link has been sent to that address and must be followed to finish creating the account. The account SHALL come into existence only when the link is followed, as fixed by `An account exists only once its address is verified`, and the fencer SHALL then be signed in and land on the screen the signup was started from, or on Fencer Home where it was started from none.

An address that belongs to an account SHALL be rejected at submission with a clear message. An address held only by a fencer record without credentials SHALL NOT be rejected. The signup SHALL proceed, and its verification SHALL take that record over (`A fencer record may exist without an account`).

#### Scenario: Fencer signs up without HEMA Ratings
- **WHEN** a fencer submits the registration window with email, password, name, and a language, skipping the HR step
- **THEN** no account exists yet, a verification link is mailed to the address, and the window states that the link must be followed

#### Scenario: Following the link finishes the signup
- **WHEN** that fencer follows the verification link
- **THEN** the account exists with the typed name and chosen language, and the fencer is signed in and lands on Fencer Home

#### Scenario: Signup started from a tournament returns there
- **WHEN** a visitor who selected Register on a tournament creates an account and follows the verification link
- **THEN** they are signed in and shown that tournament's detail on its registration tab

#### Scenario: Name field drives the HR search
- **WHEN** a fencer with a name typed in the form opens the HR step
- **THEN** the step searches by that name without asking for the name again

#### Scenario: Explicit ownership confirmation before binding
- **WHEN** a fencer selects a candidate profile in the HR step
- **THEN** an ownership confirmation is shown with the candidate's name, nationality, club, HR id, and a hemaratings.com profile link opening in a new tab, and the profile is bound only after the fencer confirms it is theirs

#### Scenario: Fencer confirms an HR profile
- **WHEN** a fencer uses the HR step, confirms one of the candidate profiles before submitting, and follows the verification link
- **THEN** the account stores the hr_id and the HR canonical name, nationality, and club
- **AND** the form showed the canonical name as the account name before submission
- **AND** the confirmation line displayed the canonical name together with the HR id

#### Scenario: Duplicate email rejected
- **WHEN** a fencer submits the registration window with an email that already belongs to an account
- **THEN** the signup is rejected with a message that the email is already registered, and nothing is mailed

#### Scenario: Fencer has no HR profile
- **WHEN** a fencer declares they have no HEMA Ratings profile and verifies the signup
- **THEN** the account is created with an empty hr_id
- **AND** the account can be bound to an HR profile later without losing history

### Requirement: A fencer record may exist without an account
A fencer record SHALL be able to exist without an account. Where the organizer
enrols a tournament's own roster — issuing registrations for rows that state who
is competing — the fencer records those registrations need SHALL be created on
the tournament's behalf. A visitor registering without signing up
(`guest-registration`) SHALL likewise be held on such a record.

Such a record SHALL hold no credentials and SHALL NOT be usable to log in. Its
creation SHALL send no mail: no invitation, no welcome, no notice that a record
exists. A person SHALL learn of it, if at all, from the organizer, or, for a
guest, from the messages about their own registration.

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
the record existing. **Where the record carries the address the person signs up
with, the verified signup SHALL take the record over** rather than create a
second one. The record gains the signup's credentials and language and becomes
an account, and every registration it holds stays with it. Its HEMA Ratings
binding SHALL be kept where it has one. Where it has none, the profile confirmed
in the signup SHALL be bound. The display name SHALL become the one the signup
gives. Each changed field SHALL be recorded in the profile audit trail. The
takeover SHALL happen only on verification: the address is what proves the
record is the signer's, and an unverified signup proves nothing.

Where the record carries no address there is nothing for the signup to recognise,
and a second record SHALL be created — the person's own, carrying no history from
the first. A registration that only carries the address as its contact address
SHALL NOT be taken over by it, since a contact address is not an identity
(`registration`). It stays a guest registration, managed through its link.
Reconciling the two is not addressed here.

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
- **WHEN** a person for whom such a record exists, holding their address, signs up for an account with that address
- **THEN** the signup is accepted and a verification link is mailed

#### Scenario: Verification takes the record over
- **WHEN** that person follows the verification link
- **THEN** the record holds the signup's credentials and language and can be signed into, it is the same record with the same registrations, and no second record exists for the address

#### Scenario: A bound record keeps its binding
- **WHEN** a record bound to one HEMA Ratings profile is taken over by a signup that confirmed a different one
- **THEN** the record's original binding stands

#### Scenario: Signing up where the record carries no address
- **WHEN** a person whose record carries no address signs up with their own
- **THEN** the signup is accepted, and on verification a second, separate record is created

## ADDED Requirements

### Requirement: An account exists only once its address is verified
A signup SHALL be held as pending until the verification link mailed to its address is followed. A pending signup SHALL NOT be a fencer record, SHALL NOT be signed into, and SHALL NOT be visible on any surface other than the sign-in screen's answer to its own address.

Following the link SHALL, in one step, create the account from what the signup gave, or take over the record without credentials that holds the address. It SHALL sign the fencer in and consume the pending signup. A link SHALL work once. It SHALL expire 48 hours after it was mailed. An expired or consumed link SHALL lead to a static statement that it is no longer valid, offering sign-in and account creation. It SHALL NOT be presented as an error.

A second signup on an address that is still pending SHALL replace the first: the earlier link SHALL stop working, and only the latest signup's password, name and choices SHALL be used. Otherwise somebody who mistyped their address, or somebody else, would hold an address its owner could not sign up with for as long as the first link lived.

Sign-in on an address whose signup is still pending SHALL state that the address has not yet been verified, and SHALL offer to send the link again. Sending it again SHALL mail a fresh link that replaces the previous one, and SHALL be rate-limited.

The verification link SHALL carry its key in a part of the URL the browser does not send to the server. The key SHALL be stored only as a hash.

Every account that existed before verification was introduced SHALL count as verified, and none SHALL be asked to verify.

#### Scenario: A pending signup cannot sign in
- **WHEN** a fencer who submitted a signup and has not followed the link tries to sign in
- **THEN** sign-in is refused with the statement that the address is not yet verified, and sending the link again is offered

#### Scenario: Resending the link
- **WHEN** that fencer asks for the link again
- **THEN** a fresh link is mailed, and the previous one no longer works

#### Scenario: A link works once
- **WHEN** a verification link that has already been followed is followed again
- **THEN** the statement that the link is no longer valid is shown, and no second account exists

#### Scenario: An expired link
- **WHEN** a verification link is followed 49 hours after it was mailed
- **THEN** the statement that the link is no longer valid is shown, with sign-in and account creation offered

#### Scenario: The latest signup wins
- **WHEN** two signups are submitted on one address before either is verified, and the first one's link is followed
- **THEN** that link is no longer valid, and only the second one's link creates the account, with the second signup's password

#### Scenario: Existing accounts are unaffected
- **WHEN** a fencer whose account was created before this change signs in
- **THEN** they are signed in as before, with no verification asked of them

### Requirement: The account form has a guest variant
The account-creation form SHALL also serve a visitor registering without signing up (`guest-registration`). The guest variant SHALL be the same form with its own heading and subtitle and without the password field. It SHALL render as its own `<form>` with its own stable `id`. Its e-mail field SHALL declare itself an e-mail address rather than an account identifier, so that no password manager offers to save a credential that does not exist. The HEMA Ratings step, its ownership confirmation and the narrow-screen step SHALL behave in it exactly as in the account variant.

Completing the guest variant SHALL mail nothing and SHALL record no pending signup.

#### Scenario: Guest form has no password
- **WHEN** a visitor opens the guest variant
- **THEN** it shows the e-mail, name, language and HEMA Ratings step under its own heading, has no password field, and is a `<form>` with an `id` distinct from sign-in's and account creation's

#### Scenario: No credential offered for saving
- **WHEN** a visitor completes the guest variant
- **THEN** no password manager offers to save a credential, and no verification mail is sent
