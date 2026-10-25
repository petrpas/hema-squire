## ADDED Requirements

### Requirement: Password change
The account section SHALL offer a "Change the password" link on the line of its heading, aligned to the right, presented as a quiet link rather than a section or a button of its own, since hardly any account uses it. Following it SHALL open a dialog asking for the current password and a new one. No password field SHALL exist on the page before the link is followed: a password manager fills such a field the moment the profile loads, which reads as the page displaying the password.

The new password SHALL meet the same minimum length as account creation. A wrong current password SHALL be refused in the dialog, without signing the account out.

A successful change SHALL close the dialog, state the outcome on the page as static text, and end every other session, as `password-reset` requires. It SHALL be recorded in the profile audit trail, without the password. It SHALL mail a notice to the account's address, in the account's language, stating that the password was changed, and that whoever did not make the change should reset it through Forgot password. The notice is sent because anyone at a browser already signed in can make this change, and the address is how the account's owner learns of it.

The dialog's fields SHALL declare the current and the new password to password managers, alongside the account's address as the identifier.

#### Scenario: Opening the profile fills in no password
- **WHEN** an account with a saved credential opens the Profile page
- **THEN** the account section shows the "Change the password" link, and no password field exists for a password manager to fill

#### Scenario: Changing the password
- **WHEN** a signed-in fencer follows the link, enters their current password and a valid new one, and saves
- **THEN** the dialog closes and the change is stated, the new password signs in, other sessions are signed out, this browser stays signed in, and a notice is mailed to the account's address

#### Scenario: Wrong current password
- **WHEN** the current password entered in the dialog is wrong
- **THEN** the change is refused in the dialog, the password is unchanged, the fencer stays signed in, and no notice is sent

## MODIFIED Requirements

### Requirement: HEMA Ratings section — bound state
WHEN the account is bound to a HEMA Ratings profile, the section SHALL display the HRID, HR canonical name, club, and nationality. The HRID itself SHALL be the link to the fighter's hemaratings.com profile page, opening in a new tab and marked as leading outside the application, as an HRID is in the entrant rosters; there SHALL NOT be a separate link line beneath the fields. No rebinding controls SHALL be offered (binding is write-once from the fencer's side per fencer-accounts).

#### Scenario: Bound profile shown with link
- **WHEN** an account with a bound hr_id opens the Profile page
- **THEN** the HEMA Ratings section shows HRID, name, club, and nationality, and the HRID is a working link to the hemaratings.com profile marked as external
