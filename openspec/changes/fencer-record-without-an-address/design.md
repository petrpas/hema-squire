## Context

Squire's `Fencer` is one record wearing two hats. It is a **login** — an email
and a password hash, unique across the deployment, portable between tournaments
— and it is a **person on a roster**, carrying the name, nationality, club and
HEMA Ratings binding that every fencer-facing surface reads.

For a fencer who signs up, the two hats are the same head and the address is
free. For a fencer the organizer enters on the tournament's behalf, only the
second hat exists: `fencer-accounts` says such a record "SHALL hold no
credentials and SHALL NOT be usable to log in. Its creation SHALL send no mail:
no invitation, no welcome, no notice that a record exists." The address is
collected anyway, because `models.py:194` makes it `NOT NULL` and unique — a
constraint that belongs to the first hat being imposed on a record that only
ever wears the second.

The pilot shows what that costs. Two brothers entered on their parent's address
cannot both be issued, so neither is billable, and the organizer meets it as
"this fencer is not in the list" four screens away from the cause.

The constraints that shape the design are already written down:

- **Nothing mails an issued registration.** Two guards, arrived at separately:
  `clocks_dormant` keeps the scheduler away (`issue-imported-registrations`
  Decision 3), and `_payment_mail_suppressed` keeps the organizer's own credit
  mail away (task 7.2b of the same change, found by a sweep — "Dormancy stops
  the scheduler; it did not stop the organizer").
- **Mail has exactly one door.** `mail.build_message(to, sender, subject, body,
  …)` constructs every message; `Mailer.send` posts it. Fifteen call sites in
  `emails.py` pass `fencer.email` straight into the first argument.
- **An address identifies an account, not a person.** `routers/accounts.py:66`
  probes it for uniqueness on signup and on profile edit; `auth.py` looks a
  login up by it.
- **A roster member is deliberately not a `Fencer`.** `TeamMember`'s docstring
  gives the reason as "`Fencer.email` is unique and non-nullable, and most
  roster members neither have nor will ever have a Squire account" (design
  team-disciplines D4).

## Goals / Non-Goals

**Goals:**

- Every fencer-list row that states a name and a discipline can be issued a
  registration, whatever address it carries or repeats.
- A record with no address is a fencer of the tournament in every respect that
  is not logging in or being written to.
- A message with no recipient is impossible to construct, not merely never
  constructed in practice.
- No existing account changes, and no address already held is taken away.

**Non-Goals:**

- Reconciling a record created this way with an account the person later opens.
  That is `issue-imported-registrations`' stated non-goal and stays one.
- Showing or editing `email` on the fencer table. It was the remedy for the
  failure this removes.
- Any change to how a fencer who signs up is identified. The login is still an
  address, and it is still unique.

## Decisions

### Decision 1 — Drop the constraint, do not work around it

Three ways to make two brothers billable. Mint a synthetic address
(`pekarek.jindrich@…`); relax the per-tournament uniqueness so two registrations
may share a fencer; or let the record hold no address.

The synthetic address is the worst of the three and the most tempting, because
it is one line. It writes a falsehood into the field whose entire meaning is
"somewhere a person can be reached", and it writes it into the column that also
decides who may log in — so the falsehood is not inert, it is an account waiting
to be claimed by whoever controls that domain. A field that is sometimes a real
address and sometimes a fabrication is worse than a field that is sometimes
absent, because absence is legible and a fabrication is not.

Sharing a fencer between two registrations breaks the thing the roster is for:
the two brothers are two people, and every count, export and placement would
have to learn that one `Fencer` sometimes means two.

Leaving the column empty says exactly what is true: nobody gave Squire a way to
reach this person, and Squire does not need one, because it is never going to
write to them.

### Decision 2 — An address is claimed by at most one record

Two rows on one list carrying one address is not one person entered twice — that
is deduplication's question, asked and answered before issuing runs. It is one
person's address written against somebody else, which is what a parent or a club
representative entering a family does.

So the pass claims an address once. A row whose address already belongs to a
fencer record reuses that record, exactly as today: an existing account keeps
its identity, its name, its HR binding, and the pilot has rows of that kind. A
row repeating an address the pass has just used gets a **new record with none**.

