# profile-page Specification

## Purpose
Provide a Profile page where every logged-in account can view and manage its account information, role and organizer plea status, and HEMA Ratings binding, reachable from every logged-in page via a shared account menu.
## Requirements
### Requirement: Profile page access
Every logged-in account SHALL have a Profile page presenting three sections: account information, role, and HEMA Ratings profile. The page SHALL be reachable from every logged-in surface via the account menu.

#### Scenario: Fencer opens profile
- **WHEN** any logged-in account selects My Profile from the account menu
- **THEN** the Profile page opens showing account information, role, and HEMA Ratings sections

### Requirement: Account information section
The account section SHALL display the account's email and full (display) name. The full name SHALL be editable through the account-update contract, with changes audited per fencer-accounts. The email SHALL be shown read-only and SHALL change only through the address change, as **Address change** requires. The account-update contract SHALL refuse an address.

#### Scenario: Rename
- **WHEN** the user edits the full name and saves
- **THEN** the account's display name is updated and the change is recorded in the profile audit trail

#### Scenario: The address is not an ordinary edit
- **WHEN** an account-update request carries an e-mail address
- **THEN** it is refused, and neither the address nor any other field of that request is changed

### Requirement: Role section
The role section SHALL display the account's effective role as one of Fencer, Organizer, Admin, or Owner. The deployment Owner (config-computed) SHALL be shown as Owner regardless of stored role. For accounts whose effective role is plain Fencer, the section SHALL embed the organizer plea flow: a request button with optional message, pending status, and denied status with re-plead, per the user-roles plea workflow.

#### Scenario: Owner sees Owner
- **WHEN** the account whose email equals the configured owner email opens the Profile page
- **THEN** the role section shows Owner

#### Scenario: Fencer pleads from profile
- **WHEN** a Fencer without a pending plea submits the organizer request from the role section
- **THEN** the plea is created and the section shows pending status

#### Scenario: Organizer sees no plea
- **WHEN** an account with Organizer role or higher opens the Profile page
- **THEN** the role section shows the role without any plea controls

### Requirement: HEMA Ratings section — bound state
WHEN the account is bound to a HEMA Ratings profile, the section SHALL display the HRID, HR canonical name, club, and nationality. The HRID itself SHALL be the link to the fighter's hemaratings.com profile page, opening in a new tab and marked as leading outside the application, as an HRID is in the entrant rosters; there SHALL NOT be a separate link line beneath the fields. No rebinding controls SHALL be offered (binding is write-once from the fencer's side per fencer-accounts).

#### Scenario: Bound profile shown with link
- **WHEN** an account with a bound hr_id opens the Profile page
- **THEN** the HEMA Ratings section shows HRID, name, club, and nationality, and the HRID is a working link to the hemaratings.com profile marked as external

### Requirement: HEMA Ratings section — find and match
WHEN the account has no bound HR profile, the section SHALL offer a find-and-match flow: the user first narrows by nationality, then searches by name; candidates are listed with HRID, name, club, and nationality, ranked by name similarity. Confirming a candidate SHALL bind it through the existing binding contract (one account per hr_id; audited).

Below 768px the flow SHALL be presented as a full-screen step layered over the Profile page rather than expanded within the section, and SHALL offer a way back from that step without binding. Entering and leaving the step SHALL NOT navigate to a different screen and SHALL NOT discard anything the fencer has edited elsewhere on the page.

The step SHALL be the same component the account-creation form uses for its own HR search, not a second implementation of it. The two differ in what they supply — account creation searches by the name held in its form and offers no query field, while the Profile page offers its own query field seeded with the account's display name — and the step SHALL carry that difference through rather than flatten it.

At 768px and above the flow SHALL remain within the section, unchanged.

#### Scenario: Find, match, bind
- **WHEN** an unbound user picks a nationality, enters a name, and confirms one of the listed candidates
- **THEN** the account stores that hr_id with the HR canonical name, club, and nationality, and the section switches to the bound state

#### Scenario: Candidate already bound elsewhere
- **WHEN** the user confirms a candidate whose hr_id is already bound to another account
- **THEN** the binding is rejected and the section explains the conflict

#### Scenario: Finding a profile from Profile on a phone
- **WHEN** an unbound fencer opens the HR search from their Profile page at 390px
- **THEN** the search covers the screen as its own step, carrying its own query field seeded with their display name, and offers a way back

#### Scenario: Backing out of the step
- **WHEN** the fencer leaves the step without confirming a candidate
- **THEN** the Profile page returns with nothing bound and nothing they had edited lost

#### Scenario: One implementation across both surfaces
- **WHEN** the full-screen HR step is used from account creation and from the Profile page
- **THEN** both render the same component, each supplying its own query behaviour

#### Scenario: Desktop behaviour unchanged
- **WHEN** the HR search is opened from the Profile page at 1024px
- **THEN** it appears within the section as before

### Requirement: Account menu
Every logged-in page SHALL show an account menu ("⋯") in the top-right corner containing: My Profile; Admin Panel (only for Admin and Owner); My tournaments, leading to the tournament picker and shown only where the account holds at least one tournament it may open a console on; Create tournament, shown only where the account may create one; and Logout. Account actions SHALL be consolidated in this menu.

