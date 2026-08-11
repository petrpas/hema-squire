## Why

A fencer registers, holds a reservation with an expiry clock running, and is shown
no payment instructions and no explanation. The instructions themselves are not
missing — `TournamentDetail.tsx:29` has a complete `PaymentPanel` with QR, amount,
IBAN, VS and expiry. It is reached only when the fetch succeeds:

```tsx
api.paymentInstructions(slug).then(setPayment, () => setPayment(null));
...
if (!payment) return null;
```

Every refusal collapses to `null`, and `null` renders nothing. Three defects sit
behind that silence.

**1. A tournament can be published with no bank account.** `GET
/my-registration/payment` refuses with `404 no_bank_account` when
`tournament.bank_account` is unset (`registrations.py:696`), and `bank_account` is
settable in exactly one place — `ParamPanel`, phase `payments`, a rail card inside
the **Console**. Setup's own `PAYMENTS` tab (`SetupPanel.tsx:113-120`: currency,
VS series, discounts) does not carry it. An organizer completes Setup, publishes,
and opens registration without ever meeting the field that makes payment possible.
`setup_missing()` — the single source of truth for publication readiness — does
not check it.

**2. The frontend and backend disagree about when payment is due.** The frontend
predicate ignores team disciplines entirely:

```
frontend  TournamentDetail.tsx:269   active.length === 0 && substitutes.length > 0
backend   registrations.py:692-694   all(e.is_substitute for e in entries)
                                     and all(t.waitlisted for t in teams)
```

It diverges in both directions. A **team-only registration whose teams are all
waitlisted** renders the panel and receives `409 no_payment_due` — another silent
blank. A registration whose **entries are all queued but whose teams are active**
is told everything is queued and shown no payment slip, while money is genuinely
owed on the teams. The backend comment at `registrations.py:688-691` states the
correct rule; the frontend predicate predates `add-team-disciplines`.

**3. No refusal has a fencer-facing message.** `registration/spec.md:404`
("In-app payment instructions retrieval") has four scenarios, all happy-path or
authorization. There is no requirement for what the fencer sees when instructions
cannot be produced, which is why a silent `return null` reads as compliant.

## What Changes

- **`bank_account` becomes a mandatory Setup item.** `setup.py` gains
  `MISSING_BANK_ACCOUNT` and its check in `setup_missing()`. Publication is
  refused without it, the PUBLISH tab lists it as outstanding, and
  `guard_published_completeness` stops a published tournament having it cleared —
  all three fall out of the existing mechanism, with no new gate logic.
- **New `setup/BankAccountSection.tsx` on the existing `PAYMENTS` tab**, alongside
  currency, VS series and discounts — the money settings the organizer already
  expects to find together. Operational parameters (tolerance, grace hours,
  reminder day, validity days) stay in the console rail where they are tuned
  during reconciliation.
- **`PaymentPanel` renders every refusal** instead of vanishing: a distinct
  message per reason, and the reason is read from `ApiError.detail`, which
  `api.ts` already carries.
- **The frontend "nothing is due" predicate is corrected** to the backend's rule,
  covering teams as well as entries, so the panel and the "all queued" hint each
  appear exactly when the backend agrees.
- **Existing published tournaments with no bank account** are reported by a
  one-shot check rather than silently left broken; they cannot be repaired by the
  publish gate, which only guards future transitions.
- Czech and English strings for the new section and the refusal messages.

Not in scope: any change to how instructions are computed, to SPAYD/QR
generation, to the deposit concept (unmodelled today), or to the payments console
surfaces covered by `add-payments-console-ui`.

## Capabilities

### Modified Capabilities
- `registration`: the in-app payment instructions requirement gains the failure
  cases it never covered, and the "nothing is due" rule is stated once so the two
  ends cannot drift apart again.
- `tournament-admin`: the mandatory-setup set gains the bank account.
- `setup-navigation`: the `PAYMENTS` tab's section allocation gains it.

## Impact

**Backend** (`backend/app/`): `setup.py` (`MISSING_BANK_ACCOUNT` + check);
`tests/` for the new completeness item and the publish refusal. No model,
migration, or endpoint change — `my_registration_payment` already refuses
correctly and keeps its current shape.

**Frontend** (`frontend/src/`): `TournamentDetail.tsx` (`PaymentPanel` error
states, corrected "nothing is due" handling); new
`setup/BankAccountSection.tsx`; `SetupPanel.tsx` (render it on the `PAYMENTS`
tab); `ParamPanel.tsx` (drop `bank_account` from the payments phase);
`i18n/{en,cs}.json`.

**Design constraints**: `CLAUDE.md` / `openspec/squire-design-spec.md` are binding
— the refusal messages are static text in existing classes (`.rail-hint`,
`.login-error`), no new colour, no icon, no animation.

**Verification**: backend tests cover the completeness item and the publish
refusal. The frontend has no test runner (`npm run lint` is `tsc -b --noEmit`), so
the panel states are verified by typecheck, build, and driving a registration
through each refusal.
