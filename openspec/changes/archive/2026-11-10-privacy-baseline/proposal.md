## Why

Squire holds personal data of fencers, guests and organizers on a live deployment and tells none of them who is responsible, why it is held, for how long or how to exercise their rights. Article 13 GDPR requires this at collection regardless of whether account deletion exists, and account deletion cannot make an honest promise until roles and retention are stated.

## What Changes

- A public privacy page, in every bundled language, naming the controller (Petr Paščenko, a natural person), the purposes and legal bases, recipients, retention periods and rights, including that a name stays on held rosters after account deletion.
- A notice with a link to that page beside every form that collects personal data: signup, guest registration, registration.
- Organizer data terms: where the organizer is the controller and Squire its processor (entries, payments, matching). A tournament owner accepts them before using the console; acceptance and its version are recorded.
- An account holder can download their own data as JSON from the Profile page (Articles 15 and 20).
- A private request channel: a mailbox that actually receives mail, stated on the page. A request from someone with no account (a guest, a person entered by an organizer) goes there.
- Compliance records in the repository: record of processing activities, the balancing test for keeping names on rosters, and the list of processors.

## Capabilities

### New Capabilities

- `privacy`: the privacy page, collection notices, organizer data terms, own-data export and the request channel.

### Modified Capabilities

None. The notice and terms are stated in `privacy` and reach existing screens without changing their requirements.

## Impact

- `frontend/src`: public privacy route in `routes.ts` and `App.tsx`, a persistent link to it, notices on the account and registration forms, a terms `Modal` on the console, a download control in `profile/`, `cs` and `en` keys.
- `backend/app`: `GET /api/account/export`, acceptance columns on `Fencer` with a migration, a guard on the owner's console.
- DNS: the domain's blackhole MX cannot receive requests, so the chosen mailbox may require an MX change.
- `docs/privacy/`: new compliance records. The repository is public, so they contain nothing that is not also on the page.
- Blocks `account-deletion` and `data-retention` going live, because both rely on the published periods and roles.
