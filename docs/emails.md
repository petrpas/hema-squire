# Email inventory

Every message Squire sends, what triggers it, and what keeps it from being sent.
Taken from the code as of change `fix-email-findings` (2026-10-25), which
resolved the findings of the first inventory (section 5).

## 1. Mechanism

- All composition lives in `backend/app/emails.py`; every message passes through
  `mail.build_message`, which raises `NoRecipientError` rather than send to nobody.
- **Delivery is queued** (`app/outgoing.py`, spec `outgoing-mail`). A send writes
  an `outgoing_mail` row into the session of the action that caused it, so the
  message commits or rolls back with its cause. Requests deliver their own rows
  after the commit (the `queued_mailer` dependency); the scheduler delivers
  whatever is still waiting at the end of every tick. A failed send stays on the
  row with its error and is retried for 48 hours, then marked failed and logged.
  An action never fails because of mail. `raw` is nulled once a row is sent or
  failed, so verification, reset and guest keys do not stay in the table.
- A scheduler tick that raises for one tournament is rolled back before the next,
  so a stamp (`reminded_at`, expiry, `demotion_notified`) exists exactly when its
  message was queued.
- The recipient is `emails.recipient`: the registration's own contact address
  where it has one, the account holder's otherwise.
- The language is the tournament's communication language (`tournament.language`);
  account mail uses the account's language. Every `email.*` key exists in both
  `cs.json` and `en.json` (parity test in `tests/test_i18n.py`); Czech remains
  the fallback for a locale added later.
- **Every registration message ends with the tournament link** (`{public_base_url}/t/{slug}`),
  added by `emails._letter`; a guest's message carries its manage link as well.
  Account mail (verification, reset, password changed) carries neither.
- **Dates** go through `i18n.format_date`: `25. 10. 2026` in Czech, `25 October 2026`
  in English; an instant is stated as its day in the tournament's zone.
- `get_mailer` picks the transport: `SmtpMailer` when `smtp_host` is set, the file
  outbox otherwise. With SMTP set, `public_base_url` must be set too (`app.main`).
- **Only fencers and account holders are written to.** No mail goes to an
  organizer or the owner.

## 2. Suppression rules

| group | guard | nothing is sent when |
|---|---|---|
| payment mails | `_payment_mail_suppressed` | payments are off; the registration is a hand entry; the registration is dormant (imported). The one exception: the surcharge after an organizer's discipline correction passes `despite_dormancy` and reaches an imported registration. |
| confirmation, amendment, promotion | `dormant_by_origin` | the registration is imported or a hand entry. With payments off the no-payment variant is sent instead. |
| composition reminder | `dormant_by_origin`, in `scheduler.process_composition_reminders` | the registration is imported or a hand entry; such a team is not stamped |
| substitution, organizer cancel | `_entered_by_hand` | the registration is a hand entry |
| everything the scheduler sends | `scheduler.tournaments_to_tick` | the tournament is manual (`registrations_kept_by = organizer`), a draft, or already held |

## 3. What is sent

Subjects are the Czech ones from `app/locales/cs.json`; each registration
message ends in `— {tournament}`.

### The payment block

The confirmation (1), the amendment (4), the reminder (12) and a short
reinstatement (8b) share one block, `emails._payment_block`, which states the
amounts, the consequence and the QR codes by payment mode:

| case | amounts | consequence | QR codes |
|---|---|---|---|
| `deposit`, window running | deposit by the window's close; total, balance by the seating deadline | deposit holds the seat; unpaid by the seating deadline → queue | deposit and total, per currency (`platba-zaloha`, `platba-celkem`, `-eur`): two or four |
| credit already held (deposit paid, partial) | what is outstanding, by the window's close (`immediate`) or the seating deadline | released (`immediate`) / moved to the queue | the outstanding balance (`platba-doplatek`) |
| `reservation` | total by the seating deadline | moved to the queue that day | total |
| `immediate` | total by the window's close | released automatically | total |

### Fencer actions

| # | message | key | trigger | QR |
|---|---|---|---|---|
| 1 | Registrace na X — pokyny k platbě | `email.confirmation` | `POST /register` (or guest registration), seated, payments on | block |
| 2 | Registrace na X — potvrzení | `email.confirmationNoPayment` | the same, payments off | — |
| 3 | Zařazení do fronty náhradníků | `email.queued.body` / `.bodyClaim` | wholly queued; `bodyClaim` where paying substitutes take free places | claim only |
| 4 | Úprava registrace — pokyny k platbě | `email.amendment` / `.queuedBody` / `email.amendmentNoPayment` | `POST /my-registration/amend` on an unpaid registration | block |
| 5 | Doplatek k registraci | `email.surcharge` | the same amend on a paid registration that now owes; a paid one that owes nothing gets no mail | yes |

### Payments

Reached from statement import, Fio poll (console and scheduler), a payment link,
a confirmed proposal, a recorded manual payment, and the tolerance resettle.

