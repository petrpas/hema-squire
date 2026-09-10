## ADDED Requirements

### Requirement: The phase is two tables behind two bands
The Payments phase SHALL present the organizer's payment work as **two tables**
in the phase's main area, reached through two tab bands: the first choosing
between the fencer table and the payments, the second — shown only while the
payments are chosen — choosing between **credited** and **uncredited** payments.
Each band SHALL carry the console's own tab idiom, and each payments tab SHALL
state its own count, so that work in a table nobody is looking at is still
visible. The fencer tab SHALL carry no count: these counts mean outstanding
work, and a roster size among them would read as more of it. The phase's rail
SHALL hold only the operation's parameters and the manual-edits log, as every
other phase's rail does.

Which table a payment belongs to SHALL be decided by **the credit journal** —
whether the payment holds a live credit — and not by the transaction's status. A
payment the matcher marked resolved while crediting nothing is uncredited money
and belongs with the work.

Each table SHALL load independently of the other and of the fencer table. A
table with nothing to show SHALL say so rather than disappear, and its tab SHALL
remain with its zero rather than being withdrawn.

The phase's sheet heading SHALL name the phase's own subject rather than the
fencer table's, as the Import phase's heading already does.

#### Scenario: Nothing outstanding
- **WHEN** the organizer opens the Payments phase on a tournament where nothing has been credited and nothing awaits resolution
- **THEN** both payments tabs show a count of zero, and whichever is opened states that it is empty in a single line

#### Scenario: The second band appears with the money
- **WHEN** the organizer chooses the payments in the first band
- **THEN** a second band appears beside it offering the credited and the uncredited payments, and the first band still offers the fencer table

#### Scenario: The fencer table gives way to whichever table is read
- **WHEN** the organizer opens either payments table
- **THEN** that table is what the phase shows, and returning to the fencer tab lists every registration with its payment state as before

#### Scenario: One table fails to load
- **WHEN** the request behind the uncredited payments fails while the other succeeds
- **THEN** that table reports its own failure, and the credited table and the fencer table still render their data

#### Scenario: The phase names itself
- **WHEN** the organizer opens the Payments phase
- **THEN** the sheet heading names the management of payments rather than the registered fencers

### Requirement: Uncredited payments are one table
The console SHALL list every payment that arrived and holds no live credit,
showing the payer, the amount with its currency, the date, and the payment's own
message text, so the organizer can judge who sent the money.

Money set aside as a sibling tournament's, on a bank account several
tournaments share, SHALL NOT appear here. It holds no credit and never will
hold one on this tournament — its own console is what resolves it — so listing
it would put work in the table that nobody reading that table can do. Holding
no credit is therefore necessary but not sufficient: the table is the payments
that lie on nobody **and are this tournament's to resolve**.

Beside that evidence each row SHALL state **what is to be done with it**, which
is one of three things: the fencer a resolver read in the payment's text, the
reason nothing could be credited, or nothing at all where the payment simply
carries no usable reference. The actions offered on a row SHALL follow from what
that column says — confirming a proposal, assigning the payment by hand,
reinstating a reservation, or marking the money for refund.

A payment whose pairing credited nothing SHALL appear here with that as its
reason, and SHALL leave the table by itself once a credit exists, without an
organizer having to withdraw anything.

#### Scenario: Foreign transfer with no VS
- **WHEN** a SEPA transfer arrives with the fencer's name but no parsable VS
- **THEN** it appears in the uncredited table with its payer name, amount, date and message, and nothing is claimed about who it is for

#### Scenario: A proposal is one row among them
- **WHEN** a resolver reads a fencer's name in an uncredited payment's text
- **THEN** that payment appears in the same table with the fencer named as what is to be done, and can be confirmed or rejected in place

#### Scenario: A refusal states itself
- **WHEN** a payment carries a VS whose reservation had already expired outside the grace period
- **THEN** the payment appears in the uncredited table stating that reason, with the reinstate and refund actions on the row

