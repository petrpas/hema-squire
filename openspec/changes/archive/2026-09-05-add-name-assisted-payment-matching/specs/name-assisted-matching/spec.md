## ADDED Requirements

### Requirement: The message names the fencer, the payer name does not
A payment SHALL be resolved to a fencer from the text the payer wrote about the
payment — the message and the other text-bearing fields ingestion captures —
and SHALL NOT be resolved from the payer's name or account.

The payer's name SHALL be consulted only where those fields name nobody at all,
and a resolution reached that way SHALL be treated as weaker evidence, not as an
equal.

The reason is a fact about how tournaments are paid for: one person routinely
pays for another, and for several others in one statement. A payer name read as
an identity credits the person holding the account rather than the person
competing, and does so most confidently in exactly the case where it is most
wrong — when the payer is also on the roster.

#### Scenario: Third party pays for a fencer
- **WHEN** a payment from one person carries a message naming a different fencer, and both are on the roster
- **THEN** the fencer named in the message is resolved, and the payer is not

#### Scenario: One payer, several fencers
- **WHEN** one person sends three payments whose messages name three different fencers
- **THEN** each payment resolves to the fencer its own message names

#### Scenario: The payer is the fallback, not a peer
- **WHEN** a payment's message names nobody — carrying only a placeholder or a description
- **THEN** the payer's name may be used to resolve it, and the resolution is not treated as clear

### Requirement: What the model extracts, and what it does not
Reading a payment's text for the person it names SHALL be done by the language
model that already interprets the statement's rows, as one more thing it reports
about each row. It SHALL be cached with the rest of that row's interpretation, so
re-importing a statement SHALL NOT ask again.

The model SHALL be asked only who the payment is for. It SHALL NOT be asked to
choose among the roster, SHALL NOT be given the roster, and SHALL NOT be relied
on to decide whether a resolution is good enough. Those are decided from the
roster by rule, so that they are testable, adjustable against real statements,
and unchanged by a model's mood.

A deployment with no model configured SHALL still resolve payments by name,
using the payment's text as written. Extraction improves the query; it is not
what makes resolution possible.

#### Scenario: Extraction rides the statement interpretation
- **WHEN** a statement is interpreted
- **THEN** each row's named person is reported with the rest of that row, and no separate model call is made for it

#### Scenario: Re-import asks nothing again
- **WHEN** the same statement is imported a second time
- **THEN** the named person for each unchanged row is taken from what was stored, and the model is not consulted

#### Scenario: Resolution without a model
- **WHEN** a deployment with no model configured ingests a payment whose message plainly names a fencer
- **THEN** the payment is still resolved against the roster

### Requirement: Resolution ranks the whole roster by rule
Every fencer of the tournament SHALL be scored against the payment's named
person and ranked, by rule rather than by a model.

Comparison SHALL be insensitive to the things that differ between how a bank
writes a name and how a roster does: diacritics, letter case, the order of a
person's names, and punctuation or spacing between them. A payment naming
`MAZANEC MATEJ`, `Vejda Josef` or `JosefVochozka` SHALL rank the fencer those
name the same as one writing the name as the roster does.

Ranking SHALL be defined for every payment, including one that names nobody
recognisable, so the organizer resolving it by hand is always offered an ordered
roster rather than an empty result.

#### Scenario: Diacritics and case do not matter
- **WHEN** a payment names `Rebekka Guenther` and the roster holds `Rebekka Günther`
- **THEN** that fencer ranks first

#### Scenario: Name order does not matter
- **WHEN** a payment names `Vejda Josef` and the roster holds `Josef Vejda`
- **THEN** that fencer ranks first

#### Scenario: A missing space does not matter
- **WHEN** a payment names `JosefVochozka` and the roster holds `Josef Vochozka`
- **THEN** that fencer ranks highly enough to be offered among the strongest candidates

