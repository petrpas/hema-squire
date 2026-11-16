## 1. Tests

- [x] 1.1 `backend/tests/test_link_remainder.py`: remainder to the last registration, one-registration overpayment, link to nothing payable refused (fail on `main`).

## 2. Backend

- [x] 2.1 `apply_payment_links`: payable registrations first, last takes the remainder; a rule finding nothing payable or no accepted currency leaves the transaction untouched (design D1, D2).
- [x] 2.2 `link_transaction` and `confirm_proposal`: refuse `409 nothing_payable` / `currency_not_accepted` before writing the rule, through `matching.link_refusal` (design D2).

## 3. Frontend

- [x] 3.1 Map `nothing_payable` and `currency_not_accepted` to a Czech and English sentence in the link dialog, which stays open; any other 409 is still a concurrent match and closes it.

## 4. Checks

- [x] 4.1 Scoped pytest (`tests/test_link_remainder.py tests/test_manual_matching.py tests/test_matching.py`), `ruff check`, `basedpyright`, `npm run typecheck`, `npm run check`.
