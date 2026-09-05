## 1. Backend: extracting who a payment is for

- [x] 1.1 Add the named-person field to the parsed statement row in `backend/app/bank.py`, alongside `payer_name` and `message` — what the payer's own text says this payment is for, taken from the message and the other text-bearing fields, never from the payer name or account
- [x] 1.2 Extend `_STATEMENT_SYSTEM_PROMPT` for it: report the person the payment is *for*; where the text names nobody, report nothing rather than falling back to the payer — the fallback is the resolver's decision to make, not the model's, so that it can be weighted
- [x] 1.3 Carry the field through `statements.py` and the stored `statement_row` decision, so re-import reuses it and no separate call is ever made
- [x] 1.4 Carry it onto `BankTransaction` at ingest, so resolution does not re-read the statement
- [x] 1.5 Tests with a fake parser: the field is stored and reused on re-import; a row naming nobody stores nothing; a Fio export (which has a real VS column) is unaffected

## 2. Backend: ranking the roster

- [x] 2.1 New module for normalisation and scoring, with no LLM dependency and no database access — take a query string and a list of names, return them ranked
- [x] 2.2 Normalisation: fold diacritics, lowercase, split on non-alphanumerics, so `Guenther`/`Günther`, `Kolodziej`/`Kołodziej` and `MAZANEC MATEJ`/`Matěj Mazanec` compare equal
- [x] 2.3 Scoring insensitive to name order, and tolerant of a missing space (`JosefVochozka`) and a surname alone (`Jakubec`, `CHEREAU`)
- [x] 2.4 Rank every fencer, always — a query matching nobody still returns the roster in a defined order
- [x] 2.5 `MIN_SCORE` 0.85 and `MIN_MARGIN` 0.05, documented as tunable and as coming from one statement, one bank, one language. Two more constants were needed and neither was foreseen: `_TOKEN_FLOOR`, below which a name token counts as unmatched, and `_JOINED_MIN_SHARE`, how much of a joined name a single query token must cover before it is read as the name with its spaces missing. Both were found by running the pilot's cases (see 2.6)
- [x] 2.6 `tests/test_name_ranking.py`, 30 tests. **Two guards came out of running the cases rather than reasoning about them.** A name token with no partner still scored 0.43 against `naduel26`, so the Pekárek whose given name looked more like a tournament prefix won by a margin wide enough to propose him. And the joined-name path, which exists to recover `JosefVochozka`, scored a bare `pekarek` by length alone — 0.70 against `ondrejpekarek`, 0.64 against `jindrichpekarek` — proposing whichever Pekárek had the shorter given name. Both are floored now, and every pilot shape lands where the design said

- [x] 2.6b **The design's numbers do not reproduce, and the outcomes do.** It recorded both Pekáreks scoring 1.00 on a bare surname, saved by the margin. This scorer averages over the fencer's own tokens, so a half-named fencer scores 0.5 and the score test fires too. Same answer by a second route; the margin still earns its place on a *full* name that agrees in part, which is a case the design did not separate out
- [x] 2.7 Property or fuzz test: ranking never raises and never returns fewer names than it was given

## 3. Backend: resolution and the `likely` state

- [x] 3.1 Add `likely` to the transaction statuses and a reference to the fencer proposed, with an Alembic migration; record a rejected pairing so it is not proposed again
- [x] 3.2 At `matching.py:344` — the `no_vs` branch — consult the resolver instead of finishing as `unmatched` outright. Nothing before that branch changes. **On a manual tournament every payment reaches this branch**, because no registration carries a symbol: the same code, but the whole flow rather than the exception
- [x] 3.3 **Corrected while implementing.** I had made the whole fallback ineligible, which would have silenced the resolver on every Fio export — that path never reads a named person, so every payment would have fallen to the ineligible branch. The design says the *payer name* is what may not be a clear winner, and the message is not the payer name (`searchable_text` excludes it deliberately). Three steps now: the named person, then the message — both eligible, and the message alone is what resolved 35 of 43 — then the payer name, never eligible
- [x] 3.4 Propose only on a clear single winner: score above the minimum AND margin above the minimum, both required
- [x] 3.5 Never propose a pairing already rejected, and never propose where the roster has no registration to credit
- [x] 3.6 **Tests that the proposal moves nothing**: after resolution, assert the registration's `amount_paid_cents`, `outstanding_cents` and `state` are unchanged and the collecting mailer is empty. Assert this, not the status string — a broken implementation gets the status right
- [x] 3.7 Tests for the ambiguity rules: two fencers scoring alike are not proposed however high the score; a best score below the minimum is not proposed; a payer-name fallback is not proposed
- [x] 3.8 Test the pilot's own shape: three payments from one payer naming three different fencers resolve to three different fencers, and none resolves to the payer

