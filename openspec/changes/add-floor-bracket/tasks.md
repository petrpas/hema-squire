## 1. Engine

- [x] 1.1 `app/floor/engine/bracket.py`: seeding order, byes, advancement targets, the third place and the team seeding rule: average place of the best k members (D3).
- [x] 1.2 `tests/floor/test_floor_bracket_engine.py`:
  - the order matches the adopted templates for every supported size;
  - Hypothesis: seeds 1 and 2 are always in opposite halves, and the byes are exactly
    the top P − A seeds.

## 2. Storage and service

- [x] 2.1 `app/floor/models.py`: `floor_brackets` and `floor_bracket_slots`, plus the bracket columns on `floor_bouts`. Add migration `floor_0005` and the classifications.
- [x] 2.2 `app/floor/bracket.py`:
  - propose and confirm (gate);
  - record with advancement in one transaction;
  - walkovers;
  - the draw refusal;
  - the correction refusal;
  - the third place;
  - closing.
- [x] 2.3 Register the Pavouk step states, the gate hooks and the progress.
- [x] 2.4 The ring screen serves elimination bouts: extend `ring.py`'s current-work query.
- [x] 2.5 Bracket PDF and PNG through Typst from the adopted templates.
- [x] 2.6 `tests/floor/test_floor_bracket.py`: one test per `floor-bracket` scenario.

## 3. Frontend

- [ ] 3.1 `frontend/src/floor/bracket/`: the proposed bracket and confirm, the bracket view with recording and correction, team matches and the print link.
- [ ] 3.2 Add tests and the i18n strings.

## 4. Acceptance

- [ ] 4.1 `pytest tests/floor -q` passes. `ruff`, `basedpyright` and the boundary test pass.
- [ ] 4.2 `npm run typecheck`, `npm run check` and `npm test` pass.
- [ ] 4.3 `openspec validate add-floor-bracket --strict` passes.
