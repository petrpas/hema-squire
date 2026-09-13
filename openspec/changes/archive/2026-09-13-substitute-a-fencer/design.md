## Context

The fencer list is a projection: source records (in-app registrations, imported
rows, hand-entered rows) are read into rows, and the organizer's manual actions
are replayed over them as rules (`sheet.py`, `rules.py`). Two kinds of rule
exist today — one writing the projected row, one writing the registration behind
it (`edit-rules`, "A rule may act on a registration rather than on a projected
row"). Row removal is a rule of the first kind.

A substitution is neither. It does not restate a field and it does not change
what a registration is billed; it changes **who holds the seat**. Every figure
the owner asked the substitute to inherit — fixed number, registration moment
and hence order, substitute-queue placement, VS, total, credits — is already a
property of the registration or of the row id, not of the fencer, so inheriting
them is achieved by *not touching them*. That is the design: the seat stays, the
person is exchanged.

Constraints that shape it:

- `registrations` carries `UniqueConstraint(tournament_id, fencer_id)`.
- `fencers.email` is unique and nullable; a record without credentials is
  already a supported population (`fencer-accounts`).
- Balances are derived from `PaymentCredit` rows keyed by registration, not by
  fencer (`payment-ledger`), so credits follow the seat with no work at all.
- Manual mode means Squire runs nothing and mails nothing (`tournament-mode`).

## Goals / Non-Goals

**Goals:**

- One action on a fencer-list row that exchanges the person and leaves the seat.
- A substitute named through the existing HR search, profile optional.
- An address that is the seat's, not necessarily the person's.
- Two mails on a published automatic tournament; none anywhere else.
- Full reversibility through the manual-edits log.

**Non-Goals:**

- Refunds, partial refunds, transfer fees, or any movement in the payment
  journal. Money between the two fencers is theirs to settle.
- A fencer-initiated substitution. This is an organizer action only.
- Re-pricing the seat for a substitute who would have been charged differently
  (a different discipline tier, a member discount). The seat is inherited as it
  stands; an organizer who wants a different price amends the registration
  afterwards by the means that already exist.
- Any change to matching, deduplication, the bank feed or export beyond what
  follows from the row now naming a different person.

## Decisions

### D1 — The registration is reassigned, not recreated

`registration.fencer_id` is repointed at the substitute's `Fencer` record. Its
id, `vs`, `registered_at`, `total_amount`, `total_eur`, `expires_at`,
`clocks_dormant`, `source_row_id`, entries, teams, credits and waivers are left
alone.

*Alternative rejected:* cancel and re-register. It would mint a new VS, restart
the payment window, orphan every credit already matched against the old VS, and
put the substitute at the end of the seating order — the exact opposite of what
was asked. It would also make the bank statement unreconcilable: money already
arrived under the old VS.

### D2 — A third rule kind, `row_substitute`, carrying both identities

The payload carries the substitute's `name`, `hr_id | null`, `nationality`,
`club`, `email | null`, and a `previous` block holding the same fields as they
stood, plus `previous_fencer_id` where a registration was reassigned.

Storing the previous identity in the rule rather than re-deriving it at
withdrawal keeps withdrawal correct after a second substitution, and after an
HR index refresh that moved a profile.

One rule, not a bundle of field edits: field edits are withdrawn individually,
and half a withdrawal leaves a row wearing two people's names.

*Which half of the kind applies* follows the amendment precedent exactly — ask
`amendment.registration_for_row`; a registration means reassign, no registration
means write the projection.

### D3 — `registrations.contact_email`, nullable

New column. `NULL` everywhere today, so the migration is additive and needs no
backfill. Set by a substitution when an address is given; read by a single new
resolver in `emails.py`:

```python
def recipient(registration: Registration, fencer: Fencer) -> str | None:
    return registration.contact_email or fencer.email
```

Every `emails.py` send that has a registration in hand routes through it. The
sends that have no registration (account mail) are untouched.

*Alternative rejected:* write the kept address onto the substitute's `Fencer`
record. It cannot be done — the address belongs to the replaced fencer's account
and `fencers.email` is unique — and it would be wrong if it could: it would make
the club's shared address a login for a person who never chose it.

*Alternative rejected:* a `contact_email` on the `Fencer` record. The address
belongs to the seat, not the person; a fencer who is substituted into two
tournaments under two addresses would need two.

### D4 — Which fencer record the seat lands on

In order:

1. The address matches an existing `Fencer` other than the replaced one **and
   that record's name is the substitute's**, compared with `hr_index.name_key`
   → reassign to it; refuse with `substitute_already_registered` (409) if that
   fencer already holds a registration on this tournament. The name test is the
   one `issuing._resolve_fencer` already makes, and for the same reason: a club
   address under another name is the payer's, not the entrant's.
1b. The address belongs to an account of a different name → an account-less
   record, the address held as `contact_email`. The other account is untouched.
2. The address is the replaced fencer's own, or is absent → create a `Fencer`
   with `email=NULL`, `password_hash=NULL`, the substitute's name, profile,
   nationality and club; store the address (where given) as
   `registration.contact_email`.
3. The address matches no account → create the record **with** that address, so
   the substitute can later claim it by the ordinary signup path.

Case 2 is what makes "keep the current address" mean what the owner asked: the
seat keeps its contact, the account does not keep the seat.

### D5 — The HR binding is a verdict, reusing what exists

The dialog embeds `HRSearchPicker` unchanged. A chosen profile writes
`hr_id` and the canonical name/nationality/club into the payload, and the
projection treats it as `match_verdict: "confirmed"`, the same shape a typed id
produces today. No profile leaves `hr_id` null and `match_verdict: "unknown"`,
so Matching on HR raises the row like any other. Ratings come from the existing
snapshot lookup keyed by `hr_id`; a substitute the snapshot does not cover
simply reads empty, which is already the handled case.

### D6 — Mail: two messages, sent once, by the router

Two new templates, `email.substituteArrived` and `email.substituteDeparted`,
in both locale files. Sent from the rules endpoint after the rule commits, not
from the rule's replay function — replay runs on every projection and must stay
free of side effects.

Gate: automatic **and** an address known. Publication needs no gate of its own here — `require_published` already stands in front of every rule the console creates, which is why the draft case is a refusal rather than a silent send. Where
`contact_email == replaced address`, one message is sent, the arrival one.
The arrival message reuses `payment_qrs` and `_amount_text` against
`outstanding_cents`, exactly as `send_promoted` does, so a part-paid seat is
inherited with the right figure rather than with its full total.

### D7 — The icon

`IconUserShare` (outline, tabler, `size=16 stroke=1.5`), beside `IconTrash`.
An outline person handed on reads as a person changing, where an arrow alone
reads as the restore action already in that column. It carries a `title` and a
`visually-hidden` label like every other row action.

### D8 — Where the dialog lives

`frontend/src/substitute/`: `SubstituteDialog.tsx` (the `Modal`, the submit and
the refusals), `SubstituteIdentitySection.tsx` (name + HR picker),
`SubstituteContactSection.tsx` (the address, the keep-current choice, the mail
notice). The orchestrator stays thin, as `src/setup/` does.

## Risks / Trade-offs

- **A substitution on a seat whose money was matched by payer name, not VS** →
  Nothing breaks — the credit is on the registration — but the payment console
  will show a credit whose payer name matches nobody on the roster. Accepted:
  the substituted row states whom it replaced, which is exactly the explanation
  a reader needs.
- **The replaced fencer loses sight of the registration** → It leaves their
  profile the moment the seat moves. Mitigated by the departure mail, which is
  the record they keep.
- **`contact_email` routes every later message** → A reminder for this seat now
  goes to the club address rather than to the substitute, where the address was
  kept. That is what keeping it means, and the dialog says so before confirming.
- **Repeated substitution grows a chain in the log** → Accepted; each rule is
  self-contained and withdrawal is well-defined at any depth.
- **Refusal for an already-entered substitute is a dead end** → The organizer
  must deal with the substitute's own registration first. Stated in the refusal
  rather than repaired automatically: merging two seats is deduplication's job,
  not this action's.

## Migration Plan

One additive migration: `registrations.contact_email VARCHAR(320) NULL`. No
backfill, no data rewrite, and nothing reads it until a substitution writes one.
Rollback is dropping the column; any substitution made in the meantime keeps its
rule and its reassigned fencer, losing only the seat's contact address.
