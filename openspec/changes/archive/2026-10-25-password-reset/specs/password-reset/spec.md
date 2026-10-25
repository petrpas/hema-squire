## ADDED Requirements

### Requirement: A forgotten password is reset through a mailed link
The sign-in screen SHALL offer a "Forgot password" action. It SHALL replace the sign-in form, in place, as account creation does, with one that asks for an e-mail address, prefilled with whatever the sign-in form's e-mail field held. It SHALL NOT navigate: sign-in renders over the URL the visitor is to return to, and leaving it would lose that place.

Where the address belongs to an account (a fencer record holding it **and** credentials), submitting SHALL mail a reset link to that address, in the account's language. The screen SHALL then state that the link was sent to that address and how long it works. Nothing about the account SHALL change until the link is followed: the current password SHALL keep working.

Where the address belongs to no account, the screen SHALL say so plainly and offer account creation. This covers an address no record holds, an address held by a record without credentials (one issued from a roster, entered by hand or entered as a guest), and an address whose signup is still pending. No mail SHALL be sent. Signup's refusal already reveals whether an address has an account, so a uniform answer would hide nothing. A record without credentials is turned into an account by verified signup, which takes it over, so creating an account is the way forward there and not a reset.

Requests SHALL be rate-limited.

#### Scenario: Requesting a reset
- **WHEN** a fencer with an account selects Forgot password on the sign-in screen and submits their address
- **THEN** a reset link is mailed to that address, the screen states that it was sent and that it works for one hour, and the old password still signs in

#### Scenario: The sign-in address carries over
- **WHEN** a fencer has typed their address into the sign-in form and selects Forgot password
- **THEN** the reset screen's address field holds that address

#### Scenario: An address without an account
- **WHEN** the address submitted is held by no record
- **THEN** the screen states that no account uses this address and offers account creation, and no mail is sent

#### Scenario: A roster-issued record is not reset
- **WHEN** the address submitted is held by a record without credentials
- **THEN** the screen states that no account uses this address and offers account creation, and no mail is sent

#### Scenario: A pending signup is not reset
- **WHEN** the address submitted has a signup still pending verification and no account
- **THEN** the screen states that no account uses this address and offers account creation, and no mail is sent

### Requirement: The reset link sets a new password once
The reset link SHALL open a screen asking for a new password, under the same minimum length as account creation. Saving it SHALL set the account's password, sign the fencer in on that browser and land them on Fencer Home.

A link SHALL work once. It SHALL expire one hour after it was mailed. A newer request for the same account SHALL replace it: only the most recently mailed link works. A used, expired or replaced link SHALL lead to a static statement that it is no longer valid, offering a new request. It SHALL NOT be presented as an error.

The link SHALL carry its key in a part of the URL the browser does not send to the server. The key SHALL be stored only as a hash.

A reset SHALL be recorded in the account's profile audit trail. The new password itself SHALL NOT be recorded.

The new-password form SHALL declare its field as a new password to password managers and SHALL carry the account's e-mail as the identifier the credential is saved under, so a manager offers to update the saved credential.

#### Scenario: Following the link
- **WHEN** a fencer follows a reset link within the hour and saves a new password
- **THEN** the new password signs in, the old one no longer does, the fencer is signed in on that browser and lands on Fencer Home

#### Scenario: A link works once
- **WHEN** a reset link that has already been used is followed again
- **THEN** the statement that the link is no longer valid is shown, with a new request offered, and the password is unchanged

#### Scenario: An expired link
- **WHEN** a reset link is followed 61 minutes after it was mailed
- **THEN** the statement that the link is no longer valid is shown, with a new request offered

#### Scenario: The latest request wins
- **WHEN** a fencer requests a reset twice and follows the first link
- **THEN** the first link is no longer valid, and the second one still works

#### Scenario: Too short a password
- **WHEN** the new password is shorter than the minimum account creation requires
- **THEN** it is refused in place, and the link remains usable

#### Scenario: A password manager updates the credential
- **WHEN** a fencer saves a new password on the reset screen
- **THEN** the password manager offers to update the credential saved for the account's e-mail

### Requirement: Changing the password ends every other session
Whenever an account's password is changed, by a reset or on the Profile page, every session signed in before the change SHALL stop being accepted. The browser that made the change SHALL remain signed in with a new session. A refused session SHALL be treated like an expired one: the visitor is shown sign-in at the URL they were on.

Accounts whose password has never been changed this way SHALL keep their existing sessions. Introducing this rule SHALL sign nobody out.

#### Scenario: A reset signs out another device
- **WHEN** a fencer signed in on a laptop resets their password from a phone
- **THEN** the laptop's next request is refused as signed out, and the phone stays signed in

#### Scenario: Deploying the rule signs nobody out
- **WHEN** this change is deployed while fencers are signed in
- **THEN** their sessions keep working until they expire as before