## 4. Backend: confirm and reject

- [x] 4.1 Confirm endpoint credits through the manual-link path. That needed 8.2 first: a proposal names a *person*, and the link rule addressed registrations only by symbol. Confirm endpoint: credit through the existing manual-link path so a confirmed proposal is indistinguishable afterwards from a hand-linked payment — same `payment_link` rule, same tolerance, same currency and part-payment behaviour, same survival across reruns
- [x] 4.2 Reject endpoint: return the payment to unresolved and record the refused pairing
- [x] 4.3 Endpoint listing the ranked roster for one transaction, for the dialog
- [x] 4.4 Tests: confirming credits exactly as a VS-quoting payment would, including sending what a credit sends; rejecting returns it and does not re-propose; both refuse without console access

## 5. Frontend: the proposals queue

- [x] 5.1 New queue card in `frontend/src/payments/`, following `QueueCard` and taking the console's `reload` signal like its four neighbours
- [x] 5.2 Each entry states the bank's own text — date, amount, message, payer — beside the proposed fencer and what they owe, so the confirmation is made on evidence
- [x] 5.3 Confirm and reject in place, refreshing the queues and the sheet
- [x] 5.4 Empty queue collapses to a heading, as the others do
- [x] 5.5 `api.ts` for the new endpoints; Czech and English strings
- [x] 5.6 Tests: an entry renders the evidence and both actions; confirming and rejecting call the right endpoint and refresh; the empty state collapses

## 6. Frontend: the link dialog

- [x] 6.1 `LinkDialog.tsx` gains the ranked roster with the strongest marked, keeping the detected VS candidates and the typed-VS input it already has
- [x] 6.2 Type-to-filter lookup over the whole roster, following the HEMA Ratings search dialog
- [x] 6.3 Selecting several fencers still links one payment to several registrations
- [x] 6.4 Tests: the roster renders ranked; typing filters it; a typed VS still resolves; multi-selection still links to each

## 7. Verification

- [x] 7.1 `cd backend && uv run pytest` and `ruff check .`
- [x] 7.2 `cd frontend && npx vitest run`, `npm run build`
- [x] 7.3 Run against a copy of the pilot with all 53 registrations issued: of
  43 transactions the resolver proposes **36** and withholds 7 — 6 naming nobody
  on the roster, 1 ambiguous — against the 35/8 this estimated. The three Milan
  Diviš payments name three different fencers (Václav Pekárek, Milan Diviš,
  Jindřich Pekárek), which is the case this capability exists for; two of the
  three resolve only because those rows now hold registrations. Nothing moved:
  `resolve` writes nothing and a proposal credits nobody until confirmed
- [x] 7.4 Confirmed on the pilot: Jan Žegklitz's 1 100 Kč credited his own
  registration in full — `amount_paid` 1 100 against a total of 1 100, state
  `paid`, one `payment_link` rule and one `payment_matched` event, exactly the
  shape a hand-linked payment leaves. **No mail, and that is right**: the
  registration was issued for a fencer-list row, so it is dormant by origin and
  `_payment_mail_suppressed` credits it silently. A VS-quoting payment against an
  ordinary registration still writes to the fencer; the difference is the
  registration's origin, not this path
