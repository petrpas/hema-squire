# Static analysis — deferred

Written 2026-09-08, between phase 4 and phase 5 of
`openspec/changes/static-analysis-spec.md`. Everything here was found by that
work, deliberately not done in it, and is worth doing eventually. Nothing here
is urgent and nothing blocks phase 5.

Security items are **not** here — they are in `security_tbd.md`, which is
untracked for its own reasons. That one has an urgent item; this one has none.

---

## 1. The contract suite reaches 15 operations out of 108

The biggest gap by a distance, and the one that makes the rest look better than
it is.

`tests/test_api_contract.py` passes on all 108 operations. Measured, the runs it
passes on are:

| | |
|---|---|
| generated requests | 8 222 |
| answered 404 | 6 215 (75.6%) |
| answered 2xx | 353 (4.3%) |
| operations that ever reached 2xx | **15 of 108** |
| operations that never got past an error | **93** |

The cause is structural, not a bug in the suite: the fuzzer starts from an empty
database with a fresh organizer account, so everything under
`/api/tournaments/{slug}/...` 404s on the slug before the handler runs. For 93
operations — the whole payments console, the import pipeline, registrations,
teams, rules, export — a green test means *the 404 path is sound*, and nothing
more.

It also explains where the four bugs phase 4 found were: all of them on
`/api/account` and `/api/account/plea`, which is the only place it could reach
live code. Not because those endpoints are worse, but because that is where it
looked. The same classes — an explicit null into a NOT NULL column, an instant
serialized without its zone, a response that does not match its schema — are
unaudited across the other 93.

**What it needs:** a seeded fixture the contract suite starts from — one
published tournament with a discipline, a registration, and an import batch —
so generation begins behind the 404 wall. Roughly an hour's work, and it should
take the reached count from 15 to most of 108. Worth doing *before* phase 5,
which is optional and worth much less.

## 2. About twenty `date-time` response fields are unaudited

Phase 4 caught `PleaOut.created_at` serialized with no offset, so a client reads
a UTC instant as its own local time. `fieldtypes.UtcInstant` fixes that one and
states the rule; `rules._utc` had already fixed the same failure for the
manual-edits log.

Twenty-odd other fields declare `format: date-time` and were never reached with
data, so their zone behaviour is unknown: `RegistrationOut.expires_at`,
`registered_at`, `paid_at`, `TransactionOut.last_evaluated_at`,
`ManualPaymentOut.created_at`, `RuleOut.created_at`, and the rest.

**This is not a sweep.** The frontend deliberately distinguishes the two forms —
an offset-bearing stamp is shifted into the tournament's zone, a zone-less one
is shown unshifted, and `frontend/src/consoleCells.test.tsx` holds that line
under the name "an imported row's zone-less stamp". A stamp that came from
someone else's table has no zone to restore. So each field needs deciding, not
converting.

Same subject as `openspec/changes/date-boundaries-read-three-clocks.md`, and it
belongs with that analysis rather than on its own.

## 3. Tests and scripts are outside the basedpyright gate

`pyproject.toml` gates `app/` only. Widening it today would add **78 findings**
— 72 in `tests/`, 6 in `scripts/`:

```
  43  reportArgumentType
  31  reportOptionalMemberAccess
   3  reportAttributeAccessIssue
   1  reportIncompatibleMethodOverride
```

The `reportArgumentType` majority is one shape: fakes (`StubRule`,
`FakeTournament`, `ExceptionInfo`) handed to functions typed against the real
models. Fixing it means introducing protocols at those seams — the same move
`_TeamEntry` made in `routers/registrations.py`, and real design work on the
test suite rather than annotation. The `reportOptionalMemberAccess` half is
mostly `session.scalar(...)` results used without narrowing, which is cheap.

Doing the cheap half first would leave a much smaller decision.

## 4. Two things phase 4 found and did not act on

Both were reported by schemathesis checks that are switched off in
`tests/test_api_contract.py`, which records why for all eleven.

- **A route's tournament lookup resolves before its auth dependency**, so an
  unauthenticated caller gets 404 where 401 was expected — 76 findings. Not a
  disclosure as things stand: a slug is public in `/api/tournaments/open`, so
  the 404 tells nobody anything the listing does not. It is still resource
  lookup ahead of authentication, which is worth knowing if a non-public
  resource ever gets the same shape.
- **Starlette answers 404 rather than 405 for an undeclared method**, and its
  `Allow` header does not list every documented one. Framework behaviour, not
  the application's, and only worth touching if a client ever depends on it.

## 5. Smaller, and genuinely optional

- **`ruff-format` is not adopted.** 38 backend files would change on the next
  commit that touched any of them, and CI does not check formatting. Deliberately
  left out of `.pre-commit-config.yaml`, with a comment there saying so. It is a
  decision of its own; the diff is large and entirely mechanical.
- **`ValidationErrorResponse.detail` carries a `| str` half.** That is the
  incomplete migration `app/errors.py` describes in its module docstring — a
  router code not named in `_ROUTER_CODE_FIELDS` still answers with a bare
  string. When the last one is converted, the `| str` goes with it and the
  published schema gets simpler.
- **Phase 5** — `deptry` (undeclared and unused dependencies) and `vulture`
  (dead code). The spec marks both optional and non-blocking, and `vulture`
  false-positives heavily on FastAPI's dependency injection, so it is an
  occasional manual run rather than a gate.
