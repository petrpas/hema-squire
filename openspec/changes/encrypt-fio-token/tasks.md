## 1. Key and sealing

- [ ] 1.1 Declare `cryptography` in `backend/pyproject.toml`; `uv run deptry .` agrees
- [ ] 1.2 Add `fio_token_key: str = ""` to `Settings`; a fixed dev key in `dev.sh` and the test configuration
- [ ] 1.3 `app/secretbox.py`: `seal` and `open_`, the only code that reads the key (design D1)

## 2. Write and read paths

- [ ] 2.1 `set_fio_token`: refuse with 409 `fio_token_key_missing` before calling Fio when no key is set; store `seal(token)`
- [ ] 2.2 Poll in `routers/payments.py`: open the token; 409 `fio_token_unreadable` where it does not open
- [ ] 2.3 Scheduler sweep: open the token; skip and log at WARNING where it does not open
- [ ] 2.4 Tournament detail: add `fio_token_readable` beside `fio_token_configured`

## 3. Migration

- [ ] 3.1 Alembic revision: widen to `String(400)`, encrypt every value not already opening under the key, refuse when readable tokens exist and no key is set; downgrade decrypts (design D4)

## 4. Frontend

- [ ] 4.1 Token form: state the missing-key refusal and the recorded-but-unreadable state, cs and en
- [ ] 4.2 Poll action: state the unreadable reason

## 5. Tests

- [ ] 5.1 The stored value is not the token and does not contain it
- [ ] 5.2 Poll and scheduler call Fio with the original token
- [ ] 5.3 No key: recording refused, nothing stored, Fio not called
- [ ] 5.4 Key replaced: Setup reports unreadable, poll refuses with the reason, scheduler sweep continues for other tournaments
- [ ] 5.5 Re-entering a token on an unreadable tournament recovers the feed
- [ ] 5.6 Migration: plaintext encrypted, already-sealed left alone, refusal without a key

## 6. Deploy

- [ ] 6.1 `deploy/.env.example` names `HEMA_SQUIRE_FIO_TOKEN_KEY` and how to generate it
- [ ] 6.2 Key into the server `.env` and the password manager, then deploy (design Migration Plan)
- [ ] 6.3 After deploy: no unreadable-token warning in the log, one poll succeeds
- [ ] 6.4 Mark S4 done in the drift map and `deployment_state.md`
