## Why

Organizers run disciplines that the HSQ taxonomy does not name, such as single sidesword, singlestick, knife, messer, smallsword and sidesword & dagger. Such a discipline carries no HEMA Ratings figure, even when HEMA Ratings keeps a category for it. Within the five weapons HSQ does name, the rating fetch is also quietly broken in two places:

- HEMA Ratings spells its category "Rapier and Dagger" but HSQ's keyword reads "Rapier & Dagger", so rapier & dagger never matches.
- Matching is by loose substring, so "Women's Steel Longsword" also hits "Underrepresented Genders & Women's Steel Longsword".

## What Changes

- The taxonomy gains six weapons. Two match official HEMA Ratings categories: **SS** Single Sidesword and **ST** Singlestick. Four are side weapons: **KN** Knife, **ME** Messer, **SM** Smallsword and **SD** Sidesword & Dagger. Each gets a generated name, slug and taxonomy code like the existing five.
- A taxonomy weapon code is always two characters, and the gender is the optional third. Reading a code back is positional, so a weapon code that ends in W or M (SM) is not mistaken for a gender.
- The default HEMA Ratings category mapping is restated for every taxonomy weapon:
  - Open and Men take the "Mixed & Men's" category.
  - **Women takes the "Underrepresented Genders & Women's" category, not "Women's"**. HSQ keeps three genders and adds no URG gender.
  - SS and ST map to their official categories.
  - Knife, Messer, Smallsword and Sidesword & Dagger get no default category. HEMA Ratings keeps them only as unofficial categories, which a fighter's page does not list (verified 2026-10-25). The setup console states that such a discipline carries no ratings, as it does for a custom weapon.
  - Plastic stays unmapped.
- **BREAKING (rating data):** HSQ Women in LS, SA, RA and SB now reads the URG & Women's rating where it read the Women's one. Snapshots already taken keep what they stored, and the next refresh reads the new category.
- A category is matched by whole name after normalization, not by substring. The normalization treats `&` and `and` alike, collapses runs of whitespace and ignores case. The normalization also drops the leading `- ` the fighter page prints before each category. This fixes rapier & dagger, and Women's no longer collides with URG & Women's. A per-tournament keyword override is matched the same way.
- A fully custom discipline stays as it is: a free-text weapon, a required name and no HEMA Ratings counterpart. Disciplines already stored with a free-text weapon such as "Messer" are not migrated.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `discipline-identity`: the classification requirement names eleven taxonomy weapons instead of five, and the taxonomy code requirement fixes the two-character weapon code with a positional gender.
- `hr-integration`: two added requirements. One states the default category mapping (Women → URG & Women's, no default for the side weapons or for plastic, the console notice for side weapons). The other replaces substring matching with whole-name normalized matching, for defaults and overrides alike.

## Impact

- `backend/app/taxonomy.py`: the weapon table, positional `parse_code`, and the generated names and codes (`DISCIPLINES` grows from 30 to 66 codes).
- `backend/app/hr_sync.py`: `DEFAULT_CATEGORY_KEYWORDS` is rewritten and the match becomes a normalized whole-name comparison.
- `frontend/src/TournamentFace.tsx` (`LEGACY_WEAPONS`): the weapon list the discipline dialog and the setup section offer. A set of unrated taxonomy weapons drives the no-ratings notice in `DisciplineDialog.tsx`.
- Legacy weapon-rental validation (`routers/registrations.py`) keeps accepting only the original five codes and no longer reads the taxonomy table.
- `/api/taxonomy/disciplines` returns the larger table.
- Tests: `test_taxonomy.py` (round trip over all codes, SM/SMW parsing), HR snapshot tests with real HEMA Ratings category strings (rapier and dagger, URG, double-space singlestick, the leading dash).
- No database migration. Stored disciplines keep their weapon strings.

## Follow-up

Ratings for the side weapons (and for synthetic longsword) need a different source: the per-category leaderboard page (`/periods/details/?ratingsetid=N`), which lists every rated fighter with rank and rating on one page. That is a new fetch path with its own drift check and a mapping by rating-set id, and it is left to its own change. The owner decided on 2026-10-25 that Plastic KN should take "Any Material Knife" and Plastic LS "Synthetic Longsword", and that every gender should take the single Mixed category where it is the only one. Those decisions belong to that change.