| # | message | key | trigger |
|---|---|---|---|
| 6 | Platba přijata | `email.paid` | a credit brings the registration within tolerance (`matching._settle`, `resettle_within_tolerance`) |
| 7 | Přijali jsme částečnou platbu | `email.partial` | a credit leaves more than tolerance outstanding; states the remainder |
| 8 | Rezervace obnovena, platba přijata | `email.reinstated` | a reinstatement — within grace with a seat free, or the organizer's `POST /transactions/{id}/reinstate` — whose credit settles the registration; states the amount received |
| 8b | Rezervace obnovena, zbývá doplatit | `email.reinstatedPartial` | the same, where the credit falls short; a fresh payment window opens, and the payment block states what is due |
| 9 | Platba přijata po vypršení rezervace | `email.afterExpiry` | payment on an expired registration outside grace or with no seat |
| 10 | Platba přijata, čekáš ve frontě | `email.paymentWhileQueued.body` / `.bodyNoPlace` / `.bodyAmountMismatch` | payment on a wholly queued registration, first time it is held |
| 11 | Máš místo | `email.seatedByPayment` | a held payment of the claim seats every waited-for discipline; states the amount paid |

Both reinstatement paths go through `matching._settle(reinstated=True)`; the
organizer's is `matching.reinstate_by_organizer`, and refuses a payment in a
currency the tournament does not price (`409 currency_not_accepted`).

### Scheduler

Also reached from the console's `POST /process` and the settle-seating-early button.

| # | message | key | trigger | QR |
|---|---|---|---|---|
| 12 | Připomínka platby | `email.reminder` | reminder day reached before the window or the seating deadline | block |
| 13 | Rezervace vypršela / …, platbu držíme | `email.expired` / `email.expiredHoldingPayment` | window lapsed; the second where some money was credited | — |
| 14 | Přesun do fronty náhradníků | `email.demoted.body` / `.bodyClaim` | seating settlement, a lapsed promotion, a seat lapsed to the queue; recorded as `demotion_notified` | claim only |
| 15 | Připomínka soupisky | `email.compositionReminder` | within `reminder_day` of the composition deadline, once per short team; the tournament link is the way to the roster editor | — |

### Organizer actions

| # | message | key | trigger | QR |
|---|---|---|---|---|
| 16 | Uvolnilo se místo | `email.promoted` / `.promotedPaid` / `.promotedNoPayment` | `admit_substitute`, `admit_team` | owing only |
| 17 | Přebíráš místo | `email.substituteArrived` / `.substituteArrivedSettled` | substitution rule, manual tournaments excluded (`rules_api._announce_substitution`) | owing only |
| 18 | Tvé místo přebírá někdo jiný | `email.substituteDeparted` | the same, to the departing fencer; skipped where the address was kept; tournament link only, never the seat's manage link | — |
| 19 | Doplatek k registraci | `email.surcharge` | an amendment rule created or withdrawn that raises the total and leaves money owed | yes |
| 20 | Registrace zrušena | `email.cancelledByOrganizer` | `POST /registrations/{id}/cancel`; carries the organizer's note and, where money arrived, the refund sentence | — |
| 21 | Odkaz na tvou přihlášku | `email.manageLinkResent` | the organizer resends a guest's manage link (`POST /registrations/{id}/manage-link`) | — |

### Accounts

| # | message | key | trigger |
|---|---|---|---|
| 22 | Dokonči založení účtu v HEMA Squire | `email.verifySignup` | `POST /api/auth/signup`, `POST /api/auth/resend-verification` |
| 23 | Obnovení hesla v HEMA Squire | `email.passwordReset` | `POST /api/auth/password-reset` |
| 24 | Heslo k HEMA Squire bylo změněno | `email.passwordChanged` | `POST /api/account/password` |

## 4. What is not sent

- **Silent organizer actions:** return to queue, team back to waitlist,
  substitution withdrawn, mark settled / waiver, credit reversal, uncrediting a
  recorded payment, refund marking, Smazat.
- **Silent fencer actions:** the fencer's own cancel (no confirmation), roster edit.
- **Accounts:** no welcome mail beyond the verification link.
- **Organizers:** never mailed, though several letters tell the fencer the
  organizer "will be in contact" (7, 9, 10, 13); the organizer learns of these
  only from the console queues.
- **Hand entries:** follow-up decided 2026-09-25 (substitution and surcharge to
  reach hand entries with an address) is not implemented; `_entered_by_hand` still
  blocks both.

## 5. Findings of the first inventory

All resolved by `fix-email-findings` unless noted.

1. ~~English is missing six core messages.~~ All `email.*` keys exist in both
   locales, enforced by a parity test.
2. ~~Reservation mode states the wrong consequence; deposit mode never mentions
   the deposit.~~ The payment block (section 3). The deposit-paid reminder now
   encodes the outstanding balance rather than the full total.
3. ~~The composition reminder has no guard and no link.~~ Guarded by
   `dormant_by_origin`; carries the tournament link.
4. ~~Organizer reinstate may claim full payment.~~ It settles through
   `_settle`; a shortfall gets message 8b and a fresh window. The automatic
   path's shortfall, which sent only the partial notice, gets 8b too.
5. ~~Date formats differ.~~ One formatter per language.
6. ~~No mail carries a link.~~ The tournament link in every registration message.
7. ~~SMTP failure is not handled.~~ Queued delivery with retry; the scheduler
   rolls back a failed tournament.
8. ~~`email.seatedByPayment` states the total.~~ It states the amount paid, as
   does `email.reinstated`.

Still open: the copy of the new paragraphs awaits the owner's review, and
`email.paid` / `email.reinstated` keep an exclamation mark in Czech.
