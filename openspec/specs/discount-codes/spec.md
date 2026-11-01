# discount-codes Specification

## Purpose
Fix private discount codes: how an organizer defines them, how a fencer redeems one, how a code prices and how its uses are counted, what a registration a code covers in full means, and who can see any of it.

## Requirements
### Requirement: An organizer defines discount codes
An account with console access SHALL be able to define, for a tournament, discount codes, each with a **name**, a **code**, an optional **limit on uses**, and an **effect**. A code SHALL exist in the tournament's automatic registration only: a manual tournament SHALL offer none.

The code SHALL be prefilled as a slug of the name, following the name until the organizer edits it, and SHALL be unique within the tournament; two tournaments MAY use the same code independently. An empty limit SHALL mean unlimited uses. A limit SHALL be at least 1.

The effect SHALL be either a **fixed amount** off the whole total, carrying an amount per configured currency as any fixed discount does, or a **percentage**, which is currency-neutral and SHALL apply to the whole total or to the categories the organizer selects, drawn from the same categories automatic discounts are scoped by. A fixed effect's missing EUR amount on a tournament that prices in EUR SHALL be reported as a missing discount price, exactly as an automatic discount's is.

#### Scenario: Code prefilled from the name
- **WHEN** the organizer types the name "Trenéři HEMA" into a new code's row
- **THEN** the code field reads `treneri-hema` and keeps following the name until the organizer edits it

#### Scenario: Duplicate code refused
- **WHEN** the organizer saves a second code reading `treneri-hema` on the same tournament
- **THEN** the save is refused with a field error on the code

#### Scenario: Percentage of selected categories
- **WHEN** the organizer defines −20 % scoped to disciplines, and a fencer entering two disciplines and buying a t-shirt redeems it
- **THEN** the discipline subtotal is reduced by 20 % and the t-shirt is billed in full

#### Scenario: Fixed code on a two-currency tournament
- **WHEN** a fixed code on a CZK + EUR tournament carries 500 Kč and no EUR amount
- **THEN** Setup reports a missing discount price and the tournament's publication check treats it as it treats an automatic discount's

### Requirement: A code in use cannot change what it means
While any registration carries a code, its effect, its scope and its code text SHALL NOT be changed, and it SHALL NOT be deleted. Its name and limit SHALL remain editable. The limit MAY be lowered to the current number of uses, which retires the code for anyone else, and SHALL NOT be lowered below them. A code no registration carries SHALL be deletable.

#### Scenario: Editing a used effect
- **WHEN** the organizer tries to change a used code from −10 % to −20 %
- **THEN** the change is refused and the effect fields say why

#### Scenario: Retiring a code
- **WHEN** a code limited to 10 with 3 uses is lowered to 3
- **THEN** the three registrations keep their discount and the code reads as nonexistent to everyone else

#### Scenario: Limit below uses
- **WHEN** the same code is lowered to 2
- **THEN** the save is refused with a field error on the limit

### Requirement: An unusable code reads as if it never existed
A code SHALL match trimmed, regardless of case and diacritics. A code that does not exist, belongs to another tournament or has reached its limit SHALL receive one and the same refusal, indistinguishable by content, so that no answer discloses that a code once existed or has run out.

#### Scenario: Exhausted and invented alike
- **WHEN** one fencer submits a code that has reached its limit and another submits a string that was never a code
- **THEN** both receive the identical refusal

#### Scenario: Typed loosely
- **WHEN** a fencer types ` ŠKOLA` for the code `skola`
- **THEN** it matches

### Requirement: A registration carries at most one code, priced with the automatic discounts
A registration SHALL carry at most one code. A code SHALL stack with every automatic discount that applies and SHALL be evaluated by the same computation, in the same order: fixed effects first, then percentage effects, the code following the automatic discounts within each. A fixed code SHALL floor at zero, as a fixed discount does.

A code SHALL price on every tournament, whether or not it uses itemized pricing, and defining one SHALL NOT change which pricing a tournament uses or stop any fee it bills.

Every computation of a registration's price — an amendment, a promotion from the queue, a claim, a substitution, a reprice of any kind — SHALL apply the code it carries, whether or not the code is still available to others.

#### Scenario: A fixed code under an automatic percentage
- **WHEN** a fencer's disciplines cost 2000 Kč, an early-bird of −15 % applies, and the fencer redeems a −500 Kč code
- **THEN** the total is 1275 Kč: the fixed code first, the percentage on what remains

#### Scenario: A disciplines-only tournament
- **WHEN** a code is defined on a tournament with no extra items and no automatic discounts
- **THEN** it prices, and the tournament keeps its pricing

#### Scenario: Legacy fees still billed
- **WHEN** a code is defined on a tournament still billing the flat rental fee
- **THEN** the rental fee continues to be billed, and a whole-total code reaches it

