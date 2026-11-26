## Why

A payment that arrives on an expired reservation outside the grace period is
flagged, not credited, and lands in Payments → Nepřipsané with the reinstate and
refund actions on it. Nothing else points at it. The registration's own row in
Payments → Registrace reads a plain "Vypršela", the default tab is Připsané, and
the queue (where an organizer naturally looks for the team) offers nothing on a
lapsed row by design. The owner, who wrote the console, could not find it when a
colleague's late team payment arrived (2026-11-26); an ordinary organizer will
not either, while the fencer has been told "the organizer will follow up".

## What Changes

- On the Payments phase's registration table, an **expired** registration that
  has money against it carries, in its state cell, a stamp of the paid stamp's
  shape drawn in a muted ink rather than `--stamp`, reading **"Pozdě" / "Too
  late"**. Two cases:
  - an uncredited payment flagged because the reservation had expired
    (`expired_outside_grace`, `expired_seat_taken`);
  - credit the expired registration still holds (today's "Vypršela s platbou").
- The stamp never reads "Zaplaceno": the lifecycle still wins over the money.
- Its tooltip states that the reservation lapsed and what money stands against
  it, with the amount and the day.
- Pressing the stamp opens the money table that payment sits in — Nepřipsané
  for a flagged payment, Připsané for held credit — scrolls to that payment's
  row and marks it.
- Not in scope, by owner decision: a cancelled registration with a late payment
  (the sheet does not draw cancelled registrations and its one action, refund,
  is already on its Nepřipsané row); any mail to the organizer; any action in
  Fronta or Týmy. A future Agenda tab is where such work will be listed.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `payments-console`: a new requirement — an expired registration holding money
  is marked late on the registration table and leads to its payment.

## Impact

- `backend/app/sheet.py`: the row of an expired registration states the late
  payment that stands against it and where it lies (one read of flagged
  transactions per projection, not per row).
- `backend/app/schemas.py`, `frontend/src/api.ts`: the row fields.
- `frontend/src/StateCell.tsx` / `StateBadge` in `Console.tsx`, `PaidStamp.tsx`,
  `index.css`: the muted stamp and its button.
- `frontend/src/Console.tsx`, `payments/UncreditedTable.tsx`,
  `payments/CreditedTable.tsx`: opening a tab on a named payment and marking its
  row.
- `frontend/src/i18n/{cs,en}.json`: label and tooltips.
- No migration, no new endpoint, no mail.
