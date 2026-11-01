## MODIFIED Requirements

### Requirement: A discount stands in the block it deducted from
A discount the tournament configures, or a discount code, SHALL appear as a line, named `Sleva`
(`Discount`) followed by its name, in the block of every category it deducted
from on at least one counted registration. Each code SHALL be a line of its own, under its name and never its code text. Its line SHALL state:
- as **Price**, the configured effect with a minus: the fixed amount in the local
  currency (`−400 Kč`) or the percentage (`−10 %`);
- as **Count**, the counted registrations it deducted from in this block, as
  paid / all;
- as **Paid** and **To pay**, the amounts it deducted in this block from the
  settled and from the other registrations, as negative figures.

The amount a discount deducted from a category SHALL be the amount pricing
deducted when it priced the registration's total — for a fixed discount
reaching several categories, the share it took from each — so that a block's
lines and discounts sum to what that category is billed.

A discount that applied to no counted registration SHALL have no line.

#### Scenario: A discount on entry fees
- **WHEN** a −400 Kč discount for entering both disciplines applied to twelve registrations, eight of them settled
- **THEN** the Startovné block has a line Sleva Both disciplines, −400 Kč, 8/12, −3 200, −1 600

#### Scenario: A discount across two categories
- **WHEN** a fixed −500 Kč discount reaching entry fees and rentals took 400 from a registration's entry fees and 100 from its rentals
- **THEN** the registration counts on the discount's line in Startovné at −400 and on its line in Zápůjčky at −100

#### Scenario: A discount nobody got
- **WHEN** an early-registration discount applied to no one
- **THEN** no block has a line for it

#### Scenario: A code stands as a line
- **WHEN** a −200 Kč code named "Trenéři" applied to three registrations, two of them settled
- **THEN** Startovné holds a line `Sleva Trenéři` at −200 Kč with a count of 2 / 3, and the block still sums to what the category is billed

#### Scenario: A legacy-priced tournament
- **WHEN** a code deducts on a tournament on the legacy path
- **THEN** its line stands in the blocks it took from, and the block sums as on any other tournament
