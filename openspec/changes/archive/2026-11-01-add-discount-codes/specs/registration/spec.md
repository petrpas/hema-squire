## ADDED Requirements

### Requirement: Registering with a discount code
A registration submission, by an account or a guest, SHALL be able to name a discount code. A code that `discount-codes` holds unusable SHALL refuse the submission with nothing created, so that the fencer never receives a total higher than the one they submitted for and decides what to do with the form still filled in.

A code named on a tournament that offers none SHALL be refused alike.

#### Scenario: Registered with a code
- **WHEN** a fencer submits a selection priced at 1500 Kč with a valid −200 Kč code
- **THEN** the registration is created at 1300 Kč, carrying the code

#### Scenario: A guest redeems a code
- **WHEN** a guest submits a valid code
- **THEN** it prices exactly as on an account's registration

#### Scenario: Code ran out while the form stood open
- **WHEN** a fencer submits a code that has meanwhile reached its limit
- **THEN** the submission is refused, no registration exists, and the form keeps its contents

### Requirement: A code can be added by amending
While the amendment window is open, a fencer's own amendment SHALL be able to add a code to a registration carrying none. The amendment SHALL NOT remove or replace a code. An organizer's correction from the console SHALL leave the code as it stands.

A code added to a registration already holding credit SHALL reprice it like any amendment, so that what was paid above the new total stands as an overpayment, stated and resolved as any other.

#### Scenario: Forgotten code added
- **WHEN** a fencer who has not paid amends their registration adding a valid −200 Kč code
- **THEN** the total falls by 200 Kč and the amended registration carries the code

#### Scenario: Added after paying
- **WHEN** a fencer who has paid 1500 Kč adds a −200 Kč code
- **THEN** the registration stays paid and its balance states an overpayment of 200 Kč

#### Scenario: A code cannot be swapped
- **WHEN** an amendment names a code on a registration already carrying a different one
- **THEN** the amendment is refused and the registration keeps its code

#### Scenario: Window closed
- **WHEN** the amendment window has closed
- **THEN** no code can be added

### Requirement: The preview prices a code
A price preview naming a code SHALL return the total the same selection would be registered at with that code, and SHALL return, apart from the discount breakdown, the code's name, its effect and what it deducted, per configured currency for a fixed effect and as a single figure for a percentage. The breakdown of automatic discounts SHALL be unchanged by it. An unusable code SHALL be refused as `discount-codes` fixes.

The preview a fencer sees while amending SHALL price the code their registration already carries whether or not it is still available.

#### Scenario: Preview matches registration with a code
- **WHEN** a preview naming a code is followed by a registration of the same selection and code on the same date
- **THEN** the totals are equal in every configured currency

#### Scenario: The holder's own preview
- **WHEN** a fencer holding a code that has since run out previews an amendment
- **THEN** the preview prices their code rather than refusing it
