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

# Openspec

`openspec/changes/archive/` is superseded history, not current behavior. The authoritative
state lives in `openspec/specs/`. Do not consult the archive unless explicitly asked to
reconstruct why a past decision was made.
