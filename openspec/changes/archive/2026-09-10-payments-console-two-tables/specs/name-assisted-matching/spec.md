## ADDED Requirements

### Requirement: Proposals are worked from the uncredited payments
A proposal SHALL be worked from **the table of payments that arrived and lie on
nobody**, and SHALL be confirmable or rejectable from it without leaving it.

A proposal is not a queue of its own. It is what is to be done about an
uncredited payment — the resolver has read a fencer in the payer's text, and
nothing has been credited — which is exactly the question that table asks of
every row it holds. Given a tab of their own, proposals made a reader visit
three tables to learn whether there was any work at all.

Each such row SHALL state the payment as the bank wrote it — its date, its
amount and its text — beside the fencer proposed and what that fencer owes, so
the organizer confirms on evidence rather than on the system's say-so.

How many of the uncredited payments carry a proposal SHALL be stated where that
table is read, so proposals remain visible as a body of work despite sharing a
table with the money nothing could be read from. Where none does, nothing SHALL
be stated.

#### Scenario: Proposals are worked from the uncredited table
- **WHEN** the organizer opens the Payments phase with proposals waiting
- **THEN** they are listed among the uncredited payments, each stating the payment and the fencer proposed, and each can be confirmed or rejected in place

#### Scenario: The evidence is shown, not just the conclusion
- **WHEN** a proposal is displayed
- **THEN** the payment's own message and payer are shown beside the proposed fencer and their outstanding amount

#### Scenario: How many are proposals is stated
- **WHEN** three of the uncredited payments carry a proposal
- **THEN** the console states that three of them are proposals, without contradicting the table's own count

#### Scenario: No proposals, nothing said
- **WHEN** no payment is proposed
- **THEN** the uncredited table lists whatever else it holds and nothing is stated about proposals

#### Scenario: A confirmed proposal moves to the credited table
- **WHEN** the organizer confirms a proposal
- **THEN** the payment is credited and appears among the credited payments, stating that a pairing is why

## REMOVED Requirements

### Requirement: Proposals are a queue of their own
**Reason**: Replaced by **Proposals are worked from the uncredited payments**. A
proposal turned out not to be a kind of queue but a kind of *row*: an uncredited
payment about which the resolver has something to say. Standing beside the
queues for unresolved and flagged money, it split one question — this arrived
and is credited to nobody — across three tabs, and a payment that was none of
the three appeared in none of them.

**Migration**: None. Confirming and rejecting are unchanged, endpoint and effect
alike; only where the row is read from moves. The collapsing-to-a-heading
behaviour goes with the queue: an empty table states its emptiness once, and its
tab keeps its zero.
