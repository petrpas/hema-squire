## 1. Verification in the bank client

- [x] 1.1 Confirm the backend needs no Fio-ness test: nothing server-side gates on it,
      and the endpoint cannot check a token against an account that may still be
      unsaved, so `accounts.py` stays untouched (design Decision 1)
- [x] 1.2 Add `verify(token) -> None` to the `FioClient` protocol and to
      `HttpFioClient` in `backend/app/bank.py`: a one-day `fetch` whose result is
      discarded, raising `FioTokenRejected` on an HTTP status from Fio, and
      `FioUnreachable` on a transport failure or a `409` rate-limit (design Decision 3)
- [x] 1.3 Tests in `backend/tests/test_bank.py`: a rejected token raises, a transport
      failure raises the other error, a `409` takes the unreachable path, and nothing
      is ingested by any of the three

## 2. Recording the token

- [x] 2.1 Remove `fio_token` from `TournamentUpdate` in `backend/app/schemas.py`, so
      the tournament PATCH is no longer a way to record one (design Decision 2)
- [x] 2.2 Add `PUT /api/tournaments/{slug}/fio-token` in
      `backend/app/routers/tournaments.py`: console access required, verify through the
      injected `FioClient`, refuse with `422 fio_token_rejected` storing nothing on a
      rejection, store and report `verified: false` when the bank is unreachable, and
      answer with `{configured, verified}` — never the token
- [x] 2.3 Add `DELETE` on the same path, clearing the token and answering the same model
- [x] 2.4 New `backend/tests/test_fio_token.py`: a rejected token is refused and stores
      nothing; a good token is stored and turns `fio_token_configured` true;
      verification ingests no transaction; an unreachable bank stores the token with
      `verified: false`; a `DELETE` removes it and withholds the poll action and the
      deposit mode again; a `PATCH` carrying `fio_token` is refused

## 3. Fio-ness in the console

- [x] 3.1 Add `isFioAccount(raw)` to the frontend beside the other account helpers:
      normalises case and whitespace, reads the bank code from an IBAN or from the
      Czech domestic form, compares against `2010`/`8330`, answers false for anything
      partial, and validates nothing (design Decision 1); comment names
      `backend/app/accounts.py` as the other copy
- [x] 3.2 Unit tests for it: both forms of the same Fio account, another bank in both
      forms, an empty value, a partial value, a Fio bank code on a failing checksum

## 4. The control and its form

- [x] 4.1 In `frontend/src/setup/BankAccountSection.tsx`, put the set / reset action on
      the account field's line, right-aligned, as an underlined text action; drive its
      availability from `isFioAccount(value)` on the typed value, and give the
      unavailable state the reason beside it in `--ink-faded` (design Decision 5)
- [x] 4.2 State in the section whether a token is recorded, from
      `detail.fio_token_configured`
- [x] 4.3 New `frontend/src/setup/FeedTokenDialog.tsx` on the `WaiverReasonDialog`
      pattern: an empty token field, the read-only-token advice, a removal control
      where one is recorded, its own `PUT` on submit and `DELETE` on removal, staying
      open and stating the refusal on a rejection, and inert on an empty submission
      (design Decision 4)
- [x] 4.4 Wire the dialog's success back into the section so
      `fio_token_configured` and everything gated on it — the intake poll action and
      the deposit mode — reflect the new state without a reload

## 5. Copy

- [x] 5.1 Add the action label, the not-a-Fio-account reason, the recorded/not-recorded
      statement, the dialog title, the read-only-token advice naming where in Fio
      internet banking it is made, the removal control, and the rejection and
      could-not-check messages to `frontend/src/i18n/en.json` and `cs.json`
- [x] 5.2 Check the new copy against the design prohibitions: no Title Case, no
      exclamation marks, no weight 600+, no emoji, one saturated color

## 6. Console tests

- [x] 6.1 Component tests for the section: the action is unavailable on an empty
      account, becomes available as a Fio account is typed without a save, states the
      reason on another bank, and nothing else on the page moves as it changes
- [x] 6.2 Component tests for the dialog: the field opens empty on a configured
      tournament, an empty submission writes nothing, a removal clears, and a
      rejection keeps the dialog open with the reason at the field

## 7. Close out

- [x] 7.1 Run `pytest backend/tests/test_fio_token.py backend/tests/test_bank.py -q
      --maxfail=3 --tb=short --show-capture=no` and the frontend test suite for the
      touched files
- [x] 7.2 Move every existing test that sets a token by `PATCH`ing the tournament onto
      the new endpoint against a stubbed `FioClient` — `test_bank.py`, `test_issuing.py`,
      `test_external_registration.py`, `test_payments_clear.py`, `test_manual_payments.py`,
      `test_payment_modes.py`, `test_payment_e2e.py`, `test_payments_off.py`,
      `test_discipline_amendment.py`, `test_rental_amendment.py`,
      `test_reservation_lifecycle.py` — and run the full backend suite once to catch any
      the grep missed