#### Scenario: An unrecognisable payment still ranks
- **WHEN** a payment's text names no one on the roster
- **THEN** the roster is still returned in a defined order for the organizer to choose from

### Requirement: A proposal requires a clear single winner
A payment carrying no variable symbol SHALL become a proposal only where the
ranking produces a clear single winner: the leading fencer SHALL both score above
a minimum and lead the next fencer by a minimum margin.

The margin SHALL be required independently of the score. A payment that names
someone the roster holds twice, or names one of two similar people, SHALL NOT
become a proposal however strongly it scores — a high score shared by two
candidates is a statement that the payment is ambiguous, not that either is
right.

Where there is no clear winner the payment SHALL be unmatched and resolved by
hand, with the ranking offered to the organizer.

#### Scenario: A clear name becomes a proposal
- **WHEN** a payment names one fencer plainly and no other fencer is close
- **THEN** it becomes a proposal naming that fencer

#### Scenario: Two close candidates are not proposed
- **WHEN** a payment's text scores equally well against two fencers
- **THEN** it is not proposed, and is left for the organizer with both at the top of the ranking

#### Scenario: A weak best match is not proposed
- **WHEN** the best-scoring fencer still scores below the minimum
- **THEN** the payment is not proposed

### Requirement: A proposal holds no money
A proposed payment SHALL be a statement about who it appears to be for, and
nothing more. Until a person confirms it, it SHALL NOT be credited to any
registration, SHALL NOT change any balance or outstanding amount, SHALL NOT
settle or advance any registration's state, and SHALL NOT cause any mail to be
sent to anyone.

A proposal SHALL be distinguishable from both a matched payment and an unresolved
one, so that the money a tournament has actually taken is never overstated by the
money it merely suspects.

Confirming a proposal SHALL credit the payment exactly as a payment quoting that
registration's variable symbol would be credited, with the same tolerance,
currency and part-payment behaviour, and SHALL be recorded as the organizer's
decision rather than the system's.

Rejecting a proposal SHALL return the payment to unresolved and SHALL NOT propose
the same fencer for it again.

#### Scenario: A proposal moves no money
- **WHEN** a payment is proposed against a fencer's registration
- **THEN** that registration's credited amount and outstanding amount are unchanged, its state is unchanged, and no mail is sent

#### Scenario: Confirmation credits
- **WHEN** the organizer confirms a proposal
- **THEN** the payment is credited to that registration, and everything that follows a credit follows

#### Scenario: Rejection returns it to the queue
- **WHEN** the organizer rejects a proposal
- **THEN** the payment becomes unresolved and is not proposed against that fencer again

#### Scenario: Proposals are not counted as taken
- **WHEN** the console reports what a tournament has been paid
- **THEN** proposed payments are not counted among it

### Requirement: Proposals are a queue of their own
Proposals SHALL be offered as their own work queue in the Payments phase, beside
the queues for unresolved and flagged money, and SHALL be confirmable or
rejectable from it without leaving it.

Each entry SHALL state the payment as the bank wrote it — its date, its amount
and its text — beside the fencer proposed and what that fencer owes, so the
organizer confirms on evidence rather than on the system's say-so.

An empty proposals queue SHALL collapse to a heading as the other queues do.

#### Scenario: Proposals are worked from their queue
- **WHEN** the organizer opens the Payments phase with proposals waiting
- **THEN** they are listed together, each stating the payment and the fencer proposed, and each can be confirmed or rejected in place

#### Scenario: The evidence is shown, not just the conclusion
- **WHEN** a proposal is displayed
- **THEN** the payment's own message and payer are shown beside the proposed fencer and their outstanding amount

#### Scenario: No proposals, no queue
- **WHEN** no payment is proposed
- **THEN** the proposals queue shows as a heading with nothing under it

### Requirement: The link dialog offers the ranked roster
Resolving a payment by hand SHALL offer the tournament's fencers ranked by how
well they match the payment, with the strongest marked, rather than requiring the
organizer to know and type a variable symbol.

