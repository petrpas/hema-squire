## 1. Taxonomy

- [x] 1.1 Add SS Single Sidesword, ST Singlestick, KN Knife, ME Messer, SM Smallsword and SD Sidesword & Dagger to `taxonomy.WEAPONS`, so that `DISCIPLINES` generates 66 codes (design D2)
- [x] 1.2 Make `parse_code` positional: material prefix, then two characters of weapon, then an optional gender character (design D1)
- [x] 1.3 `test_taxonomy.py`: round trip over every generated code, plus `SM`, `SMW` and `Plastic SMM` reading as smallsword open steel, women steel and men plastic
- [x] 1.4 Give legacy weapon-rental validation in `routers/registrations.py` its own frozen five-code set instead of `taxonomy.WEAPONS` (design D5)

## 2. HR category mapping

- [x] 2.1 Generate `DEFAULT_CATEGORY_KEYWORDS` from per-weapon (Mixed & Men's, URG & Women's) category pairs for the seven officially rated weapons, steel only, following the table in `specs/hr-integration` (design D3)
- [x] 2.2 Replace the substring match in `take_snapshot` with equality after normalization (leading `- ` dropped, `&`↔`and`, collapsed whitespace, trimmed, case-folded), applied to default and override alike (design D4)
- [x] 2.3 `test_hr_integration.py`: women's longsword reads URG when both are listed; RD reads "Rapier and Dagger"; SS and women's ST read their categories; a Messer and a plastic longsword discipline stay unrated without failure; a dashed row under a heading row matches; "Women's Steel Longsword" does not match the URG header; a double-space singlestick header matches; a lower-case override matches only the whole name. Use real HEMA Ratings header strings in fixtures.
- [x] 2.4 Check every category string in the generated mapping against a live fighter page that carries that category (the ratings table, not the page's other lists), and correct the table and the spec if HEMA Ratings prints it differently (design D3). Done 2026-10-25: official strings confirmed, leading `- ` found, side-weapon categories absent from fighter pages

## 3. Frontend

- [x] 3.1 Extend `LEGACY_WEAPONS` in `frontend/src/TournamentFace.tsx` with the six weapons and names, so the discipline dialog and setup section offer them and `disciplineName` generates their names
- [x] 3.2 Show `weaponNoRatingHint` under the weapon select when KN, ME, SM or SD is chosen (design D3a)
- [x] 3.3 Add a test that a Messer discipline gets a generated name, is not treated as a custom weapon and shows the no-ratings notice, while a typed `Tešák` still requires a name
- [x] 3.4 `npm run typecheck` and `npm run check` pass in `frontend/`

## 4. Finish

- [x] 4.1 `pytest tests/test_taxonomy.py tests/test_hr_integration.py tests/test_team_disciplines.py -q`, then the registration tests that touch weapon rentals
- [x] 4.2 `uv run ruff check .` and `uv run basedpyright` pass in `backend/`
