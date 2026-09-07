## Context

The backend half of this feature has been in place for some time. `Tournament.fio_token`
(`models.py:425`) stores the token; `TournamentUpdate.fio_token` (`schemas.py:452`)
accepts it; `TournamentDetail` returns only the derived `fio_token_configured` boolean
(`schemas.py:576`), so the token has never left the server. `HttpFioClient.fetch`
(`bank.py:371`) reads a period of transactions; the poll endpoint
(`routers/payments.py:194`) refuses with `fio_token_not_configured` when there is none,
and the nightly sweep (`scheduler.py:362`) polls the last fourteen days for every
tournament that has one. The console already reads the boolean in two places:
`IntakePanel.tsx:147` withholds the poll action, and `PaymentModeSection.tsx:197`
withholds the deposit mode.

What is missing is the field. Every one of the fourteen tests that needs a token sets it
by a raw `PATCH /api/tournaments/{slug}`, because no organizer-facing control exists.

Two existing pieces shape the design. `accounts.py` canonicalises both accepted account
forms — an IBAN, or the Czech domestic `19-2000145399/0800` — into a stored IBAN whose
bank code is always characters 4–8, and the frontend today does no account parsing at
all: it posts the raw string and lets the backend canonicalise. And `update_tournament`
(`routers/tournaments.py:533`) accepts `fio_token` today as one field among forty, with
no verification and no way to say anything about it in its reply.

## Goals / Non-Goals

**Goals:**

- An organizer can record, replace and remove a Fio feed token from Setup.
- The control appears only where it means something, and says why when it does not.
- A mistyped token is refused when it is typed, not weeks later by a scheduler.
- The token stays write-only: nothing in this change causes it to reach a browser.

**Non-Goals:**

- Any other bank's API. Squire polls Fio; a token elsewhere would be unreadable.
- Changing what polling does, when the scheduler runs, or how transactions are matched.
- Storing the token encrypted at rest, or any other change to how it is held. That is a
  real question and a separate one; this change does not make it worse or better.
- Discovering the account number from the token. Fio returns it, but the account is the
  organizer's own statement of where money is collected, and deriving it would let a
  token silently rewrite it.

## Decisions

### Decision 1 — Fio-ness is decided in the browser, from the bank code

The action's availability is decided from the value in the account field as the
organizer types, which means the frontend has to answer "is this a Fio account" without
a round trip. Fio banka is bank code `2010` in CZ and `8330` in SK, and the bank code is
readable from both accepted forms: characters 4–8 of an IBAN, and the segment after the
final `/` in the domestic form.

So the frontend gains a small `isFioAccount(raw)` that normalises whitespace and case,
matches either shape, and compares the bank code against those two. It deliberately does
**not** validate: an account whose checksum fails but whose bank code is Fio's still
enables the action, because the field's own validator already reports the checksum and
two errors about one value teach nothing. An unparseable or partial value answers false.

*Alternatives considered.* Reading `detail.bank_account`, the saved value, needs no new
frontend knowledge but makes the organizer save before the control wakes up — the
owner ruled against it. A validation endpoint called per keystroke keeps the bank codes
in one language, at the cost of a new endpoint and a round trip per character for a
question whose answer is four characters long.

*The knowledge lives only in the console.* The server holds no Fio-ness test at all,
because there is nothing for it to gate: a token may legitimately be recorded while the
account beside it is still unsaved, so the endpoint cannot check the token against a
stored account without contradicting its own scenario. The rule is a rule about which
control is offered, and it belongs where the controls are. `accounts.py` is untouched.

### Decision 2 — The token has its own endpoint, and leaves the tournament PATCH

`fio_token` is removed from `TournamentUpdate`, and recording one becomes
`PUT /api/tournaments/{slug}/fio-token` (with `DELETE` on the same path to remove).
There is then exactly one way a token reaches the database, and it is the one that
verifies — the spec's requirement holds by construction rather than by convention.

Two things forced it. Verification is a network call, so it cannot live in the pydantic
validator where `bank_account` normalisation lives, and putting it in
`update_tournament` would make the general tournament save reach the internet for a
field almost no save carries. And the unreachable path (Decision 3) has to tell the
console the check did not happen; folded into the tournament PATCH its only channel is
`TournamentOut`, the payload every Setup section reads back, which is the wrong home for
a per-request flag. A dedicated endpoint answers with its own small model —
`{configured, verified}` — and says nothing about the rest of the tournament.

The check itself is `fetch(token, today, today)` through the injected `FioClient` — a
one-day read. It ingests nothing: the result is discarded, and nothing touches
`bank.ingest`. Adding a `verify(token) -> None` method to the `FioClient` protocol keeps
the reject/unreachable distinction (Decision 3) in one place and gives the tests a stub
with one obvious knob, rather than making every test that records a token stand up a
transaction fixture. Recording the same token twice verifies it twice; that is one
avoidable call on a rare action, and skipping it would make "record it again to
re-check" impossible.

