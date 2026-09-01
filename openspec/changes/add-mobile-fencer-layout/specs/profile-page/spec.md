## MODIFIED Requirements

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
