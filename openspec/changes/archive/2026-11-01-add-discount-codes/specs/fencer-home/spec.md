## ADDED Requirements

### Requirement: The code field
The Register screen SHALL offer a code field between the discounts section and the total, only while the tournament accepts codes, and the amendment form SHALL offer the same field while the registration carries no code. Applying a code SHALL refresh the total from the server's evaluation; the screen SHALL NOT evaluate a code itself.

An accepted code SHALL leave a line stating the code's name and what it deducted. A refused one SHALL leave one plain line saying the code does not apply, with no difference between a code that never existed and one that ran out, and the total SHALL stay as it was. The applied code SHALL be submittable only as accepted: a typed but unapplied code SHALL NOT be sent.

#### Scenario: Field absent
- **WHEN** a fencer opens the Register screen of a tournament with no usable code
- **THEN** no code field and no empty-state text appear

#### Scenario: Code accepted
- **WHEN** a fencer applies a valid −200 Kč code
- **THEN** the line states its name and −200 Kč and the total drops in the same refresh

#### Scenario: Code refused
- **WHEN** a fencer applies a string that is no usable code
- **THEN** one plain line says the code does not apply, and the total is unchanged

#### Scenario: Selection changed after applying
- **WHEN** a percentage code is applied and the fencer adds a discipline
- **THEN** the line and the total update together from the same evaluation

### Requirement: The code on the registration
A registration carrying a code SHALL state on the fencer's own registration view, between the priced lines and the total, the code's name and what it deducted. A registration a code covered in full SHALL NOT offer payment instructions or a QR code.

#### Scenario: Line on the Registered tab
- **WHEN** a fencer holding a −200 Kč code opens their registration
- **THEN** a line naming the code states −200 Kč and the total below it agrees

#### Scenario: Nothing to pay
- **WHEN** a fencer's total was brought to zero by a code
- **THEN** the registration states it is paid and shows no payment slip
