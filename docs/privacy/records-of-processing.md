# Record of processing activities

Article 30 GDPR. Kept with the code so it changes with it. The repository is
public: nothing here goes beyond what the privacy page (`/privacy`) states.

- **Controller:** Petr Paščenko, natural person, Prague. Contact:
  privacy@hemasquire.eu.
- **Organizers** are controllers for entries, payments and matching on their
  events; the operator is their processor under the organizer data terms
  (`privacy.terms` in the locale files, version `ORGANIZER_TERMS_VERSION` in
  `backend/app/privacy.py`).

## Activities

| Activity | Role | Data subjects | Data | Basis | Period |
|---|---|---|---|---|---|
| Accounts and sign-in | controller | account holders | name, e-mail, password hash, club, nationality, HEMA Ratings ID, language, profile audit trail | Art. 6(1)(b) | until the account is deleted |
| Event entries | processor for the organizer | fencers, guests, people entered by an organizer | disciplines, items, contact address, accommodation, notes, amounts, variable symbol | organizer: Art. 6(1)(b) | contact address, notes, accommodation, import and manual row details: 12 months after the event date |
| Payments and matching | processor for the organizer | payers | payer name, account number, message, amount, date | organizer: Art. 6(1)(f) | payer name, account, message: 12 months after the event date; amounts, dates, variable symbols stay |
| Public rosters and their history | controller | entrants | name, nationality, club, HEMA Ratings ID, paid mark | Art. 6(1)(f), see `roster-balancing-test.md` | no period |
| Outgoing mail | controller | recipients | address, subject, body, delivery status | Art. 6(1)(b) and (f) | 30 days after sent or given up |
| Pending signups, password resets | controller | people signing up or resetting | address, token | Art. 6(1)(b) | until expiry |
| Login throttle | controller | anyone signing in | client IP address | Art. 6(1)(f), security | in memory only, for the throttle window; no access log is written (`--no-access-log` in `deploy/Dockerfile`) |
| Backups | controller | all of the above | the database | Art. 6(1)(f), security | 28 days |

## Processors

| Processor | Service | Location | Transfer basis |
|---|---|---|---|
| Hetzner Online GmbH | server | Helsinki, Finland | EU |
| Backblaze, Inc. | database replica | eu-central-003, Amsterdam, the Netherlands | EU region; verify DPA (task 1.2) |
| Scaleway SAS | outgoing mail | France | EU |
| Anthropic, PBC | language model for table reading, deduplication, payment matching, only when an organizer runs it | USA | standard contractual clauses; verify (task 1.2) |

Google (Sheets export) is not a processor of the operator: the organizer
chooses to export there under their own agreement with Google.

## Open

- Retention at Anthropic and Scaleway TEM logs, and each processor's DPA:
  privacy-baseline task 1.2.
