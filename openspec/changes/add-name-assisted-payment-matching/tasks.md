## 1. Backend: extracting who a payment is for

- [ ] 1.1 Add the named-person field to the parsed statement row in `backend/app/bank.py`, alongside `payer_name` and `message` — what the payer's own text says this payment is for, taken from the message and the other text-bearing fields, never from the payer name or account
- [ ] 1.2 Extend `_STATEMENT_SYSTEM_PROMPT` for it: report the person the payment is *for*; where the text names nobody, report nothing rather than falling back to the payer — the fallback is the resolver's decision to make, not the model's, so that it can be weighted
- [ ] 1.3 Carry the field through `statements.py` and the stored `statement_row` decision, so re-import reuses it and no separate call is ever made
- [ ] 1.4 Carry it onto `BankTransaction` at ingest, so resolution does not re-read the statement
- [ ] 1.5 Tests with a fake parser: the field is stored and reused on re-import; a row naming nobody stores nothing; a Fio export (which has a real VS column) is unaffected

## 2. Backend: ranking the roster

- [ ] 2.1 New module for normalisation and scoring, with no LLM dependency and no database access — take a query string and a list of names, return them ranked
- [ ] 2.2 Normalisation: fold diacritics, lowercase, split on non-alphanumerics, so `Guenther`/`Günther`, `Kolodziej`/`Kołodziej` and `MAZANEC MATEJ`/`Matěj Mazanec` compare equal
- [ ] 2.3 Scoring insensitive to name order, and tolerant of a missing space (`JosefVochozka`) and a surname alone (`Jakubec`, `CHEREAU`)
- [ ] 2.4 Rank every fencer, always — a query matching nobody still returns the roster in a defined order
- [ ] 2.5 Named constants for the score minimum and the margin minimum, starting at the values the pilot run suggested, documented as tunable rather than fixed
- [ ] 2.6 Tests as a table of real cases from the pilot statement: every pairing in section 6.3, plus the two that must NOT be clear winners — a payment naming a surname two fencers share, and the duplicate pair
- [ ] 2.7 Property or fuzz test: ranking never raises and never returns fewer names than it was given

## 3. Backend: resolution and the `likely` state

- [ ] 3.1 Add `likely` to the transaction statuses and a reference to the fencer proposed, with an Alembic migration; record a rejected pairing so it is not proposed again
- [ ] 3.2 At `matching.py:344` — the `no_vs` branch — consult the resolver instead of finishing as `unmatched` outright. Nothing before that branch changes
- [ ] 3.3 Query from the extracted named person; where there is none, fall back to the payment's text, and mark the resolution ineligible to be a clear winner when the fallback used the payer name
- [ ] 3.4 Propose only on a clear single winner: score above the minimum AND margin above the minimum, both required
- [ ] 3.5 Never propose a pairing already rejected, and never propose where the roster has no registration to credit
- [ ] 3.6 **Tests that the proposal moves nothing**: after resolution, assert the registration's `amount_paid_cents`, `outstanding_cents` and `state` are unchanged and the collecting mailer is empty. Assert this, not the status string — a broken implementation gets the status right
- [ ] 3.7 Tests for the ambiguity rules: two fencers scoring alike are not proposed however high the score; a best score below the minimum is not proposed; a payer-name fallback is not proposed
- [ ] 3.8 Test the pilot's own shape: three payments from one payer naming three different fencers resolve to three different fencers, and none resolves to the payer

## 4. Backend: confirm and reject

- [ ] 4.1 Confirm endpoint: credit through the existing manual-link path so a confirmed proposal is indistinguishable afterwards from a hand-linked payment — same `payment_link` rule, same tolerance, same currency and part-payment behaviour, same survival across reruns
- [ ] 4.2 Reject endpoint: return the payment to unresolved and record the refused pairing
- [ ] 4.3 Endpoint listing the ranked roster for one transaction, for the dialog
- [ ] 4.4 Tests: confirming credits exactly as a VS-quoting payment would, including sending what a credit sends; rejecting returns it and does not re-propose; both refuse without console access

## 5. Frontend: the proposals queue

- [ ] 5.1 New queue card in `frontend/src/payments/`, following `QueueCard` and taking the console's `reload` signal like its four neighbours
- [ ] 5.2 Each entry states the bank's own text — date, amount, message, payer — beside the proposed fencer and what they owe, so the confirmation is made on evidence
- [ ] 5.3 Confirm and reject in place, refreshing the queues and the sheet
- [ ] 5.4 Empty queue collapses to a heading, as the others do
- [ ] 5.5 `api.ts` for the new endpoints; Czech and English strings
- [ ] 5.6 Tests: an entry renders the evidence and both actions; confirming and rejecting call the right endpoint and refresh; the empty state collapses

## 6. Frontend: the link dialog

- [ ] 6.1 `LinkDialog.tsx` gains the ranked roster with the strongest marked, keeping the detected VS candidates and the typed-VS input it already has
- [ ] 6.2 Type-to-filter lookup over the whole roster, following the HEMA Ratings search dialog
- [ ] 6.3 Selecting several fencers still links one payment to several registrations
- [ ] 6.4 Tests: the roster renders ranked; typing filters it; a typed VS still resolves; multi-selection still links to each

## 7. Verification

- [ ] 7.1 `cd backend && uv run pytest` and `ruff check .`
- [ ] 7.2 `cd frontend && npx vitest run`, `npm run build`
- [ ] 7.3 Against the pilot's own 43 transactions, after `issue-imported-registrations` has run: confirm roughly 35 proposals and 8 unresolved, that the three Milan Diviš payments name three different fencers, and that no proposal has moved money before anyone confirmed anything
- [ ] 7.4 Confirm a proposal and check the credit, the balance and the mail match what a VS-quoting payment produces
- [ ] 7.5 Reject a proposal and check it returns to unresolved and is not proposed again
