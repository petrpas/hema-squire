## Why

`docs/emails.md` inventories every message Squire sends, and its section 5 lists eight defects found by reading the code. Some of them cost money or trust:

- A deposit-mode fencer who has paid the deposit is sent a reminder whose QR code asks for the full total, so following it overpays.
- A reservation-mode confirmation promises an expiry that never happens.
- An organizer's reinstatement tells a fencer who still owes money that the registration is paid.
- An English tournament sends its six most common messages in Czech.
- A failed SMTP send returns 500 for an action that already took effect, and in the scheduler it can stamp a reminder that was never delivered.

The owner reviewed each finding on 2026-10-25 and decided how it is to be fixed.

## What Changes

- **Deposit-mode confirmation states the deposit.** It names the deposit, the date the payment window closes, and the balance due by the seating deadline. It carries two QR codes, one for the deposit and one for the full total. Where the tournament also takes EUR there are four, each labelled with what it pays and in which currency. After the deposit is credited, the reminder states the outstanding balance and its QR code encodes that balance, as `payments` already requires.
- **Reservation-mode confirmation and reminder state the seating deadline.** They say that the full amount is due by the seating deadline and that an unpaid seat is moved to the substitute queue on that day. They no longer print `Rezervace platí do: -` or "místo se automaticky uvolní".
- **Reinstatement with a shortfall.** A reinstatement, whether automatic within grace or by the organizer, whose credit leaves more than tolerance outstanding sends a new variant of the reinstatement message. It says the reservation was reinstated, states the amount received and the amount still due, and carries a QR code for the remainder. The organizer's reinstatement goes through the same settle step as a matched payment, so it no longer claims that the registration is paid.
- **The composition reminder is guarded.** It is not sent to a hand entry or to an imported registration, the same rule the confirmation follows.
- **Every registration message carries a link to the tournament page.** The link is plain and grants nothing by itself. A guest's message keeps its manage link as well. For the composition reminder, this link is the way to the roster editor that `team-disciplines` requires.
- **Dates in messages are formatted by language:** `25. 10. 2026` in Czech and `25 October 2026` in English, from one function. ISO dates and `%d.%m.%Y` both go.
- **English is complete for mail.** The 19 missing `email.*` keys are added. A parity test fails on any `email.*` key missing from a bundled locale, as it already does for validation messages.
- **Durable outgoing mail.** A message is written to an outgoing-mail table inside the same transaction as the action that caused it. It is delivered after the commit and retried until it is sent. An action never fails because of mail, and a message is never lost or sent twice because of a partly failed batch. After an exception, the scheduler rolls back the tournament it was processing before it moves to the next one.
- **`email.seatedByPayment` states the amount received**, not the registration's total.
- `docs/emails.md` is updated to the state after this change. The update also covers what `guest-registration` added: the verification mail and the manage link.

Out of scope: mail to hand entries with an address (the follow-up decided 2026-09-25) and any mail to organizers.

## Capabilities

### New Capabilities
- `outgoing-mail`: how every message leaves Squire. Covers durable queued delivery with retry, the tournament link every registration message carries, and the language-dependent date format.

### Modified Capabilities
- `registration`: "Confirmation email with QR payment" gains what a deposit-mode and a reservation-mode confirmation state, and the deposit QR codes.
- `payments`: "Payments arriving after expiry" covers a reinstatement whose credit falls short, for the automatic and the organizer's path alike. "Reminders and expiry notices" says that a reminder after a credited deposit encodes the outstanding balance in its QR code.
- `team-disciplines`: "Composition reminder to the entering fencer" is not sent to a hand entry or an imported registration. Its link to the roster editor is the tournament link, or the manage link for a guest.
- `localization`: "Fully localized from the start" extends the locale parity test to every `email.*` key.

## Impact

- **Backend.** `emails.py`: deposit and reservation variants of the confirmation and the reminder, the reinstatement shortfall variant, the composition guard, the tournament link in `_letter`, one date formatter. `payment_qrs` produces the deposit pair. `routers/payments.reinstate_transaction` and the grace path in `matching.py` settle through `_settle(reinstated=True)`. `mail.py`: an `OutgoingMail` model and a queueing mailer that writes into the request's session, plus a delivery pass run after each request and on each scheduler tick. `scheduler.run_tick` rolls back after a failure. There is one Alembic revision.
- **Locales.** `cs.json` and `en.json`: new keys for the deposit, reservation and shortfall wording, the tournament link line, and the 19 English keys. The parity test is extended.
- **Tests.** Deposit confirmation with two and four QR codes, the deposit-paid reminder encoding the balance, the reservation-mode wording, organizer and automatic reinstatement with a shortfall, the composition guard, the link in every send, date format per language, email locale parity, a send failure leaving the action committed and the message delivered on retry, and a failed scheduler batch neither stamping an unsent reminder nor resending a sent one.
- **Ordering.** This change builds on `guest-registration`: it uses `public_base_url` and `_letter`. It is implemented after that change lands.
