## ADDED Requirements

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
