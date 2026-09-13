## ADDED Requirements

### Requirement: A rule may replace the person a row is about
A substitution SHALL be a rule of a third kind, whose subject is **who the row is about** rather than a projected field or a registration's billing.

The kind SHALL carry the whole of the substitute's identity — name, HEMA Ratings id where one was chosen, nationality, club, the seat's address — together with the identity it replaced, so that a replay states the decision that was taken and a withdrawal has somewhere to return the seat to. It SHALL NOT be recorded as a set of field edits: several edits can be withdrawn one at a time, which would leave a row wearing half of one person and half of another.

Where a registration stands behind the row, applying the rule SHALL move the registration to the substitute's fencer record and SHALL set the seat's contact address; the projection follows from the registration, as it does for an amendment. Where no registration stands behind the row — an imported or hand-entered row not yet issued one — applying the rule SHALL write the identity onto the projected row.

Applying the rule SHALL NOT recompute the registration's total, SHALL NOT touch its entries or its items, and SHALL NOT write to the payment journal. It changes who holds the seat, not what the seat is.

An identity field edit SHALL remain what it is: correcting a misspelt name is not a substitution, and SHALL NOT be recorded as one.

#### Scenario: The rule reaches the registration
- **WHEN** a substitution is applied to a row that has a registration
- **THEN** the registration belongs to the substitute's fencer record, its total and entries are unchanged, and the table states the substitute's name

#### Scenario: The rule writes the projection where there is no registration
- **WHEN** a substitution is applied to an imported row that has been issued no registration
- **THEN** the projected row states the substitute's name, profile, nationality and club

#### Scenario: Withdrawal returns the whole identity at once
- **WHEN** a substitution rule is withdrawn
- **THEN** the row states the replaced fencer's name, profile, nationality, club and address together, with nothing of the substitute left on it

#### Scenario: A correction is not a substitution
- **WHEN** the organizer corrects a misspelt name in the table
- **THEN** a field edit is recorded, no substitution is, and no mail is sent

### Requirement: The substitution reads as a sentence in the log
The manual-edits log SHALL render a substitution as one line naming the row, the fencer replaced and the fencer who replaced them, in that order, in the reading language. It SHALL NOT render the identity payload field by field.

#### Scenario: One readable line
- **WHEN** the organizer reads the fencer list's manual-edits log after a substitution
- **THEN** one entry names the row's number, the replaced fencer and the substitute
