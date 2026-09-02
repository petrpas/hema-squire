## Why

Most fencers do not quote a variable symbol. The pilot's own bank export is the
evidence: 43 incoming payments, **not one carrying a VS** — the export has no
variable-symbol column at all, and the messages are prose. What they do carry is
the fencer's name, nearly every time: `NaDuel26: Jan Sax Bělina - šavle a meč a
štítek`, `Vejda Josef`, `NaDuel26: CHEREAU - Sabre and Sidesword`. Today every one
of those lands in the unmatched queue, and the organizer resolves 43 payments by
reading a message, finding the fencer, and typing a seven-digit number.

`payments` already anticipates this: "Foreign payments that still fail to match
SHALL be resolved manually; the system MAY suggest candidates by name and amount,
but only a human confirms the match." The MAY was never realised. This change
realises it, and finds that it applies far beyond foreign payments.

Two experiments against the pilot's real 43 transactions and real 54-fencer
roster shaped the design, and one of them is the reason to be careful:

- Matching on the payer name and the message **together**, with plain string
  similarity, put the right fencer first in 43 of 43. It also credited a payment
  whose message read `NaDuel26: Jindřich Pekárek- SB` to **Milan Diviš**, who
  merely paid for him. Both Pekáreks are on the roster. One organizer pays for
  three fencers in this statement alone.
- Matching on the **message only** resolved all three of those correctly, with
  comfortable margins, and produced a clear single winner for 35 of 43. The 8 it
  leaves are the human ones: a surname alone (`Jakubec`, `CHEREAU`, `Zubalik`), a
  missing space (`JosefVochozka`, `MikulášHorák`), a diminutive (`Dan Bělina`), a
  literal placeholder (`jmeno`, where the payer field is the only signal), and one
  benign tie between a duplicate pair.

So the message names who the payment is *for*; the payer names who *paid*.
Conflating them credits the wrong fencer, which is precisely what the spec's
"never by payer name" rule exists to prevent — and why that rule survives this
change rather than being repealed.

## What Changes

- **A third transaction state, `likely`.** A payment with no VS that resolves to
  exactly one fencer becomes `likely` rather than `unmatched`. It is a proposal:
  **no money moves, no balance changes, no mail is sent** until a human confirms
  it. Crediting remains exclusively by VS, whether the VS was quoted by the payer
  or supplied by the organizer confirming a proposal.
- **A queue for likely matches**, beside the existing four, where each proposal
  states the payment, the fencer it names and why — confirmed or rejected in one
  click.
- **The name a payment is for is extracted during the statement parse.** The
  model already reads every row; it gains one more thing to report — who this
  payment is for, taken from the message, falling back to the payer name only
  where the message names nobody. It caches per row like everything else in that
  pass, so a re-import costs nothing and no new per-transaction call is added.
- **Resolution against the roster is deterministic**, not a model: diacritics
  folded, tokens normalised and compared, every fencer scored and ranked. The
  experiments show a model is not needed for this, and keeping it deterministic
  makes it testable, tunable against real statements, and functional on a
  deployment with no LLM configured at all.
- **A proposal requires a clear winner**, which means two tests, not one: a
  minimum score *and* a minimum margin over the runner-up. The margin is the
  safety-critical half — a score alone waved the wrong Pekárek through, and both
  Pekáreks scored 1.00.
- **The link dialog gains the whole roster, ranked.** Today it offers detected VS
  values and an input to type a number into. It gains every fencer ordered by
  likelihood with the strongest marked, and a type-to-filter search over all of
  them, following the HEMA Ratings search dialog the console already has.
- Czech and English strings for the new queue, the new state and the dialog.

Not in scope: changing how a VS-matched payment behaves; tolerance; refunds;
partial payments. And nothing here credits money on a name — that is the point.

## Capabilities

### New Capabilities
- `name-assisted-matching`: how a payment with no variable symbol is resolved to
  a fencer — what the model extracts and from which field, how the roster is
  ranked, what makes a proposal rather than a guess, the `likely` state and its
  promise that no money moves, the queue that confirms or rejects it, and the
  ranked-and-searchable roster in the link dialog.

### Modified Capabilities
- `payments`: "Payment identity via variable symbol" says matching is performed
  exclusively by VS, "never by payer name or amount alone". The safety intent is
  kept and made exact — **crediting** is exclusively by VS, and a name resolution
  is a proposal a human confirms, never a credit. The transaction states gain
  `likely`, defined as carrying no money.

## Impact

**Depends on** `issue-imported-registrations`. A proposal resolves a payment to a
fencer, and confirming it credits that fencer's registration — so the roster must
have registrations to credit. On the pilot as it stands there are none, and this
change is unusable without that one.

**Backend** (`backend/app/`): the statement extraction in `bank.py` gains the
"who is this for" field and `statements.py` carries it through the existing
per-row cache; a new module for normalisation, scoring and ranking, with no LLM
dependency; `matching.py` at the `no_vs` branch (`matching.py:344`), which today
finishes a transaction as `unmatched` and instead consults the resolver;
`models.py` for the `likely` status value and the resolved-fencer reference, with
an Alembic migration; endpoints to confirm and reject a proposal, and to list the
ranked roster for a transaction.

**Frontend** (`frontend/src/`): a fifth queue card beside the four in
`payments/`; `LinkDialog.tsx` gains the ranked roster and its search;
`i18n/{en,cs}.json`. The queue follows the existing `QueueCard` and the console's
reload signal, so it needs no new plumbing.

**Builds on two unarchived changes**: `add-payments-console-ui` (the queues and
`LinkDialog`) and `add-payments-intake` (the statement parse this rides along
with). Both are implemented; neither is archived, so their spec deltas are the
current shape of those surfaces.

**Cost**: no new model call. The extraction rides the statement parse that
already reads each row, and ranking is local computation.

**Risk**: the whole change is one careful line — a proposal must never move
money. A `likely` transaction that credits is worse than no feature, because it
credits *silently* and mails the wrong fencer a confirmation. Tests must assert
the balance, the state and the mailer, not merely the status string.

**Verification**: `pytest` for extraction, normalisation, ranking, the two
thresholds, and — hardest — that `likely` moves no money and sends no mail;
`vitest` for the queue and the dialog; then the pilot's own 43 transactions,
where the expected shape is roughly 35 proposals and 8 for a human, and where
the three Milan Diviš payments must resolve to three different fencers.
