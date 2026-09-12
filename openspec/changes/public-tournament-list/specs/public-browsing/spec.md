## Purpose
Define what a visitor with no account may read: which fencer-facing endpoints and
screens answer without a credential, what an anonymous payload leaves out, and how
an action that needs an account leads to sign-in rather than to a refusal.

## ADDED Requirements

### Requirement: The tournament list and a tournament's detail are public
The fencer-facing tournament list — its upcoming scope and its held scope — and a
published tournament's fencer-facing detail SHALL be readable without a
credential. A request carrying no credential SHALL be answered with the same
tournaments, in the same order, as a request from an account with no bond to any
of them; it SHALL NOT be refused with 401 and SHALL NOT be answered with an empty
list.

A request carrying a credential the server rejects SHALL be refused, not silently
treated as anonymous. An absent credential and a bad one are different facts, and
a visitor holding an expired session is told so rather than quietly downgraded.

The personal list — the tournaments an account is bound to — SHALL remain
authenticated and SHALL be refused with 401 without a credential.

Publication SHALL remain the only line. A draft, a cancelled tournament, and a
tournament whose setup is incomplete SHALL be absent from the public list and
SHALL yield a not-found answer on the public detail, for an anonymous visitor
exactly as for an authenticated one.

#### Scenario: Upcoming list without a credential
- **WHEN** the upcoming tournament list is requested with no credential while two published upcoming tournaments exist
- **THEN** both are returned, soonest first, with their names, dates, places, organizers, disciplines and registration statuses

#### Scenario: Held list without a credential
- **WHEN** the held scope is requested with no credential
- **THEN** every published, non-cancelled tournament dated before today is returned, newest first

#### Scenario: Detail without a credential
- **WHEN** a published tournament's fencer-facing detail is requested with no credential
- **THEN** the tournament's information is returned

#### Scenario: A rejected credential is not anonymous
- **WHEN** the list is requested with a credential the server does not accept
- **THEN** the request is refused with 401 rather than answered as an anonymous one

#### Scenario: The personal list still needs an account
- **WHEN** the personal list is requested with no credential
- **THEN** it is refused with 401

#### Scenario: A draft is not public
- **WHEN** an unpublished tournament's detail is requested with no credential
- **THEN** the answer is not-found, worded as it is for an authenticated visitor who may not open it

### Requirement: The organizer's index is the caller's own
The listing that feeds the tournament picker — drafts included, in the console's full shape —
SHALL require a credential, SHALL be refused without one, and SHALL carry only the tournaments
the caller may open a console on: those it owns and those it sits on the console team of,
cancelled ones excluded. No global role widens it, the console itself admitting none.

It is named here because it carries the same fields the fencer-facing detail withholds, for
every tournament it lists at once. A public detail that withheld the bank account while an
index handed it out to any signed-in account would state a rule the deployment does not keep.
A row the caller cannot follow is a row that answers 403, and the picker is the account's own
tournaments rather than the deployment's.

The fencer-facing lists remain the public ones.

The count of that same set SHALL be carried on the account, so the account menu can ask
whether there is a picker worth offering without fetching the listing on every page.

#### Scenario: The index needs a credential
- **WHEN** the picker's listing is requested with no credential
- **THEN** it is refused with 401

#### Scenario: A draft is not handed out by the index
- **WHEN** a deployment holds an unpublished tournament with a bank account on file
- **THEN** no unauthenticated request returns either the draft or the account number

#### Scenario: Another account's tournament
- **WHEN** an organizer who neither owns a tournament nor sits on its console team opens the picker
- **THEN** that tournament is not listed, while their own are, drafts among them

#### Scenario: A seat on the console team
- **WHEN** an account is added to a tournament's console team
- **THEN** that tournament appears in their picker, and their account's count of tournaments rises by one

### Requirement: An anonymous payload carries no bond
Fields describing the relationship between the caller and a tournament — the
caller's registration state for it, and whether the caller may manage it — SHALL
be absent from a payload answered without a credential, rather than sent as a
default value. A registration state of "none" and an unmanageable tournament are
claims about an account; with no account behind the request there is nothing to
claim, and a client that reads an absent field as "no bond" is reading a fact
rather than guessing at one.

Every field that does not depend on the caller SHALL be present exactly as it is
for an authenticated request.

#### Scenario: Bond fields omitted
- **WHEN** the list is answered without a credential
- **THEN** each entry omits the caller's registration state and the manage mark, and carries its name, subtitle, date, location, organizers, disciplines with counts, and registration status unchanged

#### Scenario: Counts are not personal
- **WHEN** an anonymous visitor and a registered fencer read the same tournament's entry
- **THEN** the per-discipline taken/capacity numbers and the queue lengths are identical

