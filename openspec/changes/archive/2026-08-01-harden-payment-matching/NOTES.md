## Open issue: Group 10 (Frontend) needs replanning

Discovered while applying this change (2026-08-01). Backend groups 2–9, 11,
and most of 12 are implemented and merged into the working tree; Group 10 was
not attempted beyond this note, because the task list's premises about the
frontend turned out to be wrong.

### What tasks.md assumes

Tasks 10.1–10.4 say to edit `MatchDialog.tsx` and `MatchPanel.tsx`: pre-fill
candidate VS in the dialog, show credited/outstanding balance in the panel,
list reservations that expired holding a payment, and mark auto-created
payment links in "the rules view."

### What's actually there

`MatchDialog.tsx` and `MatchPanel.tsx` belong to a **different feature**: HR
(hemaratings.com) fighter-identity matching — resolving a fencer's name
against the ratings index. `MatchPanel.tsx` triggers a matching run and
refreshes the HR index; `MatchDialog.tsx` searches HR profiles by name. Same
word ("matching"), unrelated domain. Editing these for payment-transaction
purposes would be wrong.

The actual bank-transaction console UI is `PaymentsPanel.tsx`
(`frontend/src/PaymentsPanel.tsx`). It renders **only** the `flagged` subset
of transactions (reinstate / mark-for-refund actions). Beyond that:

- **No manual-link dialog exists.** `POST /payments/link` (the manual VS-link
  endpoint) has no frontend caller anywhere. Task 10.1's "candidate pre-fill"
  has nothing to pre-fill into.
- **No reserved-registrations table with a balance column exists.** Task
  10.2 assumes one to add `outstanding_amount` to.
- **No expired-registrations list exists at all**, holding-payment or
  otherwise. Task 10.3 assumes a place to add a second list next to it.
- **No rules view exists** in the frontend. Task 10.4 assumes one to mark
  auto-created links in.

So Group 10 isn't "edit four call sites" — it's designing and building new
console UI surface: a manual-link dialog, an unmatched/candidate queue view
(distinct from the flagged-only `PaymentsPanel.tsx`), a reserved-with-balance
list, an expired/holding-payment list, and a rules list. That's a real scope
increase the original proposal/design didn't size or lay out.

### What the backend already provides for this UI

- `GET /api/tournaments/{slug}/payments/unmatched` and `/transactions` return
  `TransactionOut` with `candidate_vs: list[int]` (pre-filled VS candidates,
  computed from `matching.detect_candidates`) and `last_evaluated_at`.
- `GET /api/tournaments/{slug}/my-registration` (and presumably an
  organizer-facing registrations list, if one exists/gets built) exposes
  `outstanding_amount` / `outstanding_eur_amount` per registration.
- `PaymentEvent.kind == "expired_holding_payment"` distinguishes a
  holding-payment expiry from an ordinary one (`reservation_expired`);
  nothing currently queries this for display.
- `GET /api/tournaments/{slug}/rules?phase=payments` returns `payment_link`
  rules; auto-created ones carry `payload["auto_created"] == True`.
- `POST /payments/link` (existing endpoint, `LinkIn` schema) is what a new
  manual-link dialog would call.

### Suggested next step

Replan Group 10 as its own scoped piece of work — probably worth a short
`/opsx:explore` or `/opsx:propose` pass to decide: does the flagged-only
`PaymentsPanel.tsx` grow to cover unmatched/candidates/reserved-balance/
expired-holding-payment too, or do these become separate panels? Is a
manual-link dialog a modal like the existing HR `MatchDialog.tsx` pattern, or
inline in the table? Worth deciding with the actual console layout in view
rather than guessing blind.
