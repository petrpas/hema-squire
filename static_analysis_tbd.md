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

## 3. ~~Tests and scripts are outside the basedpyright gate~~ — both are in

The 81 findings widening would once have added are gone and `include` is now
`["app", "../scripts", "tests"]`; only `alembic/` stays outside. It went in
three parts, and the middle one changed what the last one had to be.

**48 mechanical** — unnarrowed `session.scalar` / `Session.get` results, a
nullable `paid_at`, openpyxl's optional `Workbook.active`, four annotations.
Two were real bugs in `scripts/seed_demo.py`.

**7 deliberate wrong types** — `_Int(value="4")` passes a string to a
`TolerantInt`, which is the point of the test. Not suppressed: they go through
`model_validate({"value": "4"})`, which takes the raw mapping and is the path a
JSON body actually travels. No ignore, and a truer test.

**26 fakes handed to functions typed against the real models.** The note
predicted protocols at those seams. That turned out to be wrong, and the reason
is worth keeping: a `Protocol` matches a Pydantic model (which is why
`_TeamEntry` works) but not a declarative one — basedpyright compares the
declared `Mapped[int]`, not the `int` an instance yields, so every ORM-backed
seam fails the protocol. The answer was smaller and better: a declarative model
constructs perfectly well with no session, so `StubRule`, `FakeTournament`,
`FakeRegistration` and two `SimpleNamespace` literals became `Rule()`,
`Tournament()` and `Registration()` with the fields each test cares about.
`app/` did not change at all, and the tests now break when a field they name is
renamed — which is what the stand-ins had quietly stopped doing.

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

- ~~**`ruff-format` is not adopted.**~~ — adopted. The note said 38 files; by
  the time it was done it was 140 of 193 (`app/` 39, `tests/` 73, `alembic/`
  28), which is what deferring a formatter costs — the number only ever grows,
  because nothing checks it. One formatting-only commit, its hash in
  `.git-blame-ignore-revs` beside Biome's, then `ruff format --check` in CI and
  `ruff-format` in `.pre-commit-config.yaml`. This closes the last item of the
  spec's `Integration: CI` section.
- **`ValidationErrorResponse.detail` is a three-way union.** The envelope, a
  bare string, and an arbitrary diagnostic dict — the incomplete migration
  `app/errors.py` describes in its module docstring. A union that says "one of
  these" is weak, but it is true, and the single array FastAPI used to promise
  was not. As router codes move into `_ROUTER_CODE_FIELDS` the last two shapes
  go with them and the published schema gets simpler.
- ~~**Phase 5** — `deptry` and `vulture`~~ — done, and neither became a gate.

  `deptry` found two real ones: `app/llm.py` imports `anthropic` and
  `app/routers/tournaments.py` imports `PIL`, while both arrived only as
  extras of other packages (`pydantic-ai-slim[anthropic]`, `qrcode[pil]`).
  Both are now declared directly. The other fourteen findings were import-name
  mismatches and four dependencies nothing imports on purpose — pydantic's
  `EmailStr` validator, FastAPI's multipart parser, the zone database and the
  server — and are configured in `pyproject.toml` rather than fixed.

  `vulture` found one: `statements.NoStatementParserError`, raised by nothing
  since the router answered the case with a 409 instead. Deleted. Getting to
  that one finding took the decorator list now in `[tool.vulture]`; without it
  the run is 211 lines, ~100 of them handler parameters named `request`.
