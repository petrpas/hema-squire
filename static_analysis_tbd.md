# Static analysis — deferred

Written 2026-09-08, between phase 4 and phase 5 of
`openspec/changes/static-analysis-spec.md`. Everything here was found by that
work, deliberately not done in it, and is worth doing eventually. Nothing here
is urgent and nothing blocks phase 5.

Security items are **not** here — they are in `security_tbd.md`, which is
untracked for its own reasons. That one has an urgent item; this one has none.

---

## 1. ~~The contract suite reaches 15 operations out of 108~~ — done

Seeded in `tests/contract_seed.py`, and the suite substitutes the real ids for
the generated ones. Measured again afterwards:

| | before | after |
|---|---|---|
| answered 404 | 75.6% | 9.6% |
| answered 2xx | 4.3% | 32.6% |
| operations reaching 2xx | 15 / 108 | **74 / 108** |

It found six more bugs on the way, all listed in the commit. The 34 operations
still short of a 2xx mostly need state a seed cannot reasonably hold — a
settled seating, an expired reservation, a dedup group mid-decision — and are
worth revisiting only if something looks wrong in one of them.

One trade came with it, recorded in the test file: a path id is no longer
fuzzed, so an id the route cannot handle is not reached through a path
parameter. `RowId` bounds the body-side ones, and the path-side equivalent —
`Annotated[int, Path(ge=1, le=ROW_ID_MAX)]` on the ten routes that take an id —
has not been done and would close it.

## 2. ~~About twenty `date-time` response fields are unaudited~~ — done

Sixteen were naive and are now `UtcInstant`; the audit is in the phase-4
follow-up commit. `server_time`, both `registration_opens_at` and
`NetChangeOut.at` were already offset-aware and were left alone, and
`ManualRowOut.registered_at` / `ManualEntryIn.registered_at` stay naive
deliberately — an imported stamp has no zone to restore, which
`frontend/src/consoleCells.test.tsx` holds to by name.

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
- **`ValidationErrorResponse.detail` is a three-way union.** The envelope, a
  bare string, and an arbitrary diagnostic dict — the incomplete migration
  `app/errors.py` describes in its module docstring. A union that says "one of
  these" is weak, but it is true, and the single array FastAPI used to promise
  was not. As router codes move into `_ROUTER_CODE_FIELDS` the last two shapes
  go with them and the published schema gets simpler.
- **Phase 5** — `deptry` (undeclared and unused dependencies) and `vulture`
  (dead code). The spec marks both optional and non-blocking, and `vulture`
  false-positives heavily on FastAPI's dependency injection, so it is an
  occasional manual run rather than a gate.