#### Scenario: A pairing that credited nothing is work, not a result
- **WHEN** an organizer pairs a payment with a registration and the registration is cancelled before the pairing can credit anything
- **THEN** the payment appears in the uncredited table naming the registration it was paired with and stating that nothing was credited

#### Scenario: Credited money is not here
- **WHEN** a transaction holds a live credit
- **THEN** it does not appear in the uncredited table, whatever its status says

#### Scenario: A sibling tournament's money is not this console's work
- **WHEN** a statement from a shared bank account brings a payment carrying another tournament's variable symbol
- **THEN** it does not appear in the uncredited table, the phase stating instead that its own console will match it

### Requirement: Credited payments are one table
The console SHALL list every payment holding a live credit — a bank transaction
and a payment recorded by hand alike — showing the date the money arrived, where
it came from, the amount with its currency, and every registration it credited,
since one payment may credit several.

Each row SHALL state **why** it was credited, distinguishing at least a symbol
the matcher read, a pairing an organizer made, and a payment a person recorded,
so that a reader asking why a registration is paid is not left to infer it.

The organizer SHALL be able to reverse a payment's credit from this table and to
pair the payment with somebody else. Both act on **the whole payment**: reversal
SHALL release every live credit that payment made, and the payment SHALL return
to the uncredited table.

Reversal SHALL state its consequence before it is confirmed, naming the
registrations that stop reading as paid or stating plainly that none does. That
statement SHALL be asked of the current state rather than read from the listing,
because whether a registration reads as paid is a derivation and the listing may
be older than the answer; the confirmation SHALL NOT be offered until it has
been obtained.

Which payments hold credit SHALL be answered from the credit journal and not
from a transaction's matched registration or its status: what a payment credited
is what its live entries say.

#### Scenario: An automatically matched transaction is listed
- **WHEN** a transaction is credited to a registration by an automatic VS match
- **THEN** it appears in the credited table with its date, payer, amount and the fencer it credited, and states that a symbol is why

#### Scenario: A hand-recorded payment sits beside the bank's
- **WHEN** the organizer records a cash payment
- **THEN** it appears in the same credited table, stating that a person recorded it and who

#### Scenario: A payment covering three registrations names all three
- **WHEN** the credited table lists a payment that credited three registrations
- **THEN** all three fencers are named on its row, each with the amount credited to them

#### Scenario: The consequence is stated before it is confirmed
- **WHEN** the organizer opens the reversal action on a payment whose credit is the whole of what settled a registration
- **THEN** that registration is named as one that will stop reading as paid, and nothing is reversed until the organizer confirms

#### Scenario: Nothing stops reading as paid
- **WHEN** the organizer opens the reversal action on a payment whose registrations remain settled without it
- **THEN** the action states that no registration stops reading as paid

#### Scenario: A reversal moves the row to the other table
- **WHEN** the organizer confirms the reversal
- **THEN** the credits are reversed and the payment appears in the uncredited table instead

#### Scenario: Removal of a hand-recorded payment is the same act
- **WHEN** the organizer reverses a payment they had recorded by hand
- **THEN** exactly the amount it credited is released, the consequence is stated first as for any other payment, and the row leaves the table

### Requirement: A line beside the tab band states one thing about the open table
The space beside the payments tab band SHALL carry one line about **the table
being read**, not about the band. It SHALL state something the table's own count
cannot: how many of the uncredited payments are proposals awaiting a person, or
what the credited payments come to in total.

The line SHALL be worded so that a subset reads as a subset and not as a second
count that could disagree with the tab's. It SHALL be absent where there is
nothing to say, rather than stating a zero. It SHALL NOT be a control: reading
it changes nothing about which rows are shown.

The fencer table SHALL carry no such line, because the phase's footer already
states its totals.

#### Scenario: A subset is stated as a subset
- **WHEN** seven payments are uncredited and three of them carry a proposal
- **THEN** the tab states seven, and the line beside the band states that three of those are proposals

