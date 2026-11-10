## Context

The deployment runs on Hetzner in Helsinki, replicates to Backblaze B2, sends mail through Scaleway TEM and sends names and payment text to Anthropic for table import, deduplication and matching. Organizers may export to Google Sheets and download JSON, PDF and PNG. The application has no privacy text at all. The operator is a natural person, and tournament money goes to organizers' own bank accounts.

## Goals / Non-Goals

**Goals:**
- Meet the information duty for every group: account holders, guests, people entered by an organizer, organizers.
- Fix who is controller for what, so later changes have one answer.
- Give account holders self-service access to their data.

**Non-Goals:**
- Cookie consent: confirm during 1.1 that Squire sets no non-essential storage; if it does, that is a new decision.
- Legal entity changes.
- Self-service export or deletion for records without an account; those go through the request channel.
- Legal review itself. The text ships only after the owner has had it checked.

## Decisions

### D1. Roles split by who decides

The operator is controller for accounts, the public web and rosters with their history, and mail and security operations. The organizer is controller for tournament entries, payments and matching, with the operator as processor. Organizer exports are outside Squire.

A plain "organizer owns tournament data" split was rejected: a processor could not decide on its own that names stay on rosters, and the owner has decided exactly that.

### D2. Legitimate interest for retained rosters, stated up front

Keeping a name, HR ID, club and nationality on a held roster after deletion rests on Article 6(1)(f): a complete historical record of a sporting event. The balancing test lives in `docs/privacy/`. The right to object stays open and is decided case by case. Nothing may say "anonymised", because the name stays joined to its registration.

### D3. Page text in the locale files, not in the database

The page is versioned with the code and reviewed in a diff. A CMS for one page buys nothing. Each published version carries an effective date; the organizer terms carry a version constant that drives re-acceptance.

### D4. Terms gate the owner's console once

Accepting at tournament creation would miss every existing owner. A `Modal` when an owner opens a console catches both. Team members below the owner are not asked, because the owner is who the terms bind. Acceptance is two columns on `Fencer`: version and moment.

### D5. Export is the account's own view, not the tournament export

`GET /api/account/export` returns the profile, the profile audit trail, and the account's registrations with disciplines, extras and credits, in JSON. It excludes other people's data, namely bank payer fields and members of any team, and it excludes organizer corrections and rules. The tournament's canonical export is the wrong shape, as it carries the whole roster.

## Risks / Trade-offs

- A published period that is not true → Task 1 verifies Anthropic, Scaleway and B2 before text is final. Anthropic's public pages disagreed when checked, and retention may depend on the model.
- Home address made public → the owner decides what is published; the repository stays free of it until then.
- Role split challenged as joint controllership for rosters → stated in the legal review task; if so the terms gain an Article 26 arrangement and users' rights are unchanged.
- Gate blocks an owner during an event → one click, and the terms state nothing new about what the organizer already does.

## Migration Plan

Add the columns, ship the page and notices, then enable the gate. Rollback removes the gate; the columns are harmless.

## Open Questions

- Which mailbox receives requests, and whether the street address is published. The change cannot ship without the mailbox.
- Whether the legal review accepts D1 and D2 as written.
- Whether the operator's activity needs a trade licence; for the owner's accountant, outside this change.
