## Context

`bank_account` is `Mapped[str | None] = mapped_column(String(50))` and serves two
roles that pull in opposite directions:

| role | consumer | wants |
| --- | --- | --- |
| encoded | `spayd.spayd_string(account_iban, ...)` via `emails.payment_spayd` | IBAN — `spayd.py` documents `ACC:` as IBAN-only |
| displayed | four email bodies (`{account}`), `PaymentInstructionsOut.iban`, the payment slip | the form the payer can actually use |

Validation is shared: `constraints.py:37` holds `BANK_ACCOUNT_PATTERN`, mirrored as
a literal in `frontend/src/constraints.ts` and compared by
`backend/tests/test_constraints_mirror.py`, which parses the TypeScript as text.
That mirror can carry a regex. It cannot carry an algorithm.

The Czech domestic format is `[prefix-]number/bankcode` — prefix 0–6 digits and
optional, number 2–10 digits, bank code exactly 4 digits. The CZ BBAN is
`bankcode(4) + prefix(6, zero-padded) + number(10, zero-padded)`, giving a 24-character
IBAN. The mapping is total and reversible in both directions, so no information is
lost by storing either one.

Constraints: `CLAUDE.md` / `openspec/squire-design-spec.md` are binding. The
frontend has no test runner; `npm run lint` is `tsc -b --noEmit`.

## Goals / Non-Goals

**Goals:**
- A Czech organizer can enter the account they know, without looking up an IBAN.
- A mistyped account is refused at the moment it is entered, not discovered by a
  fencer whose payment bounced.
- A Czech payer reads an account in the form their banking app asks for.
- Consumers of `bank_account` continue to see exactly one format.

**Non-Goals:**
- No other country's domestic format. A Slovak or German account is entered as an
  IBAN, as today.
- No change to SPAYD encoding, QR generation, matching, or pricing.
- No second stored column, no migration.
- No BIC/SWIFT field.

## Decisions

### Decision 1 — The column keeps holding a canonical IBAN

Entered Czech accounts are converted on save; entered IBANs are stored as given
(whitespace stripped, uppercased). Chosen by the owner on 2026-08-03 over storing
the input verbatim or keeping two columns.

This is the option that changes least: `spayd.py` needs no edit, every existing
stored value is already canonical, there is no migration, and no invariant is
created between two columns that could disagree. The display form is **derived**,
which is the repo's standing preference — `openspec/project.md` makes totals a pure
function of inputs, and the same argument applies to a second rendering of one
stored fact.

*Alternative considered*: storing the organizer's input verbatim and converting on
each SPAYD build. Rejected — it pushes format-awareness into `emails.py`,
`registrations.py` and anything else that later reads the field, to preserve a
rendering that is recoverable anyway.

### Decision 2 — Display derives the domestic form from the IBAN's country

A stored IBAN beginning `CZ` is shown as `domestic (IBAN)`; any other IBAN is shown
as itself. Nothing records which form the organizer typed, because nothing needs
to: a Czech account has a domestic form worth showing whether or not it was entered
that way, and a foreign one has none to show.

The four email bodies interpolate a single `{account}` placeholder, in both `cs`
and `en`. So this is a change to what `emails.py` passes and **no locale template
changes at all**. The payment slip gains one line; `PaymentInstructionsOut` gains
the domestic string as its own field so the frontend does not parse the IBAN.

*Consequence*: `payment.iban` in `i18n` currently reads "Account (IBAN)" and would
be lying next to a domestic number. It becomes a neutral "Account" label with the
IBAN on its own line.

### Decision 3 — Checksums are validated, in the backend only

Owner-decided on 2026-08-03, both parts. Two checks:

- **IBAN**: ISO 7064 mod-97-10. Move the first four characters to the end, map
  letters to numbers (`A`=10 … `Z`=35), and require the integer mod 97 == 1.
- **Czech account**: the ČNB weighted mod-11, applied **separately** to the prefix
  and to the account number, weights `1,2,4,8,5,10,9,7,3,6` from the rightmost
  digit; each weighted sum must be divisible by 11.

Both are mandated for real accounts, so validation rejects only typos and
fabrications. The bank code is checked for shape (four digits) but **not** against
a registry of live ČNB codes — a static list would rot, and the mod-11 already
catches the overwhelmingly common error of a mistyped account number.

They run in the backend, as a pydantic validator on `TournamentUpdate.bank_account`
that also performs the normalization from Decision 1. The frontend does not
duplicate them. `test_constraints_mirror.py` compares literals, so it could never
prove that a hand-written mod-97 in TypeScript agrees with the Python one; not
duplicating the algorithm means there is nothing to drift. The shared pattern still
gives instant feedback on shape, which is the class of error a user makes while
typing; a checksum error appears on save as a field error like any other server-side
rejection.

### Decision 4 — One module owns both formats

New `backend/app/accounts.py`, the only place that knows either format exists:

```
parse(raw)            -> Iban            accepts either form, raises on invalid
to_iban(domestic)     -> str             CZ domestic -> IBAN, computing check digits
to_domestic(iban)     -> str | None      CZ IBAN -> domestic; None for any other country
display(iban)         -> str             "19-2000145399/0800 (CZ6508000000192000145399)"
                                          or the IBAN alone when not Czech
```

`schemas.py` calls `parse`; `emails.py` and `routers/registrations.py` call
`to_domestic` / `display`. No consumer learns a second format, which is the
property that keeps this change from spreading.

### Decision 5 — The shared pattern widens to a union of two shapes

```
^([A-Z]{2}[0-9]{2}[A-Za-z0-9]{10,30}|[0-9]{1,6}-?[0-9]{2,10}/[0-9]{4})$
```

It stays a single literal in `constraints.py`, mirrored verbatim into
`constraints.ts`, so `test_constraints_mirror.py` keeps working unchanged. The
pattern is deliberately looser than the validator — it admits a shape the checksum
will later reject — because its job is to catch "this is not an account at all"
while the user types, not to be the authority.

*Note*: `TOURNAMENT_BANK_ACCOUNT_MAX_LENGTH = 50` and the `String(50)` column stay
as they are. A CZ IBAN is 24 characters and the longest domestic form is 22
(`6 + 1 + 10 + 1 + 4`), both well inside it, and the column only ever stores the
IBAN.

## Risks / Trade-offs

- **A checksum error is only seen on save** → Decision 3, argued there. Mitigated
  by the Setup field's hint stating both accepted forms, and by the error naming
  which check failed rather than saying "invalid".
- **An organizer who entered a CZ IBAN now sees a domestic form they did not type**
  → Intended (Decision 2): it is the same account, in the form their payers use.
  Both forms are shown together, so nothing is hidden.
- **A published tournament's stored account is not re-validated** → This change
  validates on write. Accounts stored before it may fail the new checksum and are
  left alone; the publish gate from `fix-payment-instructions-visibility` only
  requires presence. Re-validating existing rows is deliberately not attempted —
  it would refuse saves on tournaments whose payments are demonstrably working.
- **Widening a pattern that guards a mandatory publication field** → The pattern
  only widens, so nothing that was accepted becomes rejected; the checksum is the
  only new refusal, and it applies to values that could not have worked anyway.

## Migration Plan

No schema change, no migration, no backfill. Existing values are IBANs and stay
valid. The only persistent behaviour change is that new saves accept a second input
format and refuse an account failing its checksum. Rolling back is narrowing the
pattern in both mirrored files and dropping the validator; stored values remain
readable, since everything stored is still an IBAN.