The dialog SHALL also offer a text lookup over the whole roster, so a fencer the
ranking placed poorly can be found by typing part of their name. Typing a
variable symbol directly SHALL remain available, and one payment SHALL still be
attachable to several registrations.

#### Scenario: The roster is offered ranked
- **WHEN** the organizer opens the link dialog on an unresolved payment
- **THEN** the tournament's fencers are listed ordered by how well they match it, with the strongest marked

#### Scenario: A poorly ranked fencer is found by typing
- **WHEN** the payment names nobody recognisable and the organizer types part of a fencer's name
- **THEN** the matching fencers are shown and can be chosen

#### Scenario: Typing a variable symbol still works
- **WHEN** the organizer types a variable symbol rather than choosing a fencer
- **THEN** it resolves as it does today

#### Scenario: One payment covering several fencers
- **WHEN** the organizer chooses more than one fencer for one payment
- **THEN** the payment is linked to each of their registrations

### Requirement: A variable symbol is a shortcut, and the tail is resolved by hand
A variable symbol SHALL be understood as a shortcut that resolves the majority of payments cheaply, and SHALL NOT be treated as a registration's identity. A payment that carries none, carries one that resolves to nothing, or carries one belonging to somebody other than the person its message names SHALL be an ordinary case with an expected share of the traffic, not an exception.

**In every mode**, therefore, an organizer SHALL be able to resolve such a payment by choosing the fencer it is for, without quoting a symbol. Typing a symbol SHALL remain available as a second route for an organizer who knows the number, and SHALL NOT be the only one.

The resolver's proposal SHALL be offered wherever it has one, whatever the mode, and SHALL still move nothing until a person accepts it. Where it proposes nobody, or proposes wrongly, the organizer's own choice SHALL be the last word.

#### Scenario: A mistyped symbol is resolved by name
- **WHEN** a payment on a Squire-kept tournament quotes a variable symbol that resolves to nothing, and its message names a fencer on the roster
- **THEN** the organizer is offered that fencer, and can link the payment without typing a number

#### Scenario: A symbol quoted for somebody else
- **WHEN** a payment quotes one fencer's symbol while its message names another
- **THEN** the organizer can direct it to the fencer the message names

#### Scenario: Typing a symbol still works
- **WHEN** an organizer who knows the number types it
- **THEN** the payment links as it does today

### Requirement: Where no registration carries a symbol, this is the whole of matching
WHERE a tournament's registrations carry no variable symbol — which is every tournament whose registrations the organizer keeps (`tournament-mode`, `imported-registrations`) — resolution by the payer's own words SHALL be the only route by which a payment finds a fencer, and every incoming payment SHALL reach it.

The resolver SHALL behave identically there. The same ranking, the same score and margin minimums, the same refusal to propose without a clear single winner: what changes is that nothing precedes it, not how it decides. A proposal SHALL still move no money and SHALL still wait for a person.

**An organizer SHALL be able to resolve a payment by naming the fencer**, on such a tournament, without quoting a symbol that does not exist. Where a payment resolves to nobody, the control that links it by hand SHALL address a person rather than a symbol, since neither the registration nor the statement carries one.

No surface SHALL treat the absence of a symbol as the absence of a registration.

#### Scenario: Every payment goes through the resolver
- **WHEN** a statement is imported against a tournament whose registrations carry no variable symbols
- **THEN** every payment in it is resolved by the payer's own words, and none is set aside for quoting no symbol

#### Scenario: The unresolved are linked by name
- **WHEN** a payment on such a tournament resolves to nobody
- **THEN** the organizer can link it by choosing the fencer, and is asked for no variable symbol

#### Scenario: The decision rule is unchanged
- **WHEN** two fencers score alike on such a tournament
- **THEN** neither is proposed, exactly as on a tournament whose registrations carry symbols
