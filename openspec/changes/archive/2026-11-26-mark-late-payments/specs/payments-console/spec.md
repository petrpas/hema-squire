## ADDED Requirements

### Requirement: An expired registration holding money is marked late
On a tournament whose payments Squire handles, the Payments phase's registration
table SHALL mark an **expired** registration that has money standing against it.
Money stands against it in either of two ways:
- a payment flagged because the reservation it names had already expired —
  outside the grace period, or into a discipline that has since filled — and
  still holding no live credit;
- live credit the expired registration still holds.

The mark SHALL sit in the row's state cell in place of the state's word. It
SHALL take the paid stamp's shape and SHALL be drawn in a muted ink, not in
`--stamp`, and it SHALL read **"Pozdě"** in Czech and **"Too late"** in English.
It SHALL NOT read as paid: the registration is expired, and the lifecycle wins
over the money (`payment-ledger`, The lifecycle wins over the money).

Its tooltip SHALL say that the reservation lapsed and state the money standing
against it, with its amount, its currency and the day it arrived or the day the
reservation expired. A flagged payment SHALL be named as awaiting the
organizer's decision; held credit SHALL be named as held by the organizer.

Pressing the mark SHALL open the money table that payment sits in — the
uncredited table for a flagged payment, the credited table for held credit — and
SHALL bring that payment's row into view and mark it as the one arrived at, in a
static way, until the organizer opens another table or another tab. Where both
kinds stand against one registration, the mark SHALL lead to the flagged
payment, since that is the one awaiting a decision. Where several flagged
payments stand against it, the mark SHALL lead to the most recent one and its
tooltip SHALL state their count.

A cancelled registration SHALL NOT be marked: the registration table does not
draw it, and the one action on its late payment — refund — is on that payment's
row in the uncredited table. An expired registration with no money against it
SHALL read as it does today.

#### Scenario: A late payment outside the grace period
- **WHEN** a reservation expired five days ago and a payment of 1800 Kč carrying its VS has just arrived and been flagged
- **THEN** its row in the registration table carries a muted stamp reading "Pozdě", whose tooltip states that the reservation lapsed and 1800 Kč arrived on that day awaiting a decision

#### Scenario: The stamp leads to the payment
- **WHEN** the organizer presses that stamp
- **THEN** the uncredited table opens with the 1800 Kč payment in view and marked, carrying its reinstate and refund actions

#### Scenario: Held credit is marked the same way
- **WHEN** a reservation credited 500 Kč of 1800 Kč expires
- **THEN** its row carries the same "Pozdě" stamp, whose tooltip states that the reservation lapsed holding 500 Kč, and pressing it opens the credited table on the payment that credited it

#### Scenario: The flagged payment wins
- **WHEN** an expired registration holds 500 Kč of credit and a later payment of 1300 Kč on it has been flagged
- **THEN** pressing the stamp opens the uncredited table on the 1300 Kč payment

#### Scenario: Never read as paid
- **WHEN** an expired registration's flagged payment covers its whole total
- **THEN** its row reads "Pozdě" in the muted ink and not the paid stamp, and it is counted nowhere as paid

#### Scenario: An ordinary expiry is unchanged
- **WHEN** a reservation expires with nothing credited and no payment flagged against it
- **THEN** its state cell reads the expired state's word as before, with no stamp

#### Scenario: Reinstating removes the mark
- **WHEN** the organizer reinstates the registration from the flagged payment's row
- **THEN** the registration is no longer expired and its row carries no late stamp
