# Spec: Static Analysis Layers for HEMA Squire

**Audience:** Claude Code, phased spec-driven implementation
**Stack:** FastAPI (Python) + React/TypeScript, uv, ruff
**Current state:** the repo runs `ruff` only (lint + format)

---

## 0. Context and philosophy

Most of the code in this repo is generated agentically. That creates a specific risk profile:
an LLM does not produce syntax errors or style violations — ruff already catches those. It
produces **hallucinated attributes, drifted signatures, silently incompatible types, and
imports of modules that do not exist**. These are precisely the failures a static type
checker catches more cheaply than any test.

The second risk is the frontend. The project owner does not write TypeScript, so there is no
human review that would catch nonsense there. `tsc` is the only line of defence and is
mandatory, not optional.

**Goal:** introduce four layers of checking, each as a separate gate in CI and in pre-commit,
so the agent sees them during its own work and fixes its own errors before committing.

### Anti-goals (read these before starting)

- **Do not introduce everything at once.** Each phase = one commit, one PR, green CI.
- **Do not fix existing errors en masse.** When the first checker run emits 300 errors, the
  answer is not 300 fixes in one commit. The answer is a scoped rollout (see Phase 2).
- **Do not raise strictness until the current level is at zero errors.**
- **No bare `# type: ignore` or `# pyright: ignore`.** Always with the specific error code and
  a one-line reason. A bare ignore silently disables the entire checker on that line.
- **Do not disable rules because many of them fire.** Disabling a rule is a decision, not
  cleanup. When you disable one, it goes in `pyproject.toml` with a comment, not in an
  inline ignore.
- **Do not configure tools from memory.** Versions and config schemas change; verify every
  tool against current documentation (see `## Version verification`).

---

## Version verification

Before writing any configuration, check current stable versions and the current shape of
each config format:

```bash
uv pip index versions basedpyright
npm view @biomejs/biome version
npm view typescript version
```

For `pre-commit` hooks use `pre-commit autoupdate` instead of hand-written `rev:` values.
For schemathesis and Biome, verify the API/config shape against the documentation — both had
breaking changes across majors, and the examples in this document are illustrative sketches,
not copy-paste truth.

---

## Phase 1 — Frontend: `tsc --noEmit` + Biome

**Why first:** highest catch-to-effort ratio. `tsc` runs against code no human reviews and
typically finds real bugs on the very first run.

### 1.1 TypeScript

1. Verify `tsconfig.json` has at minimum:

```jsonc
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,   // arrays and maps yield T | undefined
    "noImplicitOverride": true,
    "noFallthroughCasesInSwitch": true,
    "verbatimModuleSyntax": true
  }
}
```

`noUncheckedIndexedAccess` is the flag that catches the classic agentic bug
`data.items[0].name` on an empty array. Expect work after enabling it.

2. Add the npm script:

```json
"scripts": {
  "typecheck": "tsc --noEmit"
}
```

3. Run it, record the error count in the PR description, fix them. **These get fixed, not
   suppressed** — frontend type errors will number in the tens, not hundreds, and each one is
   a suspected real bug.

### 1.2 Biome

Biome replaces ESLint + Prettier with a single binary. The reason to pick Biome over ESLint
is operational: zero config archaeology, no plugin tree that breaks on the next React upgrade.

1. If ESLint/Prettier config exists in the repo, migrate it so prior decisions are not lost:

```bash
npx @biomejs/biome migrate eslint --write
npx @biomejs/biome migrate prettier --write
```

2. Enable the React hooks rules — that is the one category where ESLint historically provided
   value `tsc` does not. In `biome.json`, verify `useExhaustiveDependencies` and
   `useHookAtTopLevel` are active.

3. Scripts:

```json
"scripts": {
  "check": "biome check .",
  "check:fix": "biome check --write ."
}
```

**Acceptance criterion for Phase 1:** `npm run typecheck && npm run check` passes with zero errors.

---

## Phase 2 — Python: type checker

**Choice: `basedpyright`.** Reasons: no plugin needed for Pydantic (pyright understands
`__init__` generated via `dataclass_transform` natively), best inference on generics,
configurable per-directory, deterministic across versions. `mypy` is a legitimate
alternative if you want the ecosystem standard — then the `pydantic.mypy` plugin is required.
`ty` does not belong in this repo yet: it is on 0.0.x, ships breaking changes including
diagnostic changes between versions, and by default checks bodies of unannotated functions,
so the first run emits an order of magnitude more findings than pyright. Fine as a fast local
loop, not as a CI gate.

