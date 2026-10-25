## Context

`docs/emails.md` (section 5) records eight defects in how Squire composes and sends mail. They were found by reading the code. Each was confirmed against the code on 2026-10-25, and the owner decided its fix the same day. The mail code sits in one module, `backend/app/emails.py`. Each `send_*` function composes one message and hands it to `mailer.send`. `mail.get_mailer` returns the transport: `SmtpMailer` when `smtp_host` is set, the file outbox otherwise. The request handlers and the scheduler call the `send_*` functions directly, most of them after `session.commit()`.

`guest-registration` is in flight and uncommitted. It introduced `settings.public_base_url`, the `_letter` helper through which every registration message is built, and the guest manage link that `_letter` appends. This change builds on all three and is implemented after that change lands.

Confirmed mechanisms the decisions below rest on:

- `payment_spayd` defaults each QR code to `registration.total_amount` / `total_eur`. `send_payment_reminder` passes no override. The reminder after a credited deposit therefore encodes the full total.
- `send_registration_confirmation` and `send_payment_reminder` render `expires_at.date().isoformat()` or `-`. The Czech copy says "místo se automaticky uvolní" in every mode.
- `routers/payments.reinstate_transaction` (around line 647) credits the transaction and calls `send_reservation_reinstated` without comparing the amount. The automatic grace path in `matching.py` goes through `_settle(reinstated=True)`. Its partial branch ignores `reinstated` and sends the plain partial-payment mail.
- `scheduler.process_composition_reminders` filters only on state, waitlisting and stamp. It has no dormancy or hand-entry check.
- `scheduler.run_tick` shares one session across tournaments and logs an exception without rolling back. The next tournament's `commit()` then persists the failed tournament's partial stamps, among them the `reminded_at` of the registration whose send raised.

## Goals / Non-Goals

**Goals:**
- Every amount a message asks for, and every QR code it carries, is what the fencer should actually pay now.
- No message states a consequence the tournament's mode does not have.
- Mail cannot fail an action, and cannot be lost or doubled by a partly failed batch.
- English tournaments write in English, enforced by a test.
- One date format and one tournament link, applied in one place each.

**Non-Goals:**
- Mail to hand entries with an address (the 2026-09-25 follow-up stays queued).
- Any mail to organizers.
- Rewording messages beyond what the findings require.
- HTML mail.

## Decisions

### D1. Deposit-mode payment block: two codes per currency, labelled

The confirmation in `deposit` mode, and a reminder sent before anything is credited, carry a deposit code and a total code per currency. There are two codes on a CZK-only tournament and four on CZK + EUR. Each is labelled in the body ("Záloha (CZK)", "Celá částka (EUR)") and in its attachment filename (`qr-zaloha-czk.png`, …). `payment_qrs` gains a mode-aware sibling, `payment_qr_set(tournament, registration) -> list[LabelledQr]`, so that no caller assembles codes by hand. `build_message` takes that list instead of the fixed `qr` / `qr_eur` pair, and the existing callers pass one or two entries.

*Owner's choice* over a single deposit code or a single total code: the fencer decides whether to pay in one go or in two.

*Alternative rejected:* encoding the deposit as the only code would make paying in one go a manual entry, and that is exactly the error the codes exist to prevent.

### D2. Once credit exists, every code encodes what is outstanding

The reminder computes `outstanding_in("local")` and `outstanding_in("eur")` and passes them as the override amounts, which `payment_spayd` already supports. This matches the existing `payments` scenario "Deposit paid, balance outstanding". With credit present the deposit codes are dropped. The deposit is then paid, and a deposit code would ask for it a second time.

### D3. Mode decides the "when" paragraph, in one place

A helper `_due_paragraph(tournament, registration, lang)` returns the localized paragraph for `immediate` (window close and release), `deposit` (deposit by the window close, balance by the seating deadline) and `reservation` (total by the seating deadline, moved to the queue that day). The confirmation, the amendment and the reminder interpolate it as `{due}`, which replaces the fixed `Rezervace platí do:` line and the "automaticky uvolní" sentence. The seating deadline is the effective one (`setup.seating_deadline_for`), the same value the Setup option texts show.

### D4. Reinstatement goes through `_settle`; the shortfall gets its own message

`reinstate_transaction` stops crediting and mailing on its own. After the credit it calls `matching._settle(..., reinstated=True)`, the step every other credit uses. In `_settle`, a partial outcome with `reinstated=True` sends `email.reinstatedPartial`: reinstated, the amount received, the amount still due, and a QR code for the remainder. It replaces the plain partial-payment mail. A full outcome sends `email.reinstated` as now.

A reinstatement that leaves money owed opens a fresh payment window of `payment_window_days` from now. The window it had has already closed. Without a fresh window the next scheduler pass would expire the registration again within minutes. This follows the precedent of the owner's 2026-09 decision that an upward amendment unsettles a registration and opens a fresh window, and the owner confirmed it on 2026-10-25.

The `{total}` in `email.reinstated` becomes the amount credited, for the same reason as finding 8.

### D5. Composition reminder: guard and stamp move together

`process_composition_reminders` skips a team whose registration satisfies `emails._dormant_by_origin`, before it groups by fencer, and leaves `composition_reminded_at` unset. The stamp keeps meaning "a message was queued". The check lives in the scheduler query path, not in `send_composition_reminder`. The function then cannot silently send nothing while its caller stamps.

### D6. The tournament link is appended by `_letter`