#### Scenario: A queued registration admitted later
- **WHEN** a registration holding a −10 % code waits in the queue, owing nothing, and is admitted
- **THEN** it is billed the admitted discipline less 10 %

#### Scenario: The code runs out after use
- **WHEN** a code reaches its limit and an earlier holder amends their registration
- **THEN** the amended total still carries the code

### Requirement: Uses are live registrations
The uses of a code SHALL be the number of live registrations carrying it, waiting in the queue or not, and SHALL NOT be a stored count. A cancellation or an expiry, by whoever or whatever caused it, SHALL give the use back.

A limit SHALL hold under concurrent redemption: of two registrations racing for the last use, one SHALL succeed and the other SHALL be refused with nothing created.

A registration revived after expiring SHALL keep its code and its discount even where that takes the uses past the limit, since the money that revived it was sent against the total it was quoted. A re-registration is a new cycle: it SHALL carry only the code it submits, claimed afresh.

#### Scenario: Cancellation frees a use
- **WHEN** a holder of a single-use code cancels
- **THEN** the code becomes usable by someone else

#### Scenario: The race for the last use
- **WHEN** two fencers submit the same code with one use left at the same moment
- **THEN** one registration is created with the discount and the other submission is refused, creating nothing

#### Scenario: Revival overruns the limit
- **WHEN** an expired holder of a single-use code, since taken by another fencer, is reinstated by a late payment
- **THEN** both keep the discount, the uses read 2 of 1, and the code stays unavailable to others

#### Scenario: Re-registering without the code
- **WHEN** a holder cancels and registers again submitting no code
- **THEN** the new registration carries no code and pays the full price

### Requirement: A code that covers the price leaves nothing to do
A registration whose total a code brought to zero in a lane SHALL owe nothing and SHALL read as settled as `payment-ledger` fixes, on no action by anyone. It SHALL NOT be sent a payment reminder, SHALL NOT expire for non-payment, and its confirmation SHALL state that nothing is to be paid, carrying no QR code and no payment instructions.

If an amendment leaves something owed, the registration SHALL stop reading as settled and SHALL open a fresh payment window, exactly as an amendment that unsettles any settled registration does.

No money having moved, cancelling such a registration SHALL record no refund standing.

A registration waiting wholly in the queue whose claim, as `seating-queue` fixes it, a code brought to zero SHALL hold no claim: it SHALL be offered no payment and SHALL be told nothing about paying, and it SHALL wait for the organizer to admit it. A claim a code reduces without covering SHALL stand at the reduced amount.

#### Scenario: A 100 % code on a paying tournament
- **WHEN** a fencer redeems a −100 % code for a 1500 Kč entry in immediate-payment mode
- **THEN** the confirmation states nothing is to be paid, the registration reads as paid, and no reminder or expiry ever reaches it

#### Scenario: A voucher larger than the bill
- **WHEN** a fixed code of −2000 Kč meets a total of 1500 Kč
- **THEN** the total is zero and the registration reads as paid

#### Scenario: Cancelling a covered registration
- **WHEN** a fencer whose total a code covered cancels before the refund deadline
- **THEN** the registration is cancelled with no refund pending and the use is given back

#### Scenario: A code covers a paying substitute's claim
- **WHEN** a registration holding a −100 % code waits wholly in the queue on a tournament where paying substitutes take free places
- **THEN** it holds no claim, is shown no payment instructions, and waits for the organizer to admit it

#### Scenario: An amendment leaves something owed
- **WHEN** a holder of a −1500 Kč voucher, covered in full, adds a 300 Kč item
- **THEN** the registration owes 300 Kč, stops reading as paid, and is given a fresh payment window

### Requirement: A code is private
No code, and nothing stating a code's name, effect or use, SHALL appear on any surface a visitor can read: the tournament detail, the discount list, the entrants rosters, or any endpoint reachable without console access. The public SHALL learn only whether the tournament currently accepts codes, by the field being offered. A fencer SHALL see the discount their own registration carries, and the name of the code it came from, and no one else's.

#### Scenario: The detail discloses nothing
- **WHEN** a visitor reads a tournament with three codes
- **THEN** the response carries no code, no code name and no code effect, only that codes are accepted

#### Scenario: Roster silent
- **WHEN** the entrants roster lists a fencer holding a code
- **THEN** nothing in the row differs from any other paid or unpaid fencer

### Requirement: Guessing is throttled
A preview that carries a code SHALL be rate-limited per client address, generously enough for a live form behind one shared address. A preview that carries none SHALL NOT be limited by this.

#### Scenario: Rapid guessing
- **WHEN** one address submits more previews with a code than the limit allows within a minute
- **THEN** the excess is refused with a rate-limit response and discloses nothing about any code