`TournamentOut.fio_token_configured` is unchanged and stays the console's only reading
of what is stored.

*The cost.* Fourteen existing tests set a token by `PATCH`ing the tournament and must
move to the new endpoint against a stubbed client. That is mechanical, and it is the
same set of tests either arrangement would have touched.

### Decision 3 — A rejection refuses; an unreachable bank does not

`verify` raises for a token Fio rejects — a 4xx, and a bad token is a `404` — and the
endpoint answers `422 fio_token_rejected`, storing nothing. Everything else stores the
token and reports `verified: false`, so the form can say the check did not happen: a
transport failure (connection refused, timeout, DNS) is not evidence about the token,
and neither is a `5xx`, which is Fio's own fault. Fio being down for ten minutes must
not make a correct token unrecordable.

The asymmetry is deliberate. Refusing on a rejection costs the organizer a retype;
refusing on an outage costs them the feature until Fio recovers, for no gain in
correctness.

*One known wrinkle.* Fio rate-limits a token to one call per 30 seconds and answers
`409` when it is exceeded. A verification immediately followed by a poll can hit it.
`409` is therefore the one 4xx that is not a refusal — the token demonstrably exists,
since Fio recognised it well enough to count it — and takes the unverified path.

### Decision 4 — The form writes immediately; the section stays staged

The rest of the bank account section stages into the tab's save bar, as every Setup
section does. The token does not: submitting the form issues its own
`PUT …/fio-token` and reports the outcome inside the form, which stays open on a
refusal — the `WaiverReasonDialog` contract. Verification is the reason. A refusal has
to be readable at the field that caused it, and a rejected token folded into a tab save
would surface in the save bar's per-item failure list, at the far end of the page, long
after the dialog that owns the value has closed.

Removal is the `DELETE` on the same path. This is why the empty-field submission must be inert: with an
immediate write, an organizer who opened the form to look at the token and pressed save
would otherwise delete their feed. Clearing is a separate, named control.

### Decision 5 — The action sits on the account's line, as a text action

`BankAccountSection` renders one `form-field` label. The action goes in a row with it,
right-aligned, as an underlined text action rather than a button — matching the
treatment `tournament-admin` already fixes for the logo upload, and keeping the section
free of a second filled control competing with the save bar.

Placing it there rather than beneath the account is what makes the live availability
rule bearable: the action occupies its space whether it is available or not, so an
account becoming a Fio account changes the control's state and moves nothing. A field
appearing below the account would reflow the section under the organizer's cursor,
mid-typing, which is exactly the moment it must not.

The unavailable state is `--ink-faded` with the reason beside it, per the design
system's prohibition on hiding a control without explanation, and mirrors what
`PaymentModeSection` already does for the deposit mode it gates on the same token.

The form is a new file, `frontend/src/setup/FeedTokenDialog.tsx`, keeping
`BankAccountSection` inside its seam.

## Risks / Trade-offs

- **Two bank codes in two languages.** → Bounded to `2010` and `8330`; a comment in each
  file names the other, and a spec scenario covers both account forms.
- **A Setup screen now makes an outbound call.** → Only on the token endpoint, never on
  a tab save. The tournament PATCH every other Setup section uses no longer accepts a
  token at all and is untouched by this change.
- **Fio's 30-second rate limit.** → `409` takes the unverified path (Decision 3), so a
  verify-then-poll sequence records the token and leaves the poll to report its own
  refusal rather than losing the token.
- **A token recorded against an account the organizer has not yet saved.** → Permitted,
  and covered by a scenario. The token addresses Fio directly; the stored account is
  what Squire prints on payment slips, and the two are independent.
- **Fourteen existing tests set a token by `PATCH`ing the tournament.** → They move to
  the new endpoint against a stubbed `FioClient`. Mechanical, but it is the widest edit
  in the change, and a `PATCH` still carrying `fio_token` now fails validation rather
  than being ignored — which is what makes the miss loud instead of silent.
- **Verification reads the account's transactions.** → It discards them and ingests
  nothing, but it does mean recording a token touches the organizer's bank data. This
  is the cheapest call Fio offers that proves a token; a scenario fixes that nothing is
  ingested.

## Migration Plan

None. `Tournament.fio_token` already exists with the right shape and nullability, and no
stored value changes meaning. Tokens configured today by hand keep working and become
editable through the new control.

## Open Questions

None outstanding. The four decisions the owner made — live availability from the typed
account, the action on the account's line rather than a field beneath it, a write-only
form carrying the read-only-token advice, and verification on save — are settled above.