### Requirement: An action needing an account leads to sign-in
A control on a public screen whose effect requires an account — registering for a
tournament, managing a registration, opening the personal list — SHALL lead an
anonymous visitor to the sign-in screen rather than fail, disappear, or be
presented as unavailable. After signing in the visitor SHALL be returned to the
screen they left, on the tournament they were reading.

The reason SHALL be stated where the action was taken: that registration needs an
account, in one line, in the design system's static treatment. It SHALL NOT be
delivered as an error.

#### Scenario: Register while signed out
- **WHEN** an anonymous visitor selects Register on a tournament whose registration is open
- **THEN** the sign-in screen is shown, with one line saying that registering needs an account

#### Scenario: Back to the tournament after signing in
- **WHEN** that visitor signs in
- **THEN** the tournament's detail is shown again, on its registration tab

#### Scenario: No personal list without an account
- **WHEN** an anonymous visitor opens the personal list's URL directly
- **THEN** the sign-in screen is shown, and after signing in the personal list is displayed

### Requirement: Sign-in can be declined
The sign-in screen shown by an action on a public screen SHALL offer a way back
to the screen it stands in front of, taken either by a control on the form or by
Escape. The visitor SHALL be returned to the page they were reading, at the URL
they were already on, with nothing signed in.

The screen renders over that URL rather than at one of its own, so the browser's
own Back leads away from the page behind it instead of off the sign-in screen:
without a way back of its own, an anonymous visitor who reaches for a control
needing an account has no way to decline it.

Where the sign-in screen is the whole of a gated URL — an address whose screen
cannot be read without an account — the way back SHALL lead to the public
tournament list instead, and the account-creation form's own way back SHALL lead
to sign-in rather than out of both screens at once.

#### Scenario: Declining the prompt
- **WHEN** an anonymous visitor who selected Register takes the sign-in screen's way back
- **THEN** the tournament's detail is shown again at the same URL, with no account signed in

#### Scenario: Escape dismisses the prompt
- **WHEN** that visitor presses Escape on the sign-in screen
- **THEN** the screen is dismissed exactly as its own control dismisses it

#### Scenario: Declining at a gated URL
- **WHEN** a visitor declines sign-in at the personal list's URL, which has no public page behind it
- **THEN** the tournament list is shown on the tab that its default resolution names

#### Scenario: Escape on the account-creation form
- **WHEN** a visitor presses Escape while creating an account
- **THEN** the sign-in screen is shown again, the screen behind it left standing

### Requirement: The shell offers sign-in in place of an identity
On a public screen with no account behind it, the place the shell gives a
fencer's identity SHALL offer sign-in instead. No name, no hemaratings identity
and no account menu entry that acts on an account — profile, admin, the picker,
tournament creation, sign-out — SHALL be shown to an anonymous visitor. Where
that leaves the account menu with nothing to offer, the menu SHALL be absent
rather than rendered empty.

The shell SHALL NOT render an authenticated appearance with the identity left
blank. An empty identity block reads as a broken application rather than as being
signed out.

#### Scenario: Sign-in offered in the bar
- **WHEN** an anonymous visitor opens the tournament list
- **THEN** the top bar offers sign-in where a signed-in fencer's name and hemaratings identity stand, and shows neither

#### Scenario: Account actions absent
- **WHEN** the shell renders for an anonymous visitor
- **THEN** no profile, admin, picker, create-tournament or sign-out entry is reachable, and the account menu is absent rather than shown holding nothing

#### Scenario: Signing in fills the bar
- **WHEN** the visitor signs in from the list
- **THEN** the same screen is shown with their name and hemaratings identity in the bar and the account menu's own entries available

### Requirement: The public detail carries no organizer's business
The fencer-facing detail SHALL carry only what a fencer reads: the tournament's identity,
dates, location, qualification, organizers, disciplines with their fees and counts, extra
services with their prices, the registration window and its status, the currency, and the
feature flags that decide which of those are shown at all.

It SHALL NOT carry the organizer's own configuration: the bank account, whether a bank-feed
token is on file, the accounting sheet address, the variable-symbol series, reservation and
reminder parameters, the amount tolerance, the unpaid-list treatment, the HR category map,
the setup-completeness report, or the owner's account identifier. Those belong to the
console, which reads them through its own authenticated path.

A field is withheld by being absent from the fencer-facing answer, not by being blanked:
what a fencer is never shown is not something a fencer's client should have to decide to
ignore.

#### Scenario: Bank details are not in the fencer's answer
- **WHEN** the fencer-facing detail of a tournament with a bank account and a stored feed token is read
- **THEN** the answer carries neither the account number nor any statement about the token

#### Scenario: Setup state is not in the fencer's answer
- **WHEN** the fencer-facing detail of a published tournament with incomplete optional setup is read
- **THEN** the answer carries no setup-completeness report

#### Scenario: The console still reads everything
- **WHEN** a member of a tournament's console team opens its Setup phase
- **THEN** every organizer-owned field is available to it, unchanged
