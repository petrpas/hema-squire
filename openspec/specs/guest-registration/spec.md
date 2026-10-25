# guest-registration Specification

## Purpose
Entering a tournament without an account: the guest identity and the fencer record it resolves to, and the manage link that stands in for an account — what it grants, which messages carry it, when its key changes, how the organizer sends it again, and the screen it opens.

## Requirements
### Requirement: A visitor may register without an account
A visitor holding no account SHALL be able to register for a tournament whose in-app registration is open. The way in SHALL be the sign-in screen that Register raises (`public-browsing`). Beside the way to create an account, it SHALL offer registering without signing up.

Both ways SHALL open the same form, the account-creation form of `fencer-accounts`, with the same fields, the same optional HEMA Ratings step and the same language choice, laid out identically. The guest variant SHALL differ in exactly two respects:

- its heading and subtitle state that the visitor is registering without signing up, where the account variant's state that an account is being created;
- it carries no password field.

Completing the guest variant SHALL create nothing on the server. The identity SHALL be held by the page and the visitor returned to the tournament's registration form. That form SHALL be the one an account holder sees, unchanged, and SHALL state above its first section, in one line, that the visitor is registering without an account under the name and the address they gave. It SHALL offer a way to change them. Submitting the form SHALL send the identity and the selection together, and the registration SHALL be created at that moment or not at all.

The address SHALL be checked as the guest form is completed, so that an address belonging to an account is refused before the visitor fills in a checklist they cannot submit. The same check SHALL be repeated at submission.

A guest registration SHALL be a registration of the tournament in every respect the `registration` capability fixes: priced and given a variable symbol, placed against capacity and queued where a discipline is full, subject to the payment window, the reminders, expiry, seating settlement and demotion, and sent the same messages. Being entered without an account SHALL NOT change any of them.

The guest endpoint SHALL be rate-limited no more generously than signup is.

#### Scenario: Two entries, one form
- **WHEN** an anonymous visitor selects Register on a tournament whose registration is open
- **THEN** the sign-in screen offers both creating an account and registering without signing up, and either opens the same form, differing only in its heading and subtitle and in the guest variant having no password field

#### Scenario: Guest form returns to the checklist
- **WHEN** the visitor completes the guest form with a name and an address
- **THEN** the tournament's registration form is shown, stating that they register without an account as that name and address, and nothing has been created on the server

#### Scenario: Abandoned before submitting
- **WHEN** a visitor completes the guest form and leaves without submitting the checklist
- **THEN** no fencer record, registration or message exists for them

#### Scenario: A guest registration is an ordinary registration
- **WHEN** a guest submits a selection holding a full discipline and a free one on a tournament with a payment window
- **THEN** one registration is created with a variable symbol, the free discipline seated and the full one queued, a payment window open, and the confirmation mailed to the address given

#### Scenario: An account's address refused early
- **WHEN** a visitor completes the guest form with an address that belongs to an account
- **THEN** the form states that the address has an account and offers sign-in, and the visitor is not taken to the checklist

### Requirement: A guest's identity is a record without credentials
A guest registration SHALL hold its fencer on a fencer record that has no credentials, as `fencer-accounts` fixes for records created on a tournament's behalf: it cannot be logged into, and no account exists for it. The record SHALL be resolved from the guest's address and name, with names compared by the fighters index's key, which disregards diacritics, case and word order:

- An address belonging to an **account** — a record holding credentials — SHALL be refused, and the visitor offered sign-in. A guest entry SHALL NOT attach a registration to somebody's account.
- An address held by a **record without credentials that names the same person** SHALL reuse that record. Its name, its HEMA Ratings binding and its other fields SHALL be left as they are.
- Otherwise, when the address is **held by a record naming somebody else**, or by no record at all but already in use on this tournament as the contact address of a registration naming somebody else, a new record SHALL be created **with no address**, and the address SHALL be written as the registration's contact address (`registration`, "A registration may carry a contact address of its own"). This is how a parent or a club representative enters several people from one address. Every message about each of those registrations goes to that one address.
- Where no record holds the address and it is not in use on this tournament, a new record SHALL be created holding it.

