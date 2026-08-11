## MODIFIED Requirements

### Requirement: Operation parameters
An operation whose behaviour the organizer tunes SHALL expose its own parameters in the phase that runs it — the matching similarity threshold in the matching phase, the amount-matching tolerance in the payments phase. Parameter changes SHALL be audited and take effect on the next rerun.

A phase panel SHALL carry only parameters of the operation that phase runs. **Configuration of the tournament itself SHALL NOT be offered in any phase panel**: what the tournament costs, when it happens, and how fencers pay are decisions taken in Setup before publication, and offering them in a phase panel puts a second editor on a field Setup is responsible for. A phase that has no parameters of its own SHALL show no parameter panel rather than an empty one.

#### Scenario: Threshold change
- **WHEN** the organizer lowers the matching similarity threshold and reruns
- **THEN** undecided rows are re-evaluated under the new threshold while resolved rows keep their rules

#### Scenario: Tolerance belongs to the payments phase
- **WHEN** the organizer opens the payments phase during reconciliation
- **THEN** the amount-matching tolerance is offered there and takes effect on the next rerun

#### Scenario: No tournament configuration in a phase panel
- **WHEN** the organizer looks for the payment mode, the deposit, a tournament date, or a price in any console phase panel
- **THEN** none is offered, and Setup is the only place each can be edited

#### Scenario: A phase with no parameters shows no panel
- **WHEN** the organizer opens a phase whose operation has no tunable parameters
- **THEN** no parameter panel is shown for it