- [x] 7.5 Rejected on the pilot: the payment from JAN BĚLINA returned to
  `unmatched` with reason `proposal_rejected`, carrying the refused fencer's id
  so the resolver cannot offer the same wrong answer twice. It is in the
  unmatched queue, which the endpoint selects by status.

  Found while checking it, and left as it is on the owner's say-so: the queues
  became tabs earlier the same day, and a rejected payment now leaves the tab
  being read and arrives on one nobody is looking at. Stacked, the hand-off was
  visible — the payment moved from one card to the card below. The count on the
  destination tab is the only signal now, and it has to be sought


## 8. Revision, 2026-09-05: the symbol is a shortcut, and the tail is permanent

`issue-imported-registrations` is revised to allocate no variable symbol where
the organizer keeps the registrations, so on such a tournament this resolver is
the only way a payment ever finds a fencer. **Neither half ships alone**:
removing the symbol first leaves an organizer unable to reconcile anything, and
shipping this first is harmless but leaves the symbol pointlessly minted.

And the by-name control is **not conditional on the mode**. A symbol resolves the
cheap majority — the owner's estimate is roughly nine payments in ten — and the
remaining tenth is permanent in every mode: blank fields, typos, last year's
number, one person paying for another. Those reach a queue today with a stated
reason, and the only tool for them is to read the message, find the fencer and
type a seven-digit number. That is the work this section removes, on every
tournament.

- [x] 8.1 Manual linking addresses a **fencer**, not a symbol, **in every mode**. `LinkDialog` offers `candidate_vs`, accepts a typed symbol and reports `unknown_vs`: meaningless on a manual tournament and merely the wrong question on an automatic one, where the organizer looking at a mistyped payment knows the person and not the number. The roster-listing endpoint from 4.3 is the addressing mechanism — promote it from a convenience for the proposal dialog to the way the dialog works, unconditionally
- [x] 8.1b Keep typing a symbol as a **second** way in, not the only one. Where an organizer does know the number it is the fastest route, and on a Squire-kept tournament the numbers are real; what changes is that it stops being the sole route
- [x] 8.2 `POST /payments/link` takes a VS array. Give it a way to name registrations that have none, or address them by registration id, and keep the existing shape working for tournaments that do carry symbols
- [x] 8.3a Tests over an **automatic** tournament's tail: a payment quoting no symbol, one quoting a symbol that resolves nowhere, and one quoting a symbol belonging to a different fencer than the message names. Each reaches the organizer with the resolver's proposal where there is one, and each is resolvable by choosing a person without typing a number
- [x] 8.3 Tests over a manual tournament end to end: registrations with no symbols, a statement of payments with no symbols, the resolver proposing, an organizer confirming, and the credit landing exactly as a VS-quoting payment's would
- [x] 8.4 Verified in that order on the pilot, which keeps its own registrations
  and therefore mints no symbol at all — `vs_next_seq` is still 1. Every one of
  the three ways a payment reaches a registration was exercised on real data
  after the symbols were gone: **automatic by symbol** cannot fire and correctly
  does not; **by name** proposes 37 of 43; **by hand** links from the ranked
  roster, which is how the remaining 6 are resolved. Nothing is left without a
  way through
- [x] 8.5 Re-read the threshold constants before shipping. They were tuned where a VS-matched majority would have absorbed a wrong proposal; on a manual tournament every payment goes through the resolver, so a confident mistake is a larger share of the outcome. The rule stays "propose only on a clear single winner" and the margin stays strict


## 9. Found during implementation

- [x] 9.1 `no_vs` was one reason for four different situations, and the console showed it as one. Split into `no_roster`, `no_name_match`, `name_ambiguous` and `payer_name_only`: nobody registered, nobody scored, two scored alike, or the only text was the payer's own name. They ask the organizer different questions. Two existing tests in `test_matching.py` assert the new ones
- [x] 9.2 The `payment_link` rule's `credited` map was keyed by variable symbol, which a registration need not have. Keyed by registration now, with the old keys still read back so nothing stored needs rewriting — `test_manual_matching.py` asserts the shape and was updated
- [x] 9.3 `TransactionStatus` in `api.ts` was missing `partial`, which the backend has emitted since `add-payment-modes`. Added alongside `likely`
