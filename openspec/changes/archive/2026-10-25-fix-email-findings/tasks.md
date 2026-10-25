## 0. Prerequisite

- [x] 0.1 `guest-registration` is implemented and committed (this change uses `public_base_url`, `_letter` and the manage link)
- [x] 0.2 Confirm with the owner the fresh payment window on a short reinstatement (design D4, open question)

## 1. Durable outgoing mail (design D8, D9)

- [x] 1.1 `models.py`: `OutgoingMail` (recipient, subject, raw, attempts, last_error, claimed_at, sent_at, failed_at, created_at), no foreign keys; Alembic revision creating `outgoing_mail`, downgrade drops it
- [x] 1.2 `mail.py`: `QueuedMailer(session)` implementing `Mailer`; `deliver_pending(session, transport, ids=None)` with the atomic claim, the attempt and error record, `sent_at` on acceptance, and `failed_at` plus an error log past 48 h; `raw` nulled on sent and on failed
- [x] 1.3 The request `MailerDep` (all four routers) becomes a yield dependency: a `QueuedMailer` over the request session; on success the teardown commits and delivers its own rows; on an exception it does nothing
- [x] 1.4 Grep the handlers that take `MailerDep` and end without a commit; confirm for each that a commit at teardown persists nothing unintended
- [x] 1.5 `scheduler.run_tournament_tick` queues through `QueuedMailer`; `run_tick` calls `deliver_pending` after each tournament and `session.rollback()` in its `except`
- [x] 1.6 Tests: SMTP failure during register → 2xx, registration exists, row queued with the error, delivered by the next tick; a rolled-back action queues nothing; a delivered row is not resent; concurrent claim delivers once; a pass raising mid-batch leaves no stamp and no row, and the next tick reminds each registration once

## 2. Dates and link (design D6, D7)

- [x] 2.1 `i18n.format_date(day, lang)` reading `email.date.format` / `email.date.months` from the locales; cs `25. 10. 2026`, en `25 October 2026`
- [x] 2.2 Replace every `.isoformat()` and `_due_text`'s `strftime` in `emails.py` with it; instants go through `setup.local_date` first
- [x] 2.3 `_letter` appends `email.tournamentLink` (`{public_base_url}/t/{slug}`) before the manage link
- [x] 2.4 Tests: every `send_*` that builds a registration message carries the tournament link; a guest's message carries both links and an account holder's only the first; dates read alike in confirmation and promotion (cs) and as `1 March 2027` (en)

## 3. Payment-mode wording and QR codes (design D1–D3)

- [x] 3.1 `payment_qr_set(tournament, registration)` returning labelled codes: total per currency; in `deposit` mode with no credit, deposit and total per currency; with credit, the outstanding balance per currency. `build_message` takes the list and names each attachment by its label
- [x] 3.2 `_due_paragraph(tournament, registration, lang)` for `immediate` / `deposit` / `reservation`, using `seating_deadline_for` and the window close; confirmation, amendment and reminder interpolate `{due}` in place of the `Rezervace platí do` line and the release sentence
- [x] 3.3 Reminder passes the outstanding amounts once the registration holds credit
- [x] 3.4 Tests: CZK-only deposit confirmation carries the 500 and 1800 codes, each labelled; CZK + EUR carries four; deposit-paid reminder states 1300 and encodes 1300; reservation-mode confirmation and reminder name the seating deadline and the queue and state no expiry; an immediate-mode confirmation is unchanged apart from the date format

## 4. Reinstatement (design D4)

- [x] 4.1 `reinstate_transaction` settles through `matching._settle(..., reinstated=True)` instead of mailing directly; queue before commit
- [x] 4.2 `_settle`: on a partial outcome with `reinstated=True`, open a fresh payment window and send `email.reinstatedPartial` (received, still due, QR for the remainder)
- [x] 4.3 `email.reinstated` and `email.seatedByPayment` state the amount credited, not the total
- [x] 4.4 Tests: organizer reinstatement on 500 of 1800 → reserved, owing 1300, fresh window, the shortfall mail without "potvrzena"; automatic grace reinstatement on 500 → the same single mail, no plain partial mail; a full reinstatement is unchanged; the seated-by-payment mail states the amount paid

## 5. Composition reminder (design D5)

- [x] 5.1 `process_composition_reminders` skips teams whose registration is `_dormant_by_origin`, without stamping
- [x] 5.2 Tests: a hand entry and an imported registration with short teams get no mail and no stamp; an ordinary short team is reminded once, with the tournament link

## 6. Locales (design D10)

- [x] 6.1 Add the 19 missing `email.*` keys to `en.json`; add the new keys (`_due_paragraph` variants, `reinstatedPartial`, `tournamentLink`, QR labels, `email.date.*`) to both locales
- [x] 6.2 Parity test: every `email.*` key in every bundled backend locale
- [x] 6.3 Put the new Czech and English wording to the owner (design open question) and apply their edits

## 7. Close-out

- [x] 7.1 Update `docs/emails.md` to the post-change state: queued delivery, the link, deposit/reservation wording, the reinstatement variant, the composition guard, the verification mail and manage link from `guest-registration`; strike the findings this change resolved
- [x] 7.2 `uv run ruff check .`, `uv run basedpyright`, scoped `pytest` (`tests/test_matching.py`, `tests/test_scheduler.py`, the new mail tests) clean
- [x] 7.3 Read a deposit-mode confirmation, a reservation-mode reminder and a short reinstatement from the file outbox, in Czech and English