`_letter` already appends the guest manage link to every registration message. It appends the tournament link (`{public_base_url}/t/{slug}`, spelled the way `routes.detail` spells it) before the manage link, as one localized line (`email.tournamentLink`). Every registration send already passes through `_letter`, so no send can miss the link. The signup verification mail is not about a registration and stays as it is. A test enumerates the `send_*` functions and asserts that each output contains the link. That catches a future send that bypasses `_letter`.

### D7. One date formatter, pattern from the locale

`i18n.format_date(day, lang)` reads `email.date.format` (`"{d}. {m}. {y}"` in cs, `"{d} {monthName} {y}"` in en) and, for en, `email.date.months` (twelve names). The pattern lives in the locale, so a third language adds no code. An instant (`expires_at`) is converted with `setup.local_date(tournament, instant)` before formatting. This is display only: the boundary itself stays an instant compared on UTC (day-boundaries). `_due_text` and every `.isoformat()` in `emails.py` go through the formatter.

*Alternative rejected:* Babel. A new dependency for two patterns and twelve month names is not worth it.

### D8. Durable outgoing mail

**Model.** `OutgoingMail`: `id`, `created_at`, `recipient`, `subject`, `raw` (the serialized `EmailMessage`, attachments included, as `LargeBinary`), `attempts`, `last_error`, `claimed_at`, `sent_at`, `failed_at`. The model has no foreign keys. A message outlives anything it is about.

**Queueing.** `mail.QueuedMailer(session)` implements the existing `Mailer` protocol. Its `send` adds an `OutgoingMail` row to the given session. None of the `emails.send_*` functions changes, because they still receive "a mailer".

**Request path.** `MailerDep` resolves to a `QueuedMailer` over the request's session. The dependency yields it, and its teardown runs after the handler. If the handler raised, the teardown does nothing, because the session's rollback discards the rows. Otherwise it commits, which persists rows queued after a handler's own `commit()`; most handlers today commit and then send. It then delivers the rows it queued through the transport from `get_mailer()`. Delivery failures are recorded on the row and never raised. The handlers that commit and then send can stay as they are. The cost is a narrow window: a crash between the handler's commit and the teardown's commit loses the message. That window is far smaller than today's, where any SMTP failure turns into a 500. Handlers touched by this change for other reasons (D4) queue before they commit.

**Scheduler path.** `run_tournament_tick` wraps the transport in a `QueuedMailer` over its session. The passes stay unchanged. Each pass's existing `commit()` persists its messages together with its stamps. At the end of each tick, `deliver_pending(session, transport)` delivers every row with `sent_at` and `failed_at` null.

**Claiming.** A row is delivered only after an atomic claim, `UPDATE … SET claimed_at = now WHERE id = :id AND sent_at IS NULL AND (claimed_at IS NULL OR claimed_at < now - 10 min)`, checked by its row count. A request's teardown and a scheduler tick can then never both send one row. The claim works on SQLite and Postgres alike.

**Secrets at rest.** A verification, password-reset or guest message carries a key that the database otherwise holds only as a hash. `raw` is therefore set to null as soon as a row is sent or marked failed, and only recipient, subject and timestamps are kept. A key sits in the table in clear only while its message waits for delivery, normally for seconds.

**Retry budget.** A row is retried on every tick while it is younger than 48 hours. After that it gets `failed_at` and an error log. The budget matches the expiry grace: a message older than that describes a state the fencer has most likely already moved past.

**Delivery semantics.** Delivery is at-least-once at the transport boundary. A crash after SMTP accepts a message but before `sent_at` commits resends it once. Exactly-once delivery is not achievable over SMTP. The rest of the design narrows the window to that single step.

**Tests.** The test fixtures override `get_mailer` with a collecting transport. Because the teardown delivers before the client call returns, a test that reads the mailbox right after a request still sees its mail. Tests that call `process_*` with a mailer directly keep getting immediate sends. Only `run_tick` and the request path go through the queue.

*Owner's choice* over log-and-continue, which keeps actions from failing but loses the message.

### D9. `run_tick` rolls back per tournament

`run_tick` calls `session.rollback()` in its `except` before it continues. With D8 the rollback discards the stamps and the queued rows together. That is the invariant the `outgoing-mail` spec states: a stamp exists exactly when its message was queued.

### D10. English locale and parity test

The 19 missing `email.*` keys are added to `en.json` as translations of the Czech, in sentence case without exclamation marks. A parity test walks both backend locales and fails on any `email.*` key missing from one of them. It sits beside the existing validation parity test.

## Risks / Trade-offs

- [Four QR codes crowd a message] → Labels in the body and the filenames. The deposit pair disappears from every later reminder once credit exists.
- [The teardown's commit persists something a handler left uncommitted on purpose] → No handler relies on uncommitted state being discarded on success. A grep for handlers that end without a commit is part of the tasks, and each one found is checked.
- [Delivery adds latency to every mailing request] → Same as today, since the request already sends synchronously. A later move to a background task is possible without changing the model.
- [The outbox grows forever] → Once `raw` is scrubbed a row is a few hundred bytes of send log, kept indefinitely.
- [The fresh window on reinstatement (D4) extends a fencer's time to pay beyond what the organizer may expect] → It applies only where the money falls short, and the organizer chose to reinstate.

## Migration Plan

One Alembic revision creates `outgoing_mail`. Nothing existing is migrated, because mail sent before the deploy is not in the table. Rollback drops the table. The code path then returns to direct sending, which works and has the old failure modes.

## Open Questions

- **The Czech and English wording** of the new paragraphs (`_due_paragraph`, `email.reinstatedPartial`, `email.tournamentLink`, the QR labels) goes to the owner before the locales are final.
