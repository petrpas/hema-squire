## ADDED Requirements

### Requirement: The ledger idiom
Every console phase in which a machine proposes and an organizer ratifies SHALL
present its decision unit as a ledger line carrying three registers together, in
one place, without navigation: the **claim** (what the fencer told us), the
**evidence** (what the consulted source holds), and the **verdict** (what the
system concluded). The decision unit is whatever the decision is about — a row
in Matching, a pair of rows in Deduplication, a pairing of a row and a
transaction in Payments — and the ledger line is rendered wherever that unit
lives; this requirement fixes the registers, not the surface.

No operation SHALL write the claim register. The fencer's own words are rewritten
only by an organizer's field edit; a machine's finding belongs in the evidence
register, never in place of the claim.

Consequences SHALL follow the verdict, not the proposal. Canonical naming, row
absorption, payment binding and every other effect of a decision SHALL fire when
the organizer ratifies, never when the machine proposes. A proposal changes
nothing but the verdict register.

Ratifying the machine's proposal SHALL cost one action on the ledger line
itself. Overriding it SHALL be reachable from the same place. Both SHALL persist
as rules and SHALL therefore be removable, so that a mistaken ratification costs
one undo and leaves a trail.

A distinction the organizer cannot see, the system SHALL NOT draw: where a
verdict distinguishes degrees of machine confidence, the reason for the degree
SHALL be derivable from the difference between the claim and evidence registers
already on screen. A confidence the machine merely asserts is not a ground for
drawing the distinction.

A phase holding a queue of undecided units SHALL state how many remain.

#### Scenario: Proposal does not displace the claim
- **WHEN** a machine proposes a value for a field the fencer supplied
- **THEN** the fencer's value stays in the claim register, the proposed value appears in the evidence register, and both are visible at once

#### Scenario: One action ratifies
- **WHEN** the organizer accepts the proposal on a ledger line
- **THEN** the verdict is recorded in one action, its consequences fire, and the action can be undone

#### Scenario: Unexplainable confidence is not drawn
- **WHEN** a machine reports a confidence that nothing in the claim or evidence registers accounts for
- **THEN** the verdict does not distinguish that unit from any other proposal

#### Scenario: The queue is countable
- **WHEN** units await a verdict in a phase
- **THEN** the phase states how many

## MODIFIED Requirements

### Requirement: HR matching review
The Matching phase SHALL present each row as a ledger line per **The ledger
idiom**: the registered name, nationality and club as the claim; the HR columns
(HRID, HR_Name, HR_Nat, HR_Club) as the evidence; and a per-row match verdict.
The verdict SHALL be one of confirmed, found, proposed, no match, or unmatched,
and SHALL distinguish those owing the organizer work from those that do not.

The evidence register SHALL state the profile's nationality as its two-letter
ISO country code, whatever vocabulary the source spells it in, so that it can be
read
against a claim written in codes without the reader taking a difference in
spelling for a difference in country. Where no country can be identified the
source's own words SHALL stand — a spelling the system cannot read is still the
evidence it has.

The organizer SHALL ratify a proposed match in one action on the row. From any
row, whatever its verdict, the organizer SHALL be able to search the fighters
index and select a different profile, or mark the fencer as having no HR
profile. Entering a HEMA Ratings id directly into the row SHALL be a verdict,
carrying the same weight and the same consequences as a selection made by
search. Each resolution SHALL persist as a rule.

A resolution SHALL read in the manual-edits log as **one entry**. Binding an id,
the verdict that binding reaches, the canonical name it promotes, the registered
name that promotion displaces, and the evidence register it moves are one
decision by one organizer; as separate entries they would report a single click
several times over. The entry SHALL state what the organizer decided — the id
where the resolution moved it, and the verdict where it did not.

#### Scenario: Resolving an uncertain match
- **WHEN** the organizer confirms the suggested profile on a row marked proposed
- **THEN** the row becomes confirmed, the hr_id is bound, and the decision survives future reruns

#### Scenario: One vocabulary down the evidence column
- **WHEN** the fighters index records a fencer's country as an English name
- **THEN** the row states it as a two-letter ISO code, and every row states it the same way whatever the verdict and whenever the verdict was reached

#### Scenario: Comparing claim against evidence
- **WHEN** the organizer reviews a row whose registered name, club or nationality differs from the matched profile's
- **THEN** both sets of values are visible on the row at once, without opening anything

#### Scenario: One decision, one entry
- **WHEN** the organizer confirms a proposed match and the canonical name is promoted over the registered one
- **THEN** the log carries a single entry for that row, naming the verdict reached, and the promotion is visible on the row rather than as further entries

#### Scenario: A typed id is a verdict
- **WHEN** the organizer types a HEMA Ratings id into a row's HRID cell
- **THEN** the row's verdict becomes confirmed and the id's consequences follow, as though the profile had been selected by search

#### Scenario: Settled rows are still revisable
- **WHEN** the organizer opens the search on a row already reading found or confirmed
- **THEN** an alternative profile may be selected, and the new verdict supersedes the old one