A guest entry SHALL be refused as **already registered** where the person it names is already registered on this tournament from that address: either the record holding the address names them and holds a live registration here, or a live registration here carries the address as its contact address and its fencer names them. The refusal SHALL say that the registration's link is in the mail sent to that address, and that the organizer can help where the mail is lost.

A new record SHALL carry the HEMA Ratings profile the guest confirmed in the form, because confirming it is the explicit ownership confirmation `fencer-accounts` requires. A reused record's binding SHALL NOT be changed by a guest entry. A guest entry SHALL NOT be able to rebind a record that is already bound.

Creating or reusing the record SHALL send no message of its own. The guest is written to only about the registration.

#### Scenario: A first-time guest
- **WHEN** a guest registers as Jana Malá with an address no record holds
- **THEN** a record without credentials is created holding that address and the name Jana Malá, and the registration belongs to it

#### Scenario: A parent enters two children
- **WHEN** a parent registers Anna Nová and then Petr Nový, both with the parent's own address
- **THEN** Anna's record holds the address, Petr's record holds none and his registration carries the address as its contact address, and both registrations' messages and links go to that address

#### Scenario: The same child twice
- **WHEN** that parent registers Petr Nový again on the same tournament with the same address
- **THEN** the entry is refused as already registered, and no second registration exists

#### Scenario: A returning guest is recognized
- **WHEN** a guest who registered for one tournament as Jana Malá registers for another with the same address and name
- **THEN** the same record is reused, and its name and HEMA Ratings binding are unchanged

#### Scenario: An account's address is refused at submission
- **WHEN** a guest submission carries an address that belongs to an account
- **THEN** it is refused, nothing is created, and the visitor is offered sign-in

#### Scenario: A confirmed profile binds a new record
- **WHEN** a guest confirms a HEMA Ratings profile in the form and no record holds the address
- **THEN** the new record carries that HR id

### Requirement: A guest registration is managed through a link
A guest registration SHALL have a **manage link**: an address of the application carrying a secret key. Whoever opens it SHALL be able to do with that one registration exactly what its account holder could do from the tournament's detail page, as fixed by `fencer-home` "Registration management" and the `registration` capability: read its state, its selection, its total and its outstanding balance; read its payment instructions and QR codes; amend it; cancel it; and edit its teams' rosters. Each of those SHALL be governed by the same windows, rules and refusals as for an account holder. The link SHALL grant nothing else: no other registration, no other tournament, no account and no console.

Every message Squire sends about a guest registration SHALL carry its manage link, whichever message it is and whatever caused it. A registration held by an account SHALL have no manage link, and no message about it SHALL carry one. An account holder manages their registration by signing in, and a link in a forwardable mail would grant the same thing to whoever receives the forward.

On a successful guest submission the browser SHALL be taken to the manage link at once, so the guest holds it even where the address they gave was mistyped and the mail never arrives.

The key SHALL be long enough and random enough that it cannot be guessed, SHALL be carried in a part of the URL that the browser does not send to the server and that does not leak through a referrer, and SHALL be compared in constant time. A key that is not accepted SHALL be refused identically whether it names no registration or names one under an older key, so a refusal does not reveal which registrations exist.

Squire SHALL offer no self-service way to have the link sent again. A guest who has lost it SHALL be helped by the organizer: the console's fencer list SHALL offer, on a guest registration's row and on no other, an action that mails the registration's current manage link again to the address its messages go to, after the organizer confirms it. Sending it again SHALL NOT change the key, so a link already mailed keeps working.

#### Scenario: Managing from the mail
- **WHEN** a guest opens the manage link from their confirmation mail on another device
- **THEN** their registration is shown with its state, selection, total and payment instructions, and they can amend and cancel it on the terms an account holder has

#### Scenario: The link reaches one registration only
- **WHEN** a request presenting one registration's manage key asks for another registration, another tournament's registration, or an account-only screen
- **THEN** it is refused

#### Scenario: Every message carries it
- **WHEN** a guest registration is reminded, credited, amended, promoted, demoted or cancelled by the organizer
- **THEN** each message sent about it carries its manage link

