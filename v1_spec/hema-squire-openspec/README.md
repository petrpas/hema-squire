# HEMA Squire — OpenSpec bootstrap (pre-tournament core)

Extracted from petrpas/hema-agent (v1 Discord bot) + the owner's decisions and the approved wireframe (direction B).

Usage in a fresh repo:
1. `openspec init` (choose your tools), then copy `openspec/project.md` over the generated one and drop `openspec/changes/add-pre-tournament-core/` in place.
2. `openspec validate add-pre-tournament-core --strict`
3. Review ANALYSIS.md §4 (inferred defaults) before implementation; adjust specs where you disagree.
4. Implement via tasks.md, then `openspec archive add-pre-tournament-core` to merge deltas into `openspec/specs/`.

ANALYSIS.md is a working document, not an OpenSpec artifact — keep it at the repo root.
