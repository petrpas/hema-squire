## MODIFIED Requirements

### Requirement: Setup completeness
Mandatory setup SHALL comprise: display name, date, city, at least one titular organizer, at least one discipline with a unit price, the bank account payments are collected into whenever the tournament charges anything at all **and its payments feature is on**, the account holder whenever such a tournament also takes EUR — as its only currency or as its second — and — whenever the tournament prices in EUR as a second currency — every rendered EUR price field: each discipline's EUR price, each extra item's EUR price, and the EUR amount of each fixed discount. Every team discipline SHALL additionally have valid roster bounds, and a team discipline missing them SHALL be reported as a missing item. The team composition deadline SHALL NOT be part of mandatory setup: a tournament may offer team disciplines without one. A tournament still pricing through the legacy fixed weapon-rental/afterparty parameters SHALL be reported as blocked from enabling EUR, naming those parameters and directing the organizer to itemized extra services. The recorded exchange ratio is a Setup convenience only and is never part of completeness.

The bank account is mandatory **on a tournament Squire collects money for** because a published tournament accepts registrations, and a registration that cannot be paid holds a place against a deadline the fencer has no way to meet. Completeness is the only guarantee the registration path relies on, so the account SHALL be guaranteed by the same rule as every other mandatory item rather than checked again when a fencer asks how to pay.

Mandatory setup SHALL branch on the tournament's mode, as fixed by `tournament-mode`. **A tournament in manual mode SHALL additionally require the address of its external registration**, because publishing a tournament that accepts no registration and names no other way in leaves a fencer with nowhere to go. It SHALL NOT be required to record a bank account, whatever it charges, since Squire collects nothing for it. Its registration-opens and registration-closes dates SHALL NOT be treated as mandatory and SHALL NOT be enforced as a gate: they describe when the organizer's own registration runs, and the gate they would guard refuses every submission already. Every other mandatory item SHALL apply unchanged, because an organizer-kept tournament is no less a tournament — it has a place, organizers, disciplines and prices like any other.

**A tournament whose payments feature is off SHALL NOT be required to record a bank account, whatever it charges**, and SHALL NOT have one reported as missing. Squire requests no money for such a tournament, sends no payment instructions and reconciles no transactions, as fixed by `payments`; the prices it carries state what the event costs and are settled outside the system. Every other mandatory item SHALL be unaffected by the payments feature, because the rest of completeness is about what the tournament offers rather than about collecting for it.

A tournament SHALL be treated as charging when any price it can build a total from is above zero — any discipline's unit or early-bird price in either currency, any extra item's price in either currency, or any of the legacy fixed weapon-rental and afterparty parameters. Discounts SHALL NOT be considered, since they only reduce a total and cannot make a free tournament charge. A tournament that charges nothing SHALL be publishable with no bank account recorded. Completeness therefore depends on price **values** and not merely on their presence, so a tournament with payments enabled SHALL become incomplete at the moment it first sets a nonzero price without an account to collect it into — including a published tournament, whose save SHALL then be refused until the account is supplied.

An item whose editor the tournament's features conceal SHALL still be reported, and SHALL name the feature that restores its editor, as fixed by `setup-navigation`. Completeness reads the tournament's contents, not its features: a hidden team discipline is still a team discipline and is still checked for roster bounds.

Complete mandatory setup SHALL be the precondition for publishing a tournament, and SHALL NOT by itself make a tournament public: publication is the explicit act fixed by `tournament-publication`. The items still unconfigured SHALL be named on the Setup phase's `PUBLISH` tab, which is where the organizer learns what stands between the tournament and publication. A tournament that has not been published SHALL NOT accept registrations, whether or not its mandatory setup is complete.

A tournament published before the bank account became mandatory SHALL remain published and SHALL NOT be un-published by this rule, since the guarantee attaches at the moment of publication and cannot be applied retroactively. Such tournaments SHALL be reportable, so that an organizer can be told to supply the account rather than discovering it through a fencer who cannot pay.

#### Scenario: An organizer-kept tournament needs its external address
- **WHEN** the organizer opens `PUBLISH` on a tournament whose registrations they keep, with no external registration address recorded
- **THEN** the tab lists that address as blocking publication

#### Scenario: An organizer-kept tournament needs no bank account
- **WHEN** a tournament whose registrations the organizer keeps carries priced disciplines and no bank account
- **THEN** no missing bank account is reported and publication is available once the external address is recorded

#### Scenario: The registration window does not block an organizer-kept tournament
- **WHEN** a tournament whose registrations the organizer keeps has neither a registration-opens nor a registration-closes date
- **THEN** neither is reported as missing

