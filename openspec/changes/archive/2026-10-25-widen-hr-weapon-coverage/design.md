## Context

The taxonomy in `backend/app/taxonomy.py` names five weapons, and the frontend mirrors them in `LEGACY_WEAPONS` (`frontend/src/TournamentFace.tsx`). `hr_sync.DEFAULT_CATEGORY_KEYWORDS` maps the steel open, men and women codes of those five weapons to a substring of a HEMA Ratings category header. The match is `keyword.lower() in header.lower()`, and it takes the first hit.

A live fighter page (`/fighters/details/10/`, fetched 2026-10-25) shows the ratings table naming categories as the rating-set select does: "Mixed & Men's Steel Rapier and Dagger" and "… Sword and Buckler". Other lists on the same page use "&". Two failures follow:

- The RD keyword ("… Rapier & Dagger") never matches.
- "Women's Steel Longsword" is a substring of "Underrepresented Genders & Women's Steel Longsword".

`taxonomy.parse_code` strips a trailing W or M as the gender. Its only caller is `export_json.py` (pre-migration export documents), plus the round-trip test.

`routers/registrations.py` validates legacy `weapon_rentals` against `taxonomy.WEAPONS`.

## Goals / Non-Goals

**Goals:**
- Add SS, ST, KN, ME, SM and SD as taxonomy weapons with generated names, slugs and codes.
- Restate the default HEMA Ratings mapping per `specs/hr-integration`: Women → URG, SS and ST mapped, the side weapons stated as unrated.
- Make matching a whole, normalized name comparison.

**Non-Goals:**
- A URG gender in HSQ.
- An organizer-facing UI for `hr_category_map`. It stays API-only, as today.
- Rewriting stored disciplines whose free-text weapon names a weapon that now has a code.
- Ratings for plastic codes, and for the side weapons, whose categories are unofficial and absent from fighter pages (proposal, Follow-up).

## Decisions

**D1. Two-character weapon codes, positional parse.** `parse_code` takes the material prefix, then two characters of weapon, then an optional single gender character. The alternative was picking codes that avoid a trailing W or M (`SMS`, `SX`). That leaves the parse rule fragile for every future weapon. The positional rule costs nothing for the five existing codes, which all have two characters already. A pre-split export document can carry a typed weapon as its code (`Messer`, `MesserW`). So the positional reading applies only when the first two characters are a taxonomy weapon and the remainder is a gender or nothing. Any other code keeps the trailing-W/M reading it has today.

**D2. Weapon names in English, as the existing five are.** The names are "Single Sidesword", "Singlestick", "Knife", "Messer", "Smallsword" and "Sidesword & Dagger". Generated names follow the existing pattern, e.g. "Messer Women" and "Knife Open (Plastic)". The owner chose "Messer" over "Tesák".

**D3. The default mapping is a table keyed by taxonomy code, built from rules rather than typed out.** `DEFAULT_CATEGORY_KEYWORDS` is generated from a per-weapon `(mixed_mens, urg_women)` pair for the seven officially rated weapons, steel only. Gender then picks the column: Open and Men take the first, Women the second. KN, ME, SM and SD have no pair, so their codes are absent from the table and fall through to "no category", the same path as a custom weapon. The category strings are the ones the fighter pages' ratings tables print, verified against live pages on 2026-10-25. A fighter's page lists only official categories: the top-ranked fighter of the Messer, knife and synthetic-longsword rating sets showed none of them. So the side weapons cannot be rated from that page (proposal, Follow-up).

**D3a. The no-ratings notice for a taxonomy weapon.** The frontend keeps the set of unrated taxonomy weapons (`KN`, `ME`, `SM`, `SD`) beside `LEGACY_WEAPONS`. The discipline dialog shows the existing `weaponNoRatingHint` under the weapon select when one of them is chosen, as it already does under the custom-weapon input. A per-gender rule is not needed, since no taxonomy weapon is rated in some genders and not others.

**D4. Match = equality after normalization.** `normalize(s)` removes a leading `- ` (every category row on the fighter page carries one, under a bare weapon heading row), lowercases the string, replaces `&` with `and`, collapses whitespace runs and strips the ends, and is applied to both sides. The first header that compares equal wins. Equality makes order irrelevant, because two distinct HEMA Ratings categories never normalize to the same string. The alternative was keeping substring matching with longest-match-first. It would fix URG, but any override that is a prefix of another category would keep the ambiguity. Overrides go through the same function. An override the organizer typed as a fragment ("Longsword") will stop matching, which is accepted: the field holds a category name.

**D5. Legacy rentals keep their own frozen set.** Weapon-rental validation gets its own constant holding the original five codes, instead of reading `taxonomy.WEAPONS`. Legacy rentals are a closed historical feature (registration spec: no rental row is synthesized), and widening the taxonomy should not widen what an old-style registration payload accepts.

**D6. No data migration.** Stored disciplines keep their weapon strings (owner decision). A stored free-text weapon that happens to equal a new code (`SS`, `KN`, …) would start reading as a taxonomy weapon. That is acceptable, since the organizer's meaning is the same weapon. Existing snapshots keep what they stored (`specs/hr-integration`), so no snapshot is rewritten.

## Risks / Trade-offs

- **Women's ratings shift for existing tournaments on the next refresh.** A fencer with a Women's rating but no URG rating would lose a figure. → URG & Women's is the broader set, so this should not happen in practice. Typed corrections survive refreshes anyway (`export-tables`).
- **Overrides typed as fragments stop matching.** → No UI writes overrides today. The decision is noted here so that a later UI offers category names from a list.
- **The frontend duplicates the weapon list** (`LEGACY_WEAPONS`). → It is extended in the same change, in the one place the duplication is documented (`TournamentFace.tsx`). The frontend `disciplineName` test covers a new weapon so that a missed entry shows.

## Migration Plan

Deploy as one release. No schema change and no data change. A rollback restores the old mapping, and snapshots taken in between keep whatever they stored.
