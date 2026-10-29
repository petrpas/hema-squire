## 1. The holder is stored

- [ ] 1.1 `backend/app/models.py`: `Tournament.bank_account_holder` (nullable `String(70)`); alembic migration
- [ ] 1.2 `backend/app/schemas.py`: the field in `TournamentUpdate` (bounded string type in `fieldtypes`/`constraints`, 70) and `TournamentOut`
- [ ] 1.3 `backend/app/setup.py`: completeness names the holder as missing when payments are on, the tournament charges, and it takes EUR (EUR-only or local + EUR) (D4)
- [ ] 1.4 Tests: CZK + EUR with payments on and no holder is incomplete; CZK-only is not; payments off is not

## 2. EUR codes are EPC codes

- [ ] 2.1 EPC builder (D2) beside `spayd_string`, with newline/length sanitizing; unit test fixing the exact payload for a reference case, the 140-character cut keeping the labelled VS, and the ≤331-byte bound at maximum lengths
- [ ] 2.2 `emails.py`: `payment_code` chooses the format by currency (D1); `payment_spayd` → `payment_codes`; EUR without a holder yields no code; all callers (`payment_qrs`, `_qr_pair`, `routers/registrations.py`) follow
- [ ] 2.3 Mail text: where the EUR code is absent, the EUR amount, IBAN and VS still appear in text, and no attachment is named for it
- [ ] 2.4 Tests: a CZK + EUR confirmation carries SPAYD `CC:CZK` and an EPC EUR code; a EUR-only tournament's code is EPC; a missing holder drops only the EUR code; the payment-data endpoint matches the mail
- [ ] 2.5 Matching test: a SEPA transaction whose message is the EPC remittance text matches by its labelled VS

## 3. Setup

- [ ] 3.1 `routers/tournaments.py` suggestions: `bank_account_holders` and `holder_by_account` (D3), scoped like the rest
- [ ] 3.2 `frontend/src/setup/BankAccountSection.tsx`: holder field below the account, same save, `HelpHint` saying a EUR payment code must name the holder and foreign banks refuse one without it; recalled holders; picking a recalled account fills an empty holder
- [ ] 3.3 `PUBLISH` names the missing holder; `cs`/`en` locale keys
- [ ] 3.4 Frontend tests: the field sits below the account; picking a recalled account fills an empty holder and leaves a typed one
- [ ] 3.5 `npm run typecheck`, `npm run check`; `uv run ruff check .`, `uv run basedpyright`; scoped pytest
- [ ] 3.6 After deploy: scan the EUR code from a foreign banking app (or a GiroCode reader) and record the result here
