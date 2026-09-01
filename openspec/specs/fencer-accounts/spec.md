# fencer-accounts Specification

## Purpose
Give fencers portable, globally scoped accounts bound to HEMA Ratings identities, reusable across tournaments.
## Requirements
### Requirement: Account creation with HR binding
The system SHALL offer a self-service registration window, reachable from the login screen, with the fields: email, password, name, and preferred UI language (selected from the implemented localizations). The window SHALL include an optional HEMA Ratings step: it SHALL reuse the form's own name field as the search query (there SHALL NOT be a second name input inside the step), search the fighters index by name, and present candidate profiles (name, nationality, club). Before a candidate is bound, the system SHALL present an explicit ownership confirmation that shows the candidate's details (name, nationality, club, HR id) and a link to that fighter's hemaratings.com profile page opening in a new browser tab, and asks the fencer to confirm the account is theirs; binding SHALL occur only on that confirmation. On confirmation the HR canonical name SHALL become the account display name and be visible in the form before submitting, and a confirmed profile SHALL be clearable before submit. When a profile is confirmed, the form SHALL show a confirmation line carrying the canonical name and the HR id (for example `HEMA Ratings profile confirmed: Petr Lukeš (8956)`). The step SHALL be skippable; an account created without it can be bound later from the Profile page. On successful signup the account SHALL be active immediately (no email verification) and the fencer SHALL be logged in and land on Fencer Home. A duplicate email SHALL be rejected with a clear message.

#### Scenario: Fencer signs up without HEMA Ratings
- **WHEN** a fencer submits the registration window with email, password, name, and a language, skipping the HR step
- **THEN** the account is created with the typed name and chosen language, and the fencer is logged in and lands on Fencer Home

#### Scenario: Name field drives the HR search
- **WHEN** a fencer with a name typed in the form opens the HR step
- **THEN** the step searches by that name without asking for the name again

#### Scenario: Explicit ownership confirmation before binding
- **WHEN** a fencer selects a candidate profile in the HR step
- **THEN** an ownership confirmation is shown with the candidate's name, nationality, club, HR id, and a hemaratings.com profile link opening in a new tab, and the profile is bound only after the fencer confirms it is theirs

#### Scenario: Fencer confirms an HR profile
- **WHEN** a fencer uses the HR step and confirms one of the candidate profiles before submitting
- **THEN** the account stores the hr_id and the HR canonical name, nationality, and club
- **AND** the form showed the canonical name as the account name before submission
- **AND** the confirmation line displayed the canonical name together with the HR id

#### Scenario: Duplicate email rejected
- **WHEN** a fencer submits the registration window with an email that already has an account
- **THEN** the signup is rejected with a message that the email is already registered

#### Scenario: Fencer has no HR profile
- **WHEN** a fencer declares they have no HEMA Ratings profile
- **THEN** the account is created with an empty hr_id
- **AND** the account can be bound to an HR profile later without losing history

### Requirement: Non-exclusive HR profile claims
The system SHALL allow multiple accounts to claim the same HEMA Ratings profile — a claim to an already-claimed profile SHALL NOT be rejected at signup or Profile binding. Wherever HR candidate profiles are presented for claiming, profiles already claimed by another account SHALL be marked with a non-blocking notice so the fencer can recognize they may already have an account. The admin accounts list SHALL flag accounts whose hr_id is shared with at least one other account; resolution remains the existing administrative unbinding.

#### Scenario: Claiming an already-claimed profile succeeds
- **WHEN** a fencer confirms an HR profile that another account has already claimed, at signup or on the Profile page
- **THEN** the claim succeeds exactly as for an unclaimed profile

#### Scenario: Fencer warned about an existing claim
- **WHEN** HR candidate profiles are listed and one of them is already claimed by another account
- **THEN** that candidate carries a visible notice that it is already claimed, and the fencer may still confirm it

#### Scenario: Admin sees duplicate claims
- **WHEN** an Admin opens the accounts list while two accounts share the same hr_id
- **THEN** both accounts are flagged as sharing their HR profile, and the Admin can resolve the duplicate by unbinding the wrong account

### Requirement: Portable profile across tournaments
Fencer accounts SHALL be global, not tournament-scoped, and reusable to register for any tournament in the deployment. Profile changes SHALL be audited.

#### Scenario: Returning fencer registers for a new tournament
- **WHEN** an existing fencer opens registration for another tournament
- **THEN** the registration is prefilled from the account profile without re-entering identity data

### Requirement: Administrative HR unbinding
An Admin SHALL be able to unbind a wrongly linked HEMA Ratings profile from an account: the hr_id is cleared while profile fields keep their current values, and the change is recorded in the profile audit trail. The account can then be bound to the correct profile through the existing binding flow. Fencer-initiated rebinding SHALL remain rejected — the binding stays write-once from the fencer's side.

#### Scenario: Admin unbinds a wrong profile
- **WHEN** an Admin clears the hr_id of an account linked to the wrong HEMA Ratings profile
- **THEN** the hr_id is empty, the unbinding is audited, and the fencer can bind the correct profile

#### Scenario: Fencer still cannot rebind
- **WHEN** a fencer whose account already has an hr_id attempts to bind a different profile
- **THEN** the request is rejected as before

