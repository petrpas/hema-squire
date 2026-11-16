## MODIFIED Requirements

### Requirement: Account information section
The account section SHALL display the account's email and full (display) name. The full name SHALL be editable through the account-update contract, with changes audited per fencer-accounts. The email SHALL be shown read-only and SHALL change only through the address change, as **Address change** requires. The account-update contract SHALL refuse an address.

#### Scenario: Rename
- **WHEN** the user edits the full name and saves
- **THEN** the account's display name is updated and the change is recorded in the profile audit trail

#### Scenario: The address is not an ordinary edit
- **WHEN** an account-update request carries an e-mail address
- **THEN** it is refused, and neither the address nor any other field of that request is changed

## ADDED Requirements

### Requirement: Address change
The account section SHALL offer a "Change the address" link beside the address, presented as a quiet link, as the password change is. Following it SHALL open a dialog asking for the current password and the new address.

A wrong current password SHALL be refused in the dialog without signing the account out. An address already held by any other record in Squire, an account or a registration record without credentials, SHALL be refused in the dialog. Otherwise a confirmation link SHALL be mailed to the new address, in the account's language, and the dialog SHALL state that the link was sent there and works for one hour. The account's address SHALL NOT change until the link is followed: sign-in, mail and every grant made by address keep using the old one. Requests SHALL be rate-limited.

A link SHALL work once and SHALL expire one hour after it was mailed. A newer request SHALL replace it. The key SHALL travel in a part of the URL the browser does not send to the server and SHALL be stored only as a hash. A used, expired or replaced link SHALL lead to a static statement that it is no longer valid. A link whose address another record has taken in the meantime SHALL lead to a static statement that the address is taken, and nothing changes.

Following a valid link SHALL set the account's address, record the change in the profile audit trail, end every session signed in before it, sign the browser that followed the link in, and mail a notice to the old address. The notice SHALL name the new address and say that whoever did not make the change should write to the contact stated on the privacy page.

#### Scenario: Requesting an address change
- **WHEN** a signed-in fencer enters their current password and a new address no account holds
- **THEN** a link is mailed to the new address, the dialog states that it was sent and works for one hour, and the account still signs in with the old address

#### Scenario: Wrong current password
- **WHEN** the current password entered in the dialog is wrong
- **THEN** the change is refused in the dialog, no link is mailed, and the fencer stays signed in

#### Scenario: An address another record holds
- **WHEN** the new address belongs to another account, or to a guest's or roster record without credentials
- **THEN** the change is refused in the dialog and no link is mailed

#### Scenario: Following the link
- **WHEN** the link is followed within the hour
- **THEN** the account's address is the new one, the change is in the audit trail, other sessions are signed out, the browser that followed the link is signed in, and the old address receives a notice naming the new one

#### Scenario: A link works once
- **WHEN** a link that has already been used, or replaced by a newer request, is followed
- **THEN** the statement that the link is no longer valid is shown and the address is unchanged

#### Scenario: An expired link
- **WHEN** a link is followed 61 minutes after it was mailed
- **THEN** the statement that the link is no longer valid is shown and the address is unchanged

#### Scenario: The address was taken meanwhile
- **WHEN** another record takes the new address before the link is followed
- **THEN** following the link states that the address is taken, and the account keeps its old address
