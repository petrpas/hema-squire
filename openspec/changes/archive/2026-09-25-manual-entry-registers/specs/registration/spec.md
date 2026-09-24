## MODIFIED Requirements

### Requirement: One dormancy predicate governs the lifecycle passes
Whether Squire runs its lifecycle clocks against a registration SHALL be settled by a single predicate over the tournament and the registration, and every lifecycle pass SHALL consult that predicate and no other condition of its own. The passes so governed are the reminder pass, the expiry pass, the demotion carried out at seating settlement, and the count of pending demotions the console states before the organizer confirms one.

The predicate SHALL yield the **cause** of dormancy rather than a bare yes or no, drawn from a closed set of reasons, so that why a registration is not moving is readable rather than inferred. The causes SHALL be:

- the tournament is **unpublished**, so it is a tournament being written and holds nobody for a clock to run against (`tournament-publication`);
- the tournament's **payments feature is off**, so no money was ever requested;
- the registration was **issued from an imported row**, so its clocks are dormant by origin;
- the registration was **entered by hand** on an automatic tournament, so its clocks are dormant by origin.

A cause SHALL be read from the tournament wherever it is a live setting, so that changing that setting takes effect at once and no stale copy governs a pass. A cause SHALL be stored only where it records an origin that cannot be recomputed from the registration's present contents.

**The selection of tournaments a pass considers SHALL exclude unpublished tournaments**, as it already excludes those a tournament's organizer keeps the roster for. The exclusion and the cause are both stated deliberately, and neither replaces the other: the exclusion means no pass ever reaches such a tournament, and the cause means the paths a person triggers by hand — the count the console states, the settlement an organizer asks for — answer alike. That is the difference between a guarantee and a guard, and the guarantee is what makes the property true of a registration created by any path, including one that neglects to mark it dormant.

Adding a further reason to leave a registration alone SHALL be an addition to this predicate and SHALL NOT be a condition placed in any pass.

#### Scenario: Every pass agrees
- **WHEN** a registration is dormant for any cause and the lifecycle runs
- **THEN** it receives no reminder, does not expire, is not demoted at settlement, and is not counted among the pending demotions

#### Scenario: The count and the settlement select alike
- **WHEN** the console states how many registrations settling seating would demote, and the organizer then settles
- **THEN** the registrations demoted are exactly those counted, with no registration counted that settlement leaves alone

#### Scenario: A live cause is read live
- **WHEN** a tournament's payments feature is turned on
- **THEN** its registrations cease to be dormant for that cause from that moment, without any registration being rewritten

#### Scenario: The cause is stated
- **WHEN** a registration is dormant
- **THEN** which of the reasons made it dormant is available, rather than only the fact that it is

#### Scenario: A draft is not among the tournaments a pass considers
- **WHEN** the lifecycle pass selects the tournaments it will run against
- **THEN** no unpublished tournament is among them

#### Scenario: Publication starts the clocks
- **WHEN** a tournament is published
- **THEN** its registrations cease to be dormant for that cause from that moment, without any registration being rewritten

#### Scenario: A hand entry names its own cause
- **WHEN** the dormancy of a registration entered by hand on an automatic tournament is asked
- **THEN** the cause stated is that it was entered by hand, not that it was issued from an import

## ADDED Requirements

### Requirement: A registration entered by hand
On an **automatic** tournament a fencer entered by hand at the console SHALL become a registration at the moment of entry. It SHALL be one of the tournament's registrations in every respect the rest of this capability fixes, except where this requirement says otherwise.

- **Placement.** Each discipline SHALL be placed against its own capacity exactly as an in-app submission is: seated where a place is free, queued where the discipline is full, and queued in every discipline once seating has settled. The organizer MAY promote it from the queue like any other. Capacity SHALL NOT be waived for it: an organizer who wants a fencer seated in a full discipline raises the capacity or promotes into a place that frees.
- **Money.** It SHALL be priced like an in-app registration of the same moment and SHALL carry a variable symbol from the tournament's sequence, so that a payment quoting it is matched. It SHALL be matchable, linkable, creditable and waivable like any other.
- **Clocks.** Its lifecycle clocks SHALL be dormant by origin, permanently, under the cause *entered by hand*: no payment window, no due date, no reminder, no expiry, and no demotion at seating settlement. The organizer may still return it to the queue by hand while it is unpaid.
- **Mail.** Squire SHALL send it no mail of any kind — no confirmation, no payment instruction, no reminder, no payment receipt, no promotion notice, no demotion notice, no notice of a payment held. The organizer who entered the fencer is the one in contact with them.
- **Identity.** It SHALL create no account. The fencer record SHALL carry the address the organizer typed only where no other fencer record holds that address; otherwise it SHALL carry none. An entry whose address belongs to a fencer already registered on this tournament SHALL be refused with a reason naming that registration, because the person is certainly already on the list. Any other likeness SHALL be left to deduplication, as for every row.

On a manual tournament a hand entry SHALL remain a source row, as `etl-console` fixes.

#### Scenario: Seated where there is room
- **WHEN** the organizer enters a fencer by hand for a discipline with free places on an automatic tournament before seating settles
- **THEN** a registration is created, seated, priced and given a variable symbol, and nothing is mailed

#### Scenario: Queued where there is none
- **WHEN** the same entry names a full discipline and a discipline with a free place
- **THEN** the free one is seated and the full one queued, in one registration

#### Scenario: Queued after settlement
- **WHEN** the organizer enters a fencer by hand after seating settled
- **THEN** every discipline is queued, nothing is owed, and the organizer may promote them

#### Scenario: Promoted in silence
- **WHEN** the organizer promotes a hand-entered registration into a free place
- **THEN** it is seated and billed the placement, no payment window opens, and no mail is sent

#### Scenario: Paid by bank
- **WHEN** a payment quoting a hand-entered registration's variable symbol is ingested
- **THEN** it is matched and credited, and no receipt is mailed

#### Scenario: Not demoted at settlement
- **WHEN** seating settles while a hand-entered registration is seated and unpaid
- **THEN** it keeps its seat

#### Scenario: An address already registered here
- **WHEN** the organizer enters by hand an address belonging to a fencer who already holds a registration on this tournament
- **THEN** the entry is refused, naming that registration, and nothing is created