#### Scenario: Nothing to say
- **WHEN** no uncredited payment carries a proposal
- **THEN** no line appears beside the band, and no zero is stated

#### Scenario: The line follows the open table
- **WHEN** the organizer moves from the uncredited payments to the credited ones
- **THEN** the line changes to what the credited table has to say, rather than continuing to describe the table that was left

#### Scenario: The fencer table says nothing here
- **WHEN** the fencer table is the open tab
- **THEN** the space beside the band is empty, the phase's footer stating the roster's totals as before

## MODIFIED Requirements

### Requirement: The flagged queue names a hand-settled cause
WHERE a payment is uncredited because its registration is no longer reserved,
the uncredited table SHALL state whether that registration was settled by hand
and, where it was, show the mark or the recorded payment that settled it. An
organizer resolving the row is deciding whether the payment is further money or
the same money arriving twice, and that decision needs the earlier act in front
of it.

#### Scenario: The earlier act is shown
- **WHEN** an uncredited payment names a registration a recorded cash payment had settled
- **THEN** the row states that the registration was settled by a payment recorded by hand, with its amount and date

#### Scenario: An ordinary conflict is unchanged
- **WHEN** an uncredited payment names a registration paid by an earlier bank transaction
- **THEN** the row states that as it does today, with no hand-settled claim made

## REMOVED Requirements

### Requirement: Payment resolution views
**Reason**: Replaced by **The phase is two tables behind two bands**. The
requirement described six views stacked above the fencer table — which the tab
strip had already superseded without the spec being brought level — and its
subject was the *number* of views, which is exactly what this change halves
twice over. Both the count and the stacking are gone, so editing it in place
would have left a requirement whose name and whose scenarios were about a shape
that no longer exists.

**Migration**: None. No stored data changes; the same rows are presented by two
tables instead of six views.

### Requirement: Unmatched transaction queue
**Reason**: Absorbed into **Uncredited payments are one table**. The queue's
subject — a payment carrying no reference that resolves — is one of the three
things the uncredited table's own column states, and separating it from the
flagged money put one fact on two tabs while a payment that was neither showed
on none.

**Migration**: None. No stored data changes; the same transactions are listed by
one table instead of two, and the `unmatched` endpoint's own filtering by status
is replaced by the journal-derived question.

### Requirement: Money stranded on expired reservations
**Reason**: Absorbed into the fencer table, where an expired registration
holding credit is a state the table already carries rather than a queue of its
own. The list was a work queue built from a payment event because the money was
credited and so appeared in neither transaction queue; with the credited
payments now listed in full, and the registration's own state and credited
figure on its row, the queue restated what two other views already said.

**Migration**: None. The `expired_holding` endpoint may remain for the figure it
computes; nothing depends on it being presented as a queue.

### Requirement: Payment links are visible and removable
**Reason**: Absorbed into **Credited payments are one table**. A pairing that
credited money is visible there as the reason that money was credited, and
undoing it is the same act as reversing the credit. A pairing that credited
nothing is not a result at all and now appears with the work, in the uncredited
table.

**Migration**: None. The `payment_link` rules are unchanged in storage and in
behaviour; only where they are read from changes. Withdrawing a pairing
continues to reverse exactly the credits naming it.

### Requirement: Payments recorded by hand are listed and removable
**Reason**: Absorbed into **Credited payments are one table**. A payment a
person recorded is a payment holding a live credit, and listing it apart from
the bank's meant the console answered "what has been credited" in two places
that could not be read together.

**Migration**: None. Recording a payment is unchanged, as is what removing one
reverses; both are reached from the credited table instead of from a view of
their own.

### Requirement: Credited transactions are listed and reversible
**Reason**: Superseded by **Credited payments are one table**, which is the same
requirement widened to the hand-recorded half of the journal and given the
reason each credit exists.

**Migration**: None.