#### Scenario: Blocking items shown
- **WHEN** the organizer opens `PUBLISH` for a tournament without a city and without discipline prices
- **THEN** the tab lists the city and the missing unit prices as blocking publication, and never the address, which is not mandatory

#### Scenario: Missing roster bounds block publication
- **WHEN** a tournament has a team discipline with no roster bounds set
- **THEN** the `PUBLISH` tab lists that discipline's roster bounds as blocking publication

#### Scenario: Composition deadline never blocks
- **WHEN** a tournament offers a fully configured team discipline and no composition deadline
- **THEN** the `PUBLISH` tab reports nothing missing on that account and publication is available

#### Scenario: Missing EUR price blocks publication
- **WHEN** a CZK + EUR tournament has a discipline whose EUR price is empty
- **THEN** the missing EUR price is listed as blocking publication, with no separate exchange-rate requirement

#### Scenario: Legacy fixed fees block EUR
- **WHEN** the organizer enables EUR on a tournament still pricing through the fixed weapon-rental or afterparty parameters
- **THEN** those parameters are named as blocking EUR and the organizer is directed to itemized extra services

#### Scenario: Missing bank account blocks publication
- **WHEN** the organizer publishes a priced, payments-enabled tournament whose every other mandatory item is configured but which has recorded no bank account
- **THEN** the attempt is refused and names the bank account as the item still missing

#### Scenario: A priced tournament with payments off needs no account
- **WHEN** the organizer publishes a tournament with priced disciplines, the payments feature off and no bank account recorded
- **THEN** the publication succeeds and no missing bank account is reported

#### Scenario: Turning payments on makes the account mandatory
- **WHEN** the organizer turns the payments feature on for a published, priced tournament with no bank account recorded
- **THEN** the bank account is reported as missing, `PAYMENTS` carries the marker, and it is offered on that tab

#### Scenario: A tournament that charges nothing needs no account
- **WHEN** the organizer publishes a tournament whose every discipline and extra item is priced at zero and which has recorded no bank account
- **THEN** the publication succeeds and no missing bank account is reported

#### Scenario: Setting the first price makes the account mandatory
- **WHEN** a published, payments-enabled tournament that charged nothing is saved with a nonzero discipline price and still no bank account
- **THEN** the save is refused, naming the bank account, and the price is not stored

#### Scenario: Discounts alone do not make a tournament charge
- **WHEN** a tournament priced entirely at zero carries a fixed discount and has no bank account
- **THEN** it is still treated as charging nothing and remains publishable

#### Scenario: Bank account cannot be cleared after publication
- **WHEN** the organizer of a published, priced, payments-enabled tournament saves its payment settings with the bank account emptied
- **THEN** the save is refused and the stored account is unchanged

#### Scenario: Hidden team discipline still checked
- **WHEN** a tournament with the team feature off holds a team discipline with no roster bounds
- **THEN** the roster bounds are reported as blocking publication, naming the team disciplines feature as what restores their editor

#### Scenario: Setup completed
- **WHEN** the last mandatory item is filled
- **THEN** the `PUBLISH` tab lists nothing blocking and offers the publish action; the tournament remains invisible to fencers and closed to registration until it is published

#### Scenario: A EUR-taking tournament needs its holder
- **WHEN** the organizer opens `PUBLISH` on a CZK + EUR tournament with payments on, a bank account and no account holder
- **THEN** the account holder is named as missing and the tournament cannot be published

#### Scenario: A CZK-only tournament does not
- **WHEN** a CZK-only tournament with payments on records a bank account and no holder
- **THEN** no holder is reported missing

## ADDED Requirements

### Requirement: The account holder is recorded beside the bank account
A tournament SHALL record the name of the bank account's holder — the person or organization the account belongs to, as the bank knows it — as plain text of at most 70 characters, the limit of the EPC code's beneficiary name. It SHALL be entered on `PAYMENTS` directly below the bank account, in the same section and under the same save, and SHALL carry a help hint stating that a EUR payment code must name the account's holder and that a foreign bank refuses a code without it. It SHALL be offered wherever the bank account is offered and hidden wherever the bank account is hidden.

#### Scenario: Holder entered under the account
- **WHEN** the organizer of a payments-enabled tournament opens `PAYMENTS`
- **THEN** the account holder field sits directly below the bank account, with a help hint saying why it is needed

#### Scenario: Holder too long
- **WHEN** the organizer enters a holder longer than 70 characters
- **THEN** the save is refused with the limit stated