### 2.1 Install and base configuration

```bash
uv add --dev basedpyright
```

In `pyproject.toml`:

```toml
[tool.basedpyright]
pythonVersion = "3.12"          # match the project's actual version
include = ["src", "tests"]
exclude = ["**/__pycache__", "**/node_modules", "migrations"]
venvPath = "."
venv = ".venv"

# Starting level. Do NOT start at "strict" or "all".
typeCheckingMode = "standard"

# Domains that are finished and must stay clean get raised separately:
strict = []
```

### 2.2 Rollout procedure (this is the part that matters)

1. Run `uv run basedpyright` and **record the error count by category**:

```bash
uv run basedpyright --outputjson | jq -r '.generalDiagnostics[].rule' | sort | uniq -c | sort -rn
```

2. Sort findings into three buckets:
   - **Real bugs** — fix immediately, one at a time, with a test if it is logic.
   - **Missing annotations at boundaries** (return types, parameters) — fill them in.
   - **Noise from missing third-party stubs** — solved by configuration, not by code:

```toml
[[tool.basedpyright.executionEnvironments]]
root = "src"
reportMissingTypeStubs = "none"
```

3. **Do not raise `typeCheckingMode` globally.** Instead, add finished modules to `strict`
   incrementally:

```toml
strict = ["src/payments", "src/domain"]
```

The payments domain (variable symbols, SPAYD, Fio) is the first candidate — it is the most
critical logic in the application and belongs under the strictest mode.

4. If the error count after step 1 exceeds ~150, do not try to clean it up in one commit.
   Gate only `src/payments` and `src/domain` via `include`, leave the rest out, and widen
   `include` progressively. A baseline file of suppressed errors is the worse option — it
   grows and nobody ever prunes it.

**Acceptance criterion for Phase 2:** `uv run basedpyright` passes with zero errors over the
configured scope; the scope is documented in `pyproject.toml` with a comment stating what is
still excluded.

---

## Phase 3 — Security

Context: a prior GDPR analysis already surfaced a plaintext Fio API token in the code. This
phase is a concrete response to an existing finding, not theoretical hygiene.

### 3.1 Ruff — enable the security rulesets

Add to the existing selected rules in `pyproject.toml`:

```toml
[tool.ruff.lint]
select = [
    # ... existing
    "S",      # flake8-bandit — hardcoded secrets, unsafe subprocess, weak hashes
    "ASYNC",  # blocking calls inside async functions — a throughput killer in FastAPI
    "T20",    # print() left in production code
    "TID",    # banned relative imports across packages
]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101"]  # assert in tests is fine
```

`ASYNC` deserves particular attention: LLM-generated FastAPI code routinely calls synchronous
`requests` or blocking file I/O inside an `async def` endpoint. Ruff finds this statically.

### 3.2 gitleaks

```yaml
# .pre-commit-config.yaml (fragment)
- repo: https://github.com/gitleaks/gitleaks
  hooks:
    - id: gitleaks
```

After adding it, scan the **full history**, not just the working tree:

```bash
gitleaks detect --source . --log-opts="--all"
```

The repo is public. If the scan finds the Fio token in history, deleting it from HEAD is not
enough — the token must be rotated at the bank. History rewriting (`git filter-repo`) is a
second step at best and resolves nothing on its own, because forks and caches persist.

### 3.3 Dependency audit

```bash
uv add --dev pip-audit
uv run pip-audit
npm audit --audit-level=high
```

Wire this into CI as a **non-blocking** job (`continue-on-error: true`) that only reports. A
blocking audit means a random CVE in a transitive dependency breaks your deploy at the worst
possible moment.

**Acceptance criterion for Phase 3:** ruff passes with `S` and `ASYNC`; gitleaks clean on the
working tree; history findings documented in an issue with a rotation decision.

---

## Phase 4 — Schemathesis against OpenAPI

This is not linting, but it fits the existing property-based approach (Hypothesis) and does
not count against the 40 hand-written test cap — it is a single file generating hundreds of
cases from the OpenAPI schema FastAPI already publishes.

Schemathesis fuzzes endpoints and verifies that:
- responses conform to the declared schema,
- the server does not return 500 on inputs valid per the schema,
- nothing breaks on edge values (empty strings, unicode, extreme numbers).

