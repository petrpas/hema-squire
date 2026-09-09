# Squire UI — design prohibitions

Full design spec: `openspec/squire-design-spec.md` ("Bureau 1952"). This section
(copied from spec section 8) is binding for all Squire frontend work regardless
of what else is in context.

This list takes precedence over everything else. The implementation NEVER uses:

- gradients, shadows (`box-shadow`, `text-shadow`), blur, glow
- zebra stripes in tables
- `border-radius` > 2px (no pills, no rounded cards)
- pure white `#FFF` or pure black `#000`
- default blue links or the browser's default blue focus outline
- emoji or filled icons
- skeleton shimmer, spinners, animated progress bars
- toasts with entrance animations; confirmations are static and leave via
  fade-out
- weight 600+, Title Case, exclamation marks in system copy
- more than one saturated color (`--stamp` is the only one)
- any hex value outside `tokens.css`

# Frontend conventions

Components live one per file; a file approaching ~300 lines should be split
along component seams. Panels composed of sections keep the orchestrator thin
and give each section its own file under a directory named after the panel
(see `frontend/src/setup/`).

Navigation lives in the route table in `App.tsx`; no screen owns navigation
callbacks as props. A path is never spelled out twice — build it from the
functions in `routes.ts` (`home`, `detail`, `picker`, `consolePath`, `admin`,
`profile`) whether navigating with `<Link>` or `navigate()`.

## Running tests

Default invocation inside an agent loop:

    pytest <scope> -q --maxfail=3 --tb=short --show-capture=no

- Scope to what changed (`tests/payments`, `tests/registration`). The full suite belongs to CI
  and the pre-push hook, not to a per-edit hook.
- Never pass `--cov` during the loop. Coverage reports are for CI.
- On failure: triage with `--tb=line`, then re-run the single failing test with `--tb=long`.
  Do not dump multiple full tracebacks at once.
- Hypothesis: use `--hypothesis-profile=dev` (max_examples=20). The `ci` profile runs the
  full budget.
- The OpenSpec spec is the source of truth for behavior; tests are its encoding. Read the
  spec before reading test files to infer intent.

### Writing tests

A new test must assert a behavioral invariant or a contract boundary. Do not write tests for
framework guarantees (Pydantic validation, SQLAlchemy defaults, FastAPI route registration),
trivial accessors, or the shape of mock call arguments.

# Code checks

Frontend work is finished only when both of these pass, from `frontend/`:

    npm run typecheck    # tsc --noEmit
    npm run check        # biome check .

`npm run check:fix` applies the safe fixes and the formatting. Both run in CI
alongside `npm test` and `npm run build`.

Rules:
- Never write a bare suppression. A Biome one is
  `// biome-ignore lint/<group>/<rule>: <reason>` on the line above the thing it
  suppresses — which for a JSX attribute finding is the attribute, not the
  element — and it must be a single comment line, since a second `//` line above
  it breaks the attachment.
- Disabling a rule is a decision and belongs in `biome.jsonc` with a comment
  saying why, never in a scatter of inline ignores.
- `noUncheckedIndexedAccess` is on: `array[i]` and `record[key]` are
  `T | undefined`. Narrow them; do not cast the undefined away.
- `!` is off in application code and allowed in `*.test.ts(x)`.
- A dialog is `Modal` (`src/Modal.tsx`), never a div wearing a click handler.

Backend work is finished only when both of these pass, from `backend/`:

    uv run ruff check .
    uv run basedpyright   # standard mode over `app/`

Both run in CI alongside `uv run pytest`.

Rules:
- Annotate return types on public functions.
- Never write a bare `# type: ignore` or `# pyright: ignore`. It is always
  `# pyright: ignore[specificCode]` with a comment saying why, and it goes on
  the line the checker reports — for a wrapped call, the argument's line, not
  the call's.
- Do not work around a checker error by casting to `Any` or widening a
  parameter to `object`. Narrow the value, make the function generic, or state
  the precondition the callers already hold.
- `app/` and `../scripts/` are the gated scope. `tests/` and `alembic/` are
  excluded in `pyproject.toml`, which says why; do not widen `include` without
  clearing the findings that come with it.
- A column typed `Mapped[X | None]` is `X | None` at every read. Where a guard
  earlier in the request already settled it, bind the narrowed value to a local
  and use that, rather than re-reading the attribute.
- No blocking I/O inside an `async def` — no `requests`, no bare `open()`, no
  `time.sleep`. Ruff's `ASYNC` rules gate this.
- No `assert` in `app/`. `-O` strips it, and every one of these guards is
  load-bearing; raise instead. `assert` in `tests/` is fine and expected.
- Never commit a database dump or a `.env`. `.gitignore` covers both and
  gitleaks gates the history, including a rule for the password-hash shape
  `auth.hash_password` emits.
- A module the backend imports is declared in `pyproject.toml` by its own name,
  never left to arrive as another package's extra. `uv run deptry .` answers
  whether that still holds.

Two more checks report without gating, because neither can be trusted to be
right without a human reading the answer:

    uv run deptry .    # declared-but-unimported, imported-but-undeclared
    uv run vulture     # dead code; see the [tool.vulture] comment first

`deptry` runs in CI's non-blocking `audit` job, so a dependency change that
does not match the imports is visible without breaking a deploy. `vulture` runs
nowhere but by hand — after deleting a feature is when it has something to say.

# Openspec

`openspec/changes/archive/` is superseded history, not current behavior. The authoritative
state lives in `openspec/specs/`. Do not consult the archive unless explicitly asked to
reconstruct why a past decision was made.