#### Scenario: Account mail carries none
- **WHEN** a registration held by an account is confirmed or reminded
- **THEN** the message carries no manage link

#### Scenario: Taken there on submission
- **WHEN** a guest submits their registration
- **THEN** the browser is at the manage link, showing the new registration

#### Scenario: Windows still bind
- **WHEN** a guest opens the manage link after the tournament's amendment window has closed
- **THEN** amendment is refused with the reason naming the closed window, exactly as for an account holder, and roster editing is still offered

#### Scenario: The organizer sends the link again
- **WHEN** an organizer sends a guest registration's link again from the fencer list
- **THEN** the registration's address receives a message carrying its manage link, and the link mailed at registration still opens it

#### Scenario: No link to send for an account
- **WHEN** an organizer looks at the row of a registration held by an account
- **THEN** no action to send a link is offered, and a request to send one is refused

#### Scenario: No resend offered
- **WHEN** an anonymous visitor looks for a way to have a lost link sent again
- **THEN** none is offered

### Requirement: A manage key changes when the registration changes hands
A manage key SHALL stop working, and a new one take its place, whenever the address the registration's messages go to changes. A substitution (`fencer-substitution`) that sends the seat's messages to a different address SHALL therefore leave the previous holder's link dead and give the new recipient a link of their own, carried in the substitution message they are sent. A substitution that keeps the seat's address SHALL keep its key. A substitution that hands the seat to a fencer who has an account SHALL end the registration's link altogether, since the registration is then an account's; withdrawing that substitution SHALL NOT restore it, and the organizer can send the returning guest no link until the seat is a guest's again.

A registration whose fencer becomes an account, by a verified signup taking over the record (`fencer-accounts`), SHALL cease to be a guest registration. Its manage link SHALL stop working, and its messages SHALL carry none from then on. Its holder manages it by signing in.

A cancelled registration SHALL keep its key. The link SHALL show the registration as cancelled and offer nothing further, as the detail page shows an account holder their cancelled registration.

#### Scenario: Substitution to a new address
- **WHEN** the organizer substitutes a guest registration's fencer and the seat's messages go to the substitute's address
- **THEN** the old link is refused, and the substitute's message carries a new link that opens the registration

#### Scenario: Substitution keeping the address
- **WHEN** a substitution keeps the address the seat came with
- **THEN** the existing link still opens the registration

#### Scenario: The guest becomes an account
- **WHEN** a guest verifies a signup on the address their record holds
- **THEN** their registrations' links are refused from then on, and the registrations are shown to them on signing in

### Requirement: The manage screen
The manage link SHALL open the tournament's detail page on its registration tab, showing the registration its key names in the management view `fencer-home` fixes, with the shell in its anonymous form (`public-browsing`). No account identity and no account menu entry SHALL appear, because there is no account. The rest of the detail page SHALL read as it does for an anonymous visitor.

The manage screen SHALL be shown in the language the guest chose in the guest form, on whichever device the link is opened, since there is no account whose language would apply. That language SHALL be stated only to a request presenting the registration's manage key.

A link whose key is not accepted SHALL show, in place of the registration, a static statement that the link is no longer valid. It SHALL say that a registration that changed hands or became an account is managed elsewhere, and that the organizer can help. The tournament's public detail SHALL remain readable around it. It SHALL NOT be presented as an error and SHALL NOT be the not-found screen, because the tournament exists.

A guest who has registered and is on the manage screen SHALL NOT be offered a second registration on the same tournament from that screen.

#### Scenario: The manage screen is anonymous
- **WHEN** a guest opens their manage link
- **THEN** the detail page shows their registration on its registration tab, and the top bar offers sign-in and shows no name or account menu

#### Scenario: The manage screen speaks the guest's language
- **WHEN** a guest who chose Czech in the guest form opens their manage link on another device
- **THEN** the detail page is shown in Czech

#### Scenario: A dead link
- **WHEN** a link whose key was replaced by a substitution is opened
- **THEN** the tournament's detail is shown with a static statement that the link is no longer valid, and no registration is shown

