## ADDED Requirements

### Requirement: A clear removes the registrations issued for the cleared rows
A registration issued for an imported row SHALL be removed when that row is
cleared. It exists only because the row did, and it stands in the row's place on
the fencer list — left behind it would keep drawing that fencer into the table
under the identity of a row the tournament has just asserted never existed, and
the clear could be seen through.

Everything the issued registration held SHALL go with it: its discipline
entries, its extras, its teams, its payment events, and the variable symbol it
carried. A bank transaction that had been linked to such a registration SHALL
NOT be removed — the money arrived regardless — and SHALL return to the
unresolved queue, stating that the registration it named was cleared.

A registration that was **not** issued for an imported row SHALL be untouched, as
every other row of another population is.

#### Scenario: The fencer does not survive the clear
- **WHEN** a tournament whose imported rows were issued registrations is cleared
- **THEN** no registration issued for one of those rows remains, and the fencer list is empty of them

#### Scenario: An in-app registration is untouched
- **WHEN** a tournament holding both in-app registrations and issued ones is cleared
- **THEN** the in-app registrations remain with their variable symbols, totals and history unchanged

#### Scenario: A linked payment returns to the queue
- **WHEN** a transaction had been linked to an issued registration and the tournament is cleared
- **THEN** the transaction remains, holding its amount, and appears as unresolved

### Requirement: A clear is refused where issued registrations hold credit
Clearing SHALL be refused where any registration issued for one of the rows has
been credited, and SHALL state how many. Nothing SHALL be removed by a refused
clear.

A row may be asserted never to have existed; a payment credited against it was a
real event, and destroying it on the way past would leave a tournament whose
books do not add up and nothing to say why. This is the rule a tournament is
already deleted under — financial history is not the console's to erase — applied
to the part of a tournament that can be erased.

The organizer resolves those payments first, after which the clear proceeds
normally.

#### Scenario: Credited registrations stop the clear
- **WHEN** the organizer clears a tournament in which two issued registrations have been credited
- **THEN** the clear is refused, states that two registrations hold credit, and removes nothing

#### Scenario: Uncredited issued registrations do not stop it
- **WHEN** every issued registration is still unpaid
- **THEN** the clear proceeds and removes them with their rows

#### Scenario: Clearing after the payments are resolved
- **WHEN** the organizer unlinks the credited payments and clears again
- **THEN** the clear proceeds
