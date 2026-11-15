## Why

The Fio feed token is stored in `tournaments.fio_token` as the token itself.
Every copy of the database therefore holds it readable: the server's disk, the
Litestream replica in B2 with 28 days of snapshots, and any copy taken for a
restore drill. Even a read-only token opens the whole history of the account it
reads, usually a club's, with every payer's name, account and message, not
only the tournament's payments. Found as S4 in the spec-vs-code drift map of
2026-11-12; no spec said how the token is kept.

## What Changes

- The token is encrypted before it is written and decrypted only where it is
  used, with a key of its own read from the deployment's configuration
  (`HEMA_SQUIRE_FIO_TOKEN_KEY`). The key is never stored in the database and is
  not derived from the signing key.
- With no key configured, a token is not recorded: the form states that this
  deployment cannot keep a feed token. A token is never stored readable.
- A stored token that cannot be decrypted, because the key was lost or
  replaced, is reported in Setup as recorded but unreadable, to be entered
  again. The scheduler skips it and logs the tournament.
- A migration encrypts the tokens already stored. It refuses to run while
  readable tokens exist and no key is configured.
- `deploy/.env.example` names the key and how to generate it.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `tournament-admin`: a new requirement on how a feed token is kept at rest,
  and what Setup states when it cannot be kept or read.

## Impact

- `backend/app/config.py`, a new small module for sealing and opening the
  token, `routers/tournaments.py` (record), `routers/payments.py` and
  `scheduler.py` (read), the tournament detail's `fio_token_configured`.
- `backend/pyproject.toml`: `cryptography` declared by its own name.
- An Alembic revision that encrypts existing tokens and widens the column.
- Frontend: the token form's wording for the two new states.
- Deployment: the key must be in the server's `.env` and in the password
  manager before the deploy that carries the migration.
