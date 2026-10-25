## MODIFIED Requirements

### Requirement: An action needing an account leads to sign-in
A control on a public screen whose effect requires an account — managing a registration from the detail page, opening the personal list — SHALL lead an
anonymous visitor to the sign-in screen rather than fail, disappear, or be
presented as unavailable. After signing in the visitor SHALL be returned to the
screen they left, on the tournament they were reading.

Registering for a tournament SHALL lead to the same sign-in screen, which SHALL
offer, beside signing in and creating an account, **registering without signing
up** (`guest-registration`). Because registering no longer needs an account,
the screen SHALL NOT state that it does. It SHALL state instead, in one line in
the design system's static treatment, that the visitor may sign in, create an
account, or register without one. A visitor who registers without signing up
SHALL be returned to the tournament's registration tab as `guest-registration`
fixes, and one who creates an account to the same place once the account is
verified (`fencer-accounts`).

The reason for any other gated action SHALL be stated where the action was
taken, in one line, in the same static treatment. It SHALL NOT be delivered as
an error.

#### Scenario: Register while signed out
- **WHEN** an anonymous visitor selects Register on a tournament whose registration is open
- **THEN** the sign-in screen is shown, offering sign-in, account creation and registering without signing up, and it does not say that registering needs an account

#### Scenario: Back to the tournament after signing in
- **WHEN** that visitor signs in
- **THEN** the tournament's detail is shown again, on its registration tab

#### Scenario: Registering without signing up from the prompt
- **WHEN** that visitor chooses to register without signing up and completes the guest form
- **THEN** the tournament's detail is shown again, on its registration tab, with the checklist ready to submit as a guest

#### Scenario: No personal list without an account
- **WHEN** an anonymous visitor opens the personal list's URL directly
- **THEN** the sign-in screen is shown, offering no way to register without signing up, and after signing in the personal list is displayed