The menu SHALL NOT carry an entry back to the fencer's own screens. The application's name in the top bar is that way back, present on the fencer's screens and on the pages the menu leads to, and reachable without opening a menu.

Each entry SHALL be named for what it leads to rather than for whom it is meant: an entry that names an audience tells an account holding both roles nothing about which of its two lists it is about to open.

#### Scenario: Menu navigation
- **WHEN** a logged-in user opens the account menu and selects My Profile
- **THEN** the Profile page opens, from any logged-in surface

#### Scenario: The picker entry where there is nothing to pick
- **WHEN** an account that owns no tournament and sits on no console team opens the account menu
- **THEN** no My tournaments entry is shown, creation being the only way to a first tournament

#### Scenario: The picker entry where there is something to pick
- **WHEN** an account holding one tournament opens the account menu
- **THEN** a My tournaments entry is shown, leading to the picker

#### Scenario: Admin entry hidden for fencers
- **WHEN** an account below Admin (and not Owner) opens the account menu
- **THEN** no Admin Panel entry is shown

### Requirement: Leaving a page reached from the account menu
The Profile page, the admin panel and the tournament picker (My tournaments) SHALL carry the same top bar as the fencer's screens (`fencer-home`, Fencer identity header): the application's name at the left, leading to the tournament list, the list's title at the centre, and the visitor with the account menu at the right. Each page's skin stays its own (`design-system`, Skins): the Profile page night, the admin panel and the picker day.

Each SHALL also carry a close control at the right of its card's heading, returning to the screen the page was opened from, or to the tournament list where the page was reached by its address and there is no screen of this application to return to. Escape SHALL do the same, except while a field has focus — the key then belongs to the field, and leaving would drop what was being typed — and except while something stands over the page, such as a dialog or the full-screen HR search step, which Escape closes first.

#### Scenario: Closing the profile opened from a console
- **WHEN** an organizer opens My Profile from the account menu in a console and selects the close control
- **THEN** the console returns

#### Scenario: Escape leaves the profile
- **WHEN** a fencer on the Profile page presses Escape with no field focused and nothing open over the page
- **THEN** the page closes as by its close control

#### Scenario: Escape in a field stays
- **WHEN** the fencer presses Escape while editing their name
- **THEN** the Profile page stays, with the edit in place

#### Scenario: Escape closes the HR step first
- **WHEN** the full-screen HR search step is open over the Profile page and the fencer presses Escape
- **THEN** the step closes and the Profile page remains

#### Scenario: Reached by its address
- **WHEN** a fencer opens the Profile page directly by its address and selects the close control
- **THEN** the tournament list opens

### Requirement: Bootstrap owner account
The deployment bootstrap SHALL create the account petr.pascenko@gmail.com (Petr Paščenko) with the Organizer role and the configured password, and the dev environment SHALL set the owner email configuration to petr.pascenko@gmail.com, making the account the deployment Owner with Organizer and inherent Fencer capabilities. Seeding SHALL be idempotent.

#### Scenario: Owner logs in
- **WHEN** petr.pascenko@gmail.com logs in with the seeded password in the dev environment
- **THEN** the Profile page role section shows Owner and tournament creation is available

### Requirement: The Profile page wears the night skin
The Profile page SHALL render in the night skin (`design-system`, Skins), for every account that opens it, organizer or fencer: a fencer reaches it from the account menu of a night screen, and the skin follows the route, not the role. Its form fields SHALL keep their 2px geometry and bottom-rule treatment, as every form does in either skin.

#### Scenario: A fencer opens the profile from the list
- **WHEN** a fencer selects My Profile from the account menu on the tournament list
- **THEN** the Profile page renders night, with no day paper visible

#### Scenario: An organizer opens the profile from the console
- **WHEN** an organizer selects My Profile from the account menu in a console
- **THEN** the Profile page renders night, and returning to the console renders it day

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

### Requirement: The Profile page has a Privacy tab
The Profile page SHALL be split into two tabs, `Profile` and `Privacy`, the first selected by default. The Privacy tab SHALL have an address of its own, so that the privacy notice and a message can lead to it. It SHALL hold everything about the account's personal data in one place:

- who is responsible and the contact for requests, with a link to the full privacy notice (`privacy`);
- the download of the account's own data (`privacy`, An account holder can download their own data);
- account deletion, opening a dialog that states the impact and asks for the password. While a deletion is pending the tab SHALL state the date it takes effect and SHALL offer withdrawal;
- for an account that has accepted the organizer data terms or owes them, a button below the other sections opening the terms, with which version it accepted and when, or that acceptance is due.

The Profile tab SHALL hold the account, role and HEMA Ratings sections and none of the above.

#### Scenario: Pending deletion
- **WHEN** an account with a pending deletion opens the Privacy tab
- **THEN** the date is stated and withdrawal is offered

#### Scenario: Reached by address
- **WHEN** someone follows a link to the Profile page's Privacy tab
- **THEN** the Privacy tab is selected and shows the download and deletion

#### Scenario: The Profile tab stays about the account
- **WHEN** an account opens the Profile page
- **THEN** the Profile tab is selected and neither the download nor deletion is on it

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

