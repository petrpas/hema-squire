## Context

`tournaments.fio_token` (`String(200)`) is written in one place,
`set_fio_token` in `routers/tournaments.py`, after the token is verified
against Fio. It is read in two: the organizer's poll (`routers/payments.py`) and
the scheduler's sweep (`scheduler.py`). `setup.py` and the tournament detail
read only whether it is set. The API never returns it and the canonical export
does not carry it. Production held two tokens on 2026-11-15.

The threat this answers is a copy of the database leaving the server: the B2
replica and its 28 days of snapshots, or a copy taken for a restore drill. It
does not answer an attacker on the server itself, who can read the key from the
environment as the application does.

## Goals / Non-Goals

**Goals:**
- No copy of the database is enough to recover a token.
- No path stores a token readable, including a deployment that forgot the key.
- Losing the key costs re-entering tokens, never a crash or a wrong poll.

**Non-Goals:**
- Encrypting the whole replica (Litestream's own encryption). Possibly later,
  separately; whether 0.5.16 supports it is unverified.
- Key rotation tooling. Replacing the key is handled as losing it: the tokens
  read as unreadable and are entered again.
- Protecting against compromise of the running server.

## Decisions

### D1. Fernet from `cryptography`, one module

A small module, `app/secretbox.py`, holds `seal(token) -> str` and
`open_(stored) -> str | None`, the only code that touches the key. Fernet is
authenticated encryption with a versioned, base64 text output, so the value
fits a string column and a wrong key fails as an `InvalidToken` rather than as
garbage. `cryptography` is declared in `pyproject.toml` by its own name; it may
already arrive through another package, which is not a declaration.

Alternatives: a hand-built AES-GCM wrapper (more code for the same property);
SQLCipher for the whole database (changes the driver, the backup and the restore
drill for one column).

### D2. Its own key, empty by default

`settings.fio_token_key: str = ""`. Empty means the deployment cannot keep a
token: `set_fio_token` answers 409 `fio_token_key_missing` before calling Fio,
and the form states it. The key is not derived from `secret_key`, so replacing
the signing key, which signs every session, does not lose the feeds, and
replacing this one does not sign anyone out.

`dev.sh` and the test configuration set a fixed development key, published like
`DEV_SECRET_KEY`. Production must set its own. The application does not refuse
to start without one: a deployment with no Fio feeds is valid.

### D3. Unreadable is a state, not an error

`open_` returns `None` for a value the current key does not open. The tournament
detail gains `fio_token_readable: bool` beside `fio_token_configured`, so Setup
can say "recorded but unreadable" rather than "recorded". The poll answers 409
`fio_token_unreadable`. The scheduler logs `fio token unreadable for <slug>` at
WARNING and moves on to the next tournament. Recording a new token overwrites the
stored value as it does today.

Deposit mode and the poll action are offered on `fio_token_configured`, as now.
An unreadable token keeps them offered, and the poll states why it cannot run.
Withdrawing deposit mode because a key went missing would change a tournament's
payment rules behind the organizer's back.

### D4. Migration encrypts in place

One Alembic revision widens the column to `String(400)`, then encrypts every
non-empty value with `settings.fio_token_key`. A value that already opens under
the key is left alone, so the revision is safe to rerun. Where readable tokens
exist and no key is configured, the revision raises with a message naming
`HEMA_SQUIRE_FIO_TOKEN_KEY`. The deploy then fails and the old containers keep
running, rather than leaving the tokens readable or dropping them.

Downgrade decrypts back to plain text with the same key.

## Risks / Trade-offs

- [The key is lost] → The tokens read as unreadable and organizers enter them
  again; nothing else breaks. The key goes into the password manager with the
  rest of `.env`.
- [The deploy runs before the key is set] → The migration refuses (D4); setting
  the key and redeploying finishes it.
- [A restore drill on a workstation without the key] → The drill copy holds no
  readable token, which is the point. Feeds there read as unreadable.

## Migration Plan

1. Generate the key:
   `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
2. Add `HEMA_SQUIRE_FIO_TOKEN_KEY=<key>` to the server's `deploy/.env` and to the
   password-manager copy.
3. Deploy. The revision encrypts the two stored tokens.
4. Check: a scheduler sweep logs no unreadable token, and one organizer poll
   succeeds.

Rollback: downgrade the revision with the key still set, then deploy the
previous commit.
