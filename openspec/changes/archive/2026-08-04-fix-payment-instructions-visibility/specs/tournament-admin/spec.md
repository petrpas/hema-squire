## MODIFIED Requirements

### Requirement: Setup completeness
Mandatory setup SHALL comprise: display name, date, location, at least one titular organizer, at least one discipline with a unit price, the bank account payments are collected into whenever the tournament charges anything at all, and — whenever the tournament prices in EUR as a second currency — every rendered EUR price field: each discipline's EUR price, each extra item's EUR price, and the EUR amount of each fixed discount. Every team discipline SHALL additionally have valid roster bounds, and a team discipline missing them SHALL be reported as a missing item. The team composition deadline SHALL NOT be part of mandatory setup: a tournament may offer team disciplines without one. A tournament still pricing through the legacy fixed weapon-rental/afterparty parameters SHALL be reported as blocked from enabling EUR, naming those parameters and directing the organizer to itemized extra services. The recorded exchange ratio is a Setup convenience only and is never part of completeness.

The bank account is mandatory because a published tournament accepts registrations, and a registration that cannot be paid holds a place against a deadline the fencer has no way to meet. Completeness is the only guarantee the registration path relies on, so the account SHALL be guaranteed by the same rule as every other mandatory item rather than checked again when a fencer asks how to pay.

A tournament SHALL be treated as charging when any price it can build a total from is above zero — any discipline's unit or early-bird price in either currency, any extra item's price in either currency, or any of the legacy fixed weapon-rental and afterparty parameters. Discounts SHALL NOT be considered, since they only reduce a total and cannot make a free tournament charge. A tournament that charges nothing SHALL be publishable with no bank account recorded. Completeness therefore depends on price **values** and not merely on their presence, so a tournament SHALL become incomplete at the moment it first sets a nonzero price without an account to collect it into — including a published tournament, whose save SHALL then be refused until the account is supplied.

Complete mandatory setup SHALL be the precondition for publishing a tournament, and SHALL NOT by itself make a tournament public: publication is the explicit act fixed by `tournament-publication`. The items still unconfigured SHALL be named on the Setup phase's `PUBLISH` tab, which is where the organizer learns what stands between the tournament and publication. A tournament that has not been published SHALL NOT accept registrations, whether or not its mandatory setup is complete.

A tournament published before the bank account became mandatory SHALL remain published and SHALL NOT be un-published by this rule, since the guarantee attaches at the moment of publication and cannot be applied retroactively. Such tournaments SHALL be reportable, so that an organizer can be told to supply the account rather than discovering it through a fencer who cannot pay.

#### Scenario: Blocking items shown
- **WHEN** the organizer opens `PUBLISH` for a tournament without location and without discipline prices
- **THEN** the tab lists location and the missing unit prices as blocking publication

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
- **WHEN** the organizer publishes a priced tournament whose every other mandatory item is configured but which has recorded no bank account
- **THEN** the attempt is refused and names the bank account as the item still missing

#### Scenario: A tournament that charges nothing needs no account
- **WHEN** the organizer publishes a tournament whose every discipline and extra item is priced at zero and which has recorded no bank account
- **THEN** the publication succeeds and no missing bank account is reported

#### Scenario: Setting the first price makes the account mandatory
- **WHEN** a published tournament that charged nothing is saved with a nonzero discipline price and still no bank account
- **THEN** the save is refused, naming the bank account, and the price is not stored

#### Scenario: Discounts alone do not make a tournament charge
- **WHEN** a tournament priced entirely at zero carries a fixed discount and has no bank account
- **THEN** it is still treated as charging nothing and remains publishable

#### Scenario: Bank account cannot be cleared after publication
- **WHEN** the organizer of a published priced tournament saves its payment settings with the bank account emptied
- **THEN** the save is refused and the stored account is unchanged

#### Scenario: Setup completed
- **WHEN** the last mandatory item is filled
- **THEN** the `PUBLISH` tab lists nothing blocking and offers the publish action; the tournament remains invisible to fencers and closed to registration until it is published