```bash
uv add --dev schemathesis
```

Integration sketch — **verify the current API shape in the docs**, it changed across majors:

```python
# tests/test_api_contract.py
import schemathesis
from src.main import app

schema = schemathesis.openapi.from_asgi("/openapi.json", app)

@schema.parametrize()
def test_api_contract(case):
    case.call_and_validate()
```

Set a sane example limit so CI does not run forever (Hypothesis profile, roughly 20–50
examples per endpoint). Endpoints with side effects (submitting a payment, deleting an
account) should be either excluded or run against an isolated test database.

**Acceptance criterion for Phase 4:** the contract test runs in CI against an
in-memory/test database and is green.

---

## Phase 5 — Optional, only once everything above is green

- **`deptry`** — finds dependencies declared in `pyproject.toml` that are never imported, and
  imports that are not declared. On a repo where an agent added the packages, it typically
  finds 3–5 redundant ones.
- **`vulture`** — dead code. High false-positive rate on FastAPI (dependency injection, event
  handlers), so use it as an occasional manual run, not a CI gate.

---

## Integration: pre-commit

The point is for the agent to see errors immediately and fix them itself, rather than
discovering them in CI.

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    hooks:
      - id: ruff-check
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/gitleaks/gitleaks
    hooks:
      - id: gitleaks

  - repo: local
    hooks:
      - id: basedpyright
        name: basedpyright
        entry: uv run basedpyright
        language: system
        types: [python]
        pass_filenames: false

      - id: tsc
        name: tsc --noEmit
        entry: npm run --prefix frontend typecheck
        language: system
        files: \.(ts|tsx)$
        pass_filenames: false

      - id: biome
        name: biome check
        entry: npm run --prefix frontend check:fix
        language: system
        files: \.(ts|tsx|js|jsx|json)$
        pass_filenames: false
```

Fill in `rev:` values via `pre-commit autoupdate`; do not edit them by hand.
`pass_filenames: false` on the type checkers is deliberate — type-checking a single file in
isolation is meaningless, the checker needs the whole project.

---

## Integration: CI

```yaml
# .github/workflows/checks.yml
name: checks
on: [push, pull_request]

jobs:
  python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync --all-extras --dev
      - run: uv run ruff check .
      - run: uv run ruff format --check .
      - run: uv run basedpyright
      - run: uv run pytest

  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm
      - run: npm ci
      - run: npm run typecheck
      - run: npm run check

  audit:
    runs-on: ubuntu-latest
    continue-on-error: true
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv run pip-audit
```

The jobs are deliberately separated: when the frontend breaks, you still want the Python
result, not just the first failure.

---

## Integration: Claude Code hooks

So the agent fixes errors while working rather than at the end. Verify the current hook schema
against the Claude Code documentation — the config shape changes.

```jsonc
// .claude/settings.json (fragment)
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "uv run ruff check --fix $CLAUDE_FILE_PATHS 2>&1 | tail -20"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "uv run basedpyright 2>&1 | tail -30"
          }
        ]
      }
    ]
  }
}
```

The split is deliberate: fast per-file work (ruff) on `PostToolUse`, slower project-wide work
(basedpyright, tsc) on `Stop`, so there is no wait after every single edit.

---

## Documentation for the agent

Add a section to `CLAUDE.md` so the agent stops writing code the checkers immediately reject:

```markdown
## Code checks

Before finishing a task, all of these must pass:
- `uv run ruff check . && uv run ruff format --check .`
- `uv run basedpyright`
- `npm run typecheck && npm run check` (frontend)

Rules:
- Annotate return types on all public functions.
- Never write a bare `# type: ignore` — always `# pyright: ignore[specificCode]  # reason`.
- No blocking I/O inside `async def` (`requests`, `open()`, `time.sleep`).
- Do not work around a checker error by casting to `Any`; fix the type.
```

---

## Order summary

| Phase | Content | Blocking in CI | Effort estimate |
|-------|---------|----------------|-----------------|
| 1 | `tsc --noEmit` + Biome | yes | 1–3 h, depending on findings |
| 2 | basedpyright, scoped rollout | yes | 2–6 h |
| 3 | ruff `S`/`ASYNC`, gitleaks, audit | yes / audit no | 1–2 h + token rotation |
| 4 | schemathesis | yes | 1–2 h |
| 5 | deptry, vulture | no | optional |

Each phase is its own PR. Do not start Phase 2 until Phase 1 is green.
