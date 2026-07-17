# ANALYSIS — extraction notes (v1 hema-agent → HEMA Squire pre-tournament spec)

Working document for the owner and future agents. Not an OpenSpec artifact — keep it out of `openspec/` or exclude it from validation.

## 1. Provenance map

| Capability | v1 source of behavior |
|---|---|
| fencer-accounts | new (replaces Google Form identity-by-string); HR binding logic from `reg_agent/step3_match.py` (fighters index, profile lookup, canonical name / `reg_name`) |
| tournament-admin | `pre_tournament/config/pre_config.py` (disciplines, `discipline_limits`, language), `setup_agent` (config wizard — retired, replaced by settings UI), discipline taxonomy from `reg_agent/models.py` (`HemaWeapon × HemaGender × HemaMaterial`) |
| registration | new mechanism; billable items and record fields from `FencerRecord` (`models.py`): disciplines, borrow, after_party, aftersparring, accommodation, notes |
| payments | replaces `step7_payments.py` + `payment_agent` (LLM matching by name/amount — **retired by design**); new VS/QR/expiry architecture per the owner's payment specification (reservation window, SPAYD QR, Fio API, ±5 % tolerance, VS-in-message for SEPA, refundable-until softening) |
| etl-console | phase structure from the reg pipeline steps 1–7; UI per approved wireframe direction B |
| edit-rules | generalizes v1's scattered persistence: `match_corrections.json`, `withdrawn.json`, memory.md files, "surgical sheet edits" — unified into one rule/replay engine |
| table-import | `step2_parse.py` (LLM parse → `FencerRecord`), `step3_match.py` (LLM fuzzy match), `step4_dedup.py` (same-id merge; three-band no-id classification: surely / likely / possible with discard of possible), incremental caching behavior |
| hr-integration | `step3_match.py` (fighters index scrape + cache), `step5_ratings.py` (dated snapshots `ratings_YYYY-MM-DD.json`; self-healing parser downgraded to drift detection) |
| data-export | `step6_upload.py` (sheet formats, preserve Reg./No., always refresh HRating/HRank, write-if-blank) |
| localization | `msgs/` EN/CS trees with fallback — inverted to CZ-first |

## 2. Deliberately dropped v1 behavior

- All Discord machinery: cogs, channels-as-state, modals, embeds, invite/role/QR onboarding, `/clear`, instance locks, typing loops.
- Conversational setup agent and reg agent (LLM dialog as UI) — replaced by forms and the console.
- LLM payment matching (`hi`/`low` confidence, name/amount heuristics) — root cause designed out via VS.
- Google Form as intake; Google Sheet as database. Sheet survives only as an export target.
- Per-tournament deployment (one Fly app per tournament) — replaced by multi-tenant single deployment.
- Seed recalculation (`recalculate_seeds`: 1..N by ascending HRank, unranked appended) — **deferred by owner (C9)**, documented here so the rule is not lost: revisit when seeding enters scope.
- `generate_social_media_list`, `set_discipline_limit` chat tools — superseded by console/admin UI.

## 3. Scope notes

- **Pool alchemy (`pool_alch_agent`)** — solver with real business rules (snake seeding, tiers, Hungarian construction, hill-climbing, club/nationality spread, wave constraint for dual-discipline fencers). The owner's scope answer covered payments explicitly and pool alchemy not at all → treated as **out of this change**, likely a future `add-pool-design` change. The rules are documented in the v1 repo; do not re-derive them.
- In-tournament and post-tournament phases: menu placeholders only.

## 4. Inferred defaults requiring owner confirmation

1. **Substitute queue**: capacity + waitlist with *manual* admission by the organizer when a spot frees. Inferred from "kdo nezaplatí … je přeskočen" + "pak jen náhradník"; automatic admission was not specified.
2. **Rule ordering**: creation order, latest-wins per field. Not specified; chosen as the least surprising default.
3. **Merge precedence** (same-hr_id dedup): most recent explicit value per field. v1 delegated this to the LLM prompt.
4. **"Deleted rule = as if it never existed"** is specified data-side, per the owner. Whether a meta-journal of rule creation/deletion is retained for accountability is left as an implementation option — the spec does not forbid it.
5. **Repeat-export surgical semantics retained** for the sheet target only, because downstream (v1 in-tournament tooling, humans filling No.) still edits sheets.
6. **Unpaid on public list**: hidden vs greyed is a per-tournament setting; no default chosen.

## 5. Open decisions (mirrored in design.md)

Foreign payment channel (VS-in-message vs Stripe/Wise); discipline taxonomy extensibility; ratings category-mapping parameter shape; reservation window defaults (7–10 d validity, reminder ~day 5); early-bird defaults.

## 6. v1 findings worth archiving (out of current scope)

From the in-tournament code review, for whenever that phase is rebuilt: bout outcome (`Win/Loss/Draw/No`) is not persisted to the verified sheet, so unplayed bouts (0:0) inflate M and distort V/M — the walkover/withdrawal rule was never defined; pool-size limits are inconsistent across the codebase (templates 4–8, validation 5–7, solver warn >7 / hard 10); fencer identity is a case-insensitive name string throughout (name collisions break stats); shared memory files leak context between agents (`setup_memory.md` read by payment agent).