### Requirement: Credential managers can fill and save the account forms
The sign-in and account-creation forms SHALL declare their fields to the browser and to
password managers, so that iCloud Keychain, Google Password Manager and third-party
managers offer to fill an existing credential and to save a newly created one.

Each field SHALL carry a `name` and the autocomplete purpose it serves. The e-mail
field SHALL declare itself the account identifier on **both** forms — including
account creation, where it is the signal that makes a manager offer to save the new
pair — and SHALL additionally suppress autocapitalisation, autocorrection and
spellcheck, and request an e-mail keyboard. The password field SHALL declare the
current password on sign-in and a new password on account creation. The display-name
field SHALL declare itself a name and capitalise words.

Sign-in and account creation SHALL each render their own `<form>` element carrying its
own stable `id`, so a manager's heuristics have a durable identity for each and cannot
attribute one form's fields to the other.

#### Scenario: Returning fencer signs in on a phone
- **WHEN** a fencer with a saved credential opens the sign-in form on a mobile browser
- **THEN** the password manager offers to fill the e-mail and password, and accepting it fills both

#### Scenario: Password offered for saving after account creation
- **WHEN** a fencer completes the account-creation form
- **THEN** the browser or password manager offers to save the e-mail and password as a pair

#### Scenario: E-mail field keyboard and text handling
- **WHEN** a fencer focuses the e-mail field on a touch device
- **THEN** an e-mail keyboard is presented and the entry is neither autocapitalised, autocorrected, nor spellchecked

#### Scenario: The two forms are distinguishable
- **WHEN** the sign-in form and the account-creation form are inspected
- **THEN** each is its own `<form>` with its own stable `id`

### Requirement: The account forms do not summon a keyboard before they are read
A field SHALL take focus automatically on load only at viewport widths of 768px and
above. On a narrower viewport, the on-screen keyboard raised by an automatic focus
covers the form and pushes its heading and its first fields out of view before they
can be read — most severely on account creation, which is the longer form.

The viewport width SHALL be resolved once when the form mounts, not re-evaluated during
rendering, so that focus behaviour cannot change under a resize while the fencer is
typing.

#### Scenario: Sign-in opens on a phone
- **WHEN** the sign-in form is opened on a 390px-wide viewport
- **THEN** no field takes focus automatically and no keyboard appears until the fencer taps a field

#### Scenario: Sign-in opens on a desktop
- **WHEN** the sign-in form is opened at 1024px or wider
- **THEN** the e-mail field takes focus automatically as before

### Requirement: A submission in flight is stated in words
WHILE a sign-in or account-creation request is in flight, the submit control SHALL
state so by changing its own label to a progress wording, in addition to being
disabled. The wording SHALL exist in every supported language.

A disabled control whose label does not change gives no feedback across the seconds a
mobile connection can take, and the fencer taps again. The statement SHALL be static
text: no spinner, no animated indicator, and no progress bar, per the design
prohibitions.

#### Scenario: Slow sign-in on a mobile connection
- **WHEN** a fencer submits the sign-in form and the response takes two seconds
- **THEN** the submit control is disabled and its label reads the progress wording for the whole interval, with no animated indicator

#### Scenario: Submission completes
- **WHEN** the request finishes, whether it succeeded or failed
- **THEN** the submit control returns to its resting label

### Requirement: An error appearing does not move the submit control
The space an error message occupies on the account forms SHALL be reserved in the
layout, so that the message appearing does not displace the submit control.

On a touch device a control that moves between the moment a person aims and the moment
they tap is a control they miss, and a failed sign-in is exactly when a second tap is
most likely.

#### Scenario: Sign-in rejected
- **WHEN** a fencer submits invalid credentials and the error message appears
- **THEN** the submit control stays at the same position on screen as before the message appeared

### Requirement: Finding an HR profile during account creation is its own step on a narrow screen
Below 768px, the HEMA Ratings profile search offered during account creation SHALL be
presented as a full-screen step layered over the form, rather than expanded inline
within it. Inline, the form grows past three screens with a search field and its
results in the middle, and the fencer loses track of what they were filling in.

Entering and leaving the step SHALL NOT navigate to a different screen and SHALL NOT
unmount the form: everything already entered — e-mail, password, name and language —
SHALL be present and unchanged on return. Confirming a candidate SHALL return to the
form and fill in the name, exactly as the inline flow does.

Because the step searches by the name already held in the form and offers no query
field of its own, it SHALL display the name it is searching for, so the fencer is not
presented with a nationality control and a search action with nothing stating what is
being searched.

At 768px and above the search SHALL remain inline in the form, unchanged.

#### Scenario: Finding a profile mid-signup on a phone
- **WHEN** a fencer on a 390px viewport has filled in e-mail, password and name and opens the HR profile search
- **THEN** the search covers the screen as its own step and states the name it is searching for

#### Scenario: Form survives the step
- **WHEN** that fencer confirms a candidate and returns to the form
- **THEN** the e-mail, password and language they had entered are unchanged, and the name is filled from the confirmed profile

#### Scenario: Leaving the step without choosing
- **WHEN** the fencer backs out of the step without confirming a candidate
- **THEN** the form returns with every entered value intact and no profile bound

#### Scenario: Desktop behaviour unchanged
- **WHEN** the HR profile search is opened at 1024px
- **THEN** it appears inline within the form as before

