## ADDED Requirements

### Requirement: Destructive actions
An action that ends or rewrites something the user already holds — cancelling a registration, amending one that is already reserved or paid — SHALL be presented as a destructive control: outlined in `--stamp` with `--stamp` text, never filled, so it stays distinct from the screen's single primary button and adds no second saturated color.

A destructive control SHALL ask for confirmation before acting. The confirmation SHALL be the static, unanimated pattern already used for cancellation — a plain statement of the consequence with a pair of controls, one confirming and one abandoning — and SHALL NOT be a browser dialog.

WHERE two or more destructive controls stand together, they SHALL be laid out as one centered row with space between them, so neither reads as the continuation of the other and neither can be hit by aiming at its neighbour.

#### Scenario: A destructive control is drawn
- **WHEN** a screen offers a cancel-registration control
- **THEN** it is outlined in `--stamp` with `--stamp` text, unfilled, and the screen's primary button remains the only filled one

#### Scenario: Confirmation before acting
- **WHEN** a user activates a destructive control
- **THEN** a static confirmation states what will happen and offers confirming and abandoning controls, with no animation and no browser dialog

#### Scenario: Two destructive controls together
- **WHEN** a screen offers both amend and cancel
- **THEN** the two stand in one centered row separated by space

#### Scenario: Abandoning changes nothing
- **WHEN** a user abandons the confirmation
- **THEN** nothing is sent, and the screen returns to the state it was in