The alternative — giving the second record the same address and dropping the
unique index — was rejected. The index is what makes an address a login, and an
address is still a login for everyone who has one. What this change removes is
the requirement to have one, not the meaning of having one.

Which row keeps the address is the order the rows are issued in, which is
registration order. That is arbitrary between siblings and it does not matter:
nothing is sent to either record, and the address remains visible on both rows
of the fencer list, which is where it was written.

### Decision 3 — Refuse a recipientless message at the door, not at the callers

The invariant "an addressless fencer is never mailed" is true today by
coincidence of two guards. Coincidence is exactly what task 7.2b caught: the
scheduler was guarded, the organizer's path was not, and confirming forty-three
proposals would have mailed forty-three people who registered a season ago.

So `mail.build_message` refuses a falsy recipient by raising. Three reasons for
the door rather than the callers:

- **It cannot be forgotten.** Fifteen call sites today, and the sixteenth is
  written by someone who has never read this document.
- **It fails loudly.** A raise in a request is a five-hundred and a test that
  goes red. Skipping silently would turn a missing notification into a mystery
  the organizer reports months later as "the fencer says nothing arrived".
- **It is the honest shape.** Building a message with no `To` is not a state the
  system has an opinion about — it is a programming error, and that is what an
  exception is for.

Deliberately **not** a silent skip inside `emails.py`. Every function there
sends something a person is supposed to receive; a version that quietly sends
nothing is a worse bug than the crash, because the caller believes it worked.

The consequence for callers is small and is the point: any path that could reach
mail with an addressless fencer has to say what it does instead. Today there is
no such path — dormancy and the payment-mail suppression cover both — and the
tests assert that by calling the mail path directly against an addressless
fencer, not by asserting the fencer is dormant.

### Decision 4 — The skip reasons shrink rather than being reinterpreted

`no_email` and `email_taken` are removed, not redefined. What a row must have to
be issued becomes a name and at least one discipline, and both survivors are
about the row being unreadable rather than about Squire's bookkeeping —
`no_name` cannot make a fencer, `no_discipline` would make a registration
totalling zero that reads as settled and quietly absorbs a payment
(`imported-registrations`, Decision 6).

That is the test the remaining reasons pass and the removed ones failed: a skip
reason should describe something wrong with the row, not something inconvenient
about the schema.

The surfaces that name them — `would_skip`, `GET /import/issue`'s `skipped`, the
intake pre-flight, the link dialog's notice — keep working with fewer reasons to
report, and the two translations go.

### Decision 5 — The unique index stays

`NULL` is not equal to `NULL` in either SQLite or Postgres, so a unique index
admits any number of them. Nothing about the constraint has to be rebuilt, and
an address that is present is still unique across the deployment — which is what
`auth.py` and `routers/accounts.py:66` rely on, and neither is touched.

## Risks / Trade-offs

**A path reaching mail with an addressless fencer.** → The risk the change turns
on, and Decision 3 is the whole of the answer. Tests must exercise
`build_message` and each `emails.py` entry point against a fencer with no
address, not merely assert that such a fencer is dormant. A test that proves the
scheduler skips them proves nothing about the next caller.

**A reader that assumes an address is present.** `export_json.py:108`,
`sheet.py`, `routers/admin.py`, `routers/manual_api.py`,
`routers/registrations.py`, `routers/tournaments.py`. → Each is checked and
made to state absence rather than render `None`. The exports are the ones to
watch: a column reading `None` in a CSV an organizer sends onwards is a defect
that leaves the building.

**A person who later signs up gets a second record.** → Already true of anyone
whose issued record carries an address they do not use, and out of scope by
`issue-imported-registrations`' own statement. This narrows the case where the
signup could have found the old record — an address is what would have matched
it. Worth stating in the spec rather than discovering later: the two records do
not merge, and no history follows.

**`TeamMember`'s rationale loses half its ground.** Its docstring says a roster
member is not a `Fencer` because the address is unique and non-nullable. Half of
that stops being true. → The reason that survives is the one that was doing the
work anyway, and is already in the same docstring: identity is local to the
roster, and two rosters naming the same person produce two independent rows. The
docstring is restated rather than left to contradict the model.

**Rollback.** The reverse migration reimposes `NOT NULL`, and fails while any
record created under this change exists. Like the dormancy migration before it,
treat as one-way in practice once used.
