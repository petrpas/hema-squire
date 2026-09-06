## MODIFIED Requirements

### Requirement: The Payments phase is boned out where Squire collects nothing
WHERE Squire does not handle a tournament's payments, the Payments phase SHALL hold exactly one thing: whether each registration has been marked settled, and the control that marks and unmarks it (`payments`).

It SHALL hold nothing else. No queue of unmatched or flagged transactions, no intake card, no matching tolerance, no transaction list, no recorded-payments view, no variable symbol, no payment window — none of them has a meaning when no money passes through Squire, and a phase offering a control that answers a refusal is worse than one that does not offer it.

Where Squire does handle the payments the phase SHALL be everything it is today **and SHALL also offer the settled mark**, which there is the waiver and asks for a reason before it is written (`payments`). It SHALL offer it on the registration's state cell rather than in a column, and SHALL offer recording a payment among the row's actions rather than in a column: the phase's table is already wide, and neither a control that is empty on almost every row nor an action dressed as a value earns a column of its own. The mark has a column only in the boned-out phase, where it is the whole content.

The phase SHALL state what the mark means where it could mislead: where Squire collects nothing, that it records the organizer's word that the money was received and that Squire has received nothing itself; where Squire collects, that the registration owes nothing and no money arrived for it.

**The mark SHALL be a write to the registration, not a rule.** Every other manual edit in the console persists as a rule replayed over the projection, which changes what the table and the export show and reaches nothing else. This mark changes what the registration *is* — the public participant list and the registration's own state depend on it — so it SHALL be written through. Recording a payment SHALL be written through for the same reason and by the same route. The departure SHALL be deliberate and confined to these two actions.

#### Scenario: The boned-out phase
- **WHEN** the organizer opens the Payments phase on a tournament that handles its own payments
- **THEN** each row states whether it is marked settled and the mark can be set and unset, and no queue, intake, tolerance, transaction list or recorded-payments view is offered

#### Scenario: The full phase offers the mark without a column
- **WHEN** the organizer opens the Payments phase on a tournament whose payments Squire handles
- **THEN** it holds every queue, panel and column it holds today, the mark is reached on the state cell, recording a payment sits at the end of the row, and no column was added

#### Scenario: The mark reaches the registration
- **WHEN** a registration is marked settled and the tournament's public participant list is read
- **THEN** that entrant is shown as confirmed, which no rule over the projection could have achieved

### Requirement: Outstanding balance in the Payments phase table
The Payments phase's fencer table SHALL carry an outstanding-balance column alongside the total. The balance SHALL be a value on the sheet row, so it sorts, exports and reruns with the rest of the table rather than living only in a side panel or in the fencer's own view.

The column SHALL show the one balance the registration has, in the one currency that balance is in (`payments`). It SHALL NOT show a figure per currency lane. The total beside it names both prices, because both are what the place costs; the balance names one, because only one lane is owed. Read as a pair the second figure passes for a conversion of the first, and a fully paid row states a debt.

A row whose registration is settled but credited short of its total SHALL state the shortfall rather than zero (`payments`). The tolerance decides whether the registration counts as paid; it does not decide what the column says, and a column reading zero on money that never arrived tells the organizer their books balance when they do not.

Money an organizer recorded by hand SHALL be counted in what has been credited, exactly as an ingested transaction's amount is, so that a registration settled in cash shows no balance outstanding.

WHERE a registration has been settled by hand, the column SHALL state that the balance is **waived** rather than showing the figure it would otherwise owe. Nothing was credited and nothing is due, and presenting the full total there would read as a fault in every roster it appears in.

The column SHALL state the word alone and SHALL NOT print the organizer's reason beside it. A reason is a sentence — *volný vstup za čtvrté místo dosažené v loňském roce* — and a money column set to the width of the longest of them stops being a money column. The reason SHALL be reachable from that word, opening where it is asked for.

The word SHALL carry no mark of its own — no glyph, no underline, no altered cursor. The one word standing in a column of figures is already conspicuous, and each of those would be a second mark saying only that the first has more behind it. Where a waiver carries no reason there SHALL be nothing to open.

#### Scenario: Part-paid reservation
- **WHEN** a fencer has paid half of a reservation's total and the organizer opens the Payments phase
- **THEN** the row shows the total and the remaining balance, without the organizer subtracting anything by hand

#### Scenario: Settled reservation
- **WHEN** a registration has been paid in full
- **THEN** its outstanding balance reads as zero

#### Scenario: One currency in the column
- **WHEN** the tournament prices in both crowns and euro and a registration has been paid in crowns
- **THEN** the column reads zero, with no euro figure beside it

#### Scenario: A shortfall the tolerance accepted
- **WHEN** a paid registration was credited a converted transfer that fell a few crowns short, within tolerance
- **THEN** the column states those crowns, and the row still reads paid

#### Scenario: A surcharge is not hidden
- **WHEN** a paid registration is amended upward and owes 300
- **THEN** the column reads 300

#### Scenario: Settled in cash
- **WHEN** a registration's whole total was recorded as a cash payment
- **THEN** its outstanding balance reads as zero, as it would had a transaction settled it

#### Scenario: Waived registration
- **WHEN** a registration with a total of 1750 has been settled by hand
- **THEN** its outstanding column states that the balance is waived, and does not show 1750 owed

#### Scenario: A long reason does not widen the column
- **WHEN** a registration is waived with the reason *volný vstup za čtvrté místo dosažené v loňském roce*
- **THEN** the column reads only that the balance is waived, and the reason opens from that word rather than standing in the row

#### Scenario: A waiver with no reason marks nothing
- **WHEN** a registration is waived without a reason
- **THEN** the column reads that the balance is waived and offers nothing to open

#### Scenario: Balance survives a rerun
- **WHEN** the organizer reruns processing
- **THEN** the outstanding column is recomputed from the current credited amounts, with no rule required to maintain it

#### Scenario: The Payments phase keeps its table
- **WHEN** the organizer opens the Payments phase
- **THEN** the fencer table is present with the outstanding column, below the phase's resolution queues — unlike Deduplication, which replaces the table entirely
