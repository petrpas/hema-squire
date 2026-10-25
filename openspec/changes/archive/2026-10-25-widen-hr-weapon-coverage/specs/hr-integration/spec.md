## ADDED Requirements

### Requirement: Default rating category mapping
Every taxonomy code SHALL have a default HEMA Ratings category, or none, that applies wherever the tournament configures no override for that code. A fighter's page lists only HEMA Ratings' official categories, so a default SHALL name an official category. The defaults SHALL follow these rules:

- **Open and Men** SHALL take the weapon's "Mixed & Men's" category.
- **Women** SHALL take the weapon's "Underrepresented Genders & Women's" category, not its "Women's" category. HSQ offers no gender of its own for underrepresented genders.
- **Knife, Messer, Smallsword, and Sidesword & Dagger** have HEMA Ratings categories only among the unofficial ones, which a fighter's page does not list. They SHALL have no default category in any gender or material.
- Every **plastic** code SHALL have no default category.

| Weapon | Open, Men | Women |
|---|---|---|
| LS | Mixed & Men's Steel Longsword | Underrepresented Genders & Women's Steel Longsword |
| SA | Mixed & Men's Steel Sabre | Underrepresented Genders & Women's Steel Sabre |
| RA | Mixed & Men's Steel Single Rapier | Underrepresented Genders and Women's Steel Single Rapier |
| RD | Mixed & Men's Steel Rapier and Dagger | Underrepresented Genders and Women's Steel Rapier and Dagger |
| SB | Mixed & Men's Steel Sword and Buckler | Underrepresented Genders & Women's Steel Sword and Buckler |
| SS | Mixed & Men's Steel Single Sidesword | Underrepresented Genders & Women's Steel Single Sidesword |
| ST | Mixed & Men's  Singlestick | Underrepresented Genders & Women's  Singlestick |
| KN, ME, SM, SD | none | none |

Where the organizer configures a discipline whose weapon is a taxonomy weapon with no default category in any gender (KN, ME, SM, SD), the console SHALL state at the point of configuration that the discipline will carry no ratings, as it does for a weapon outside the taxonomy.

A snapshot already stored SHALL keep the ratings it stored. A changed default SHALL take effect from the next refresh.

#### Scenario: Women read the URG category
- **WHEN** a snapshot is taken for a women's longsword discipline and the fencer's page lists both "Women's Steel Longsword" and "Underrepresented Genders & Women's Steel Longsword"
- **THEN** the stored rating and rank are the ones from "Underrepresented Genders & Women's Steel Longsword"

#### Scenario: Rapier and dagger rated
- **WHEN** a snapshot is taken for an open rapier & dagger discipline and the fencer's page lists "Mixed & Men's Steel Rapier and Dagger"
- **THEN** the fencer's rapier & dagger rating and rank are stored

#### Scenario: New official weapons rated
- **WHEN** a snapshot is taken for an open single sidesword discipline and a women's singlestick discipline
- **THEN** they read "Mixed & Men's Steel Single Sidesword" and "Underrepresented Genders & Women's  Singlestick"

#### Scenario: Side weapon unrated without failure
- **WHEN** a snapshot is taken for a Messer discipline with no override configured
- **THEN** that discipline contributes no ratings, the snapshot completes normally, and no failure is reported

#### Scenario: Side weapon's absence stated up front
- **WHEN** the organizer chooses Knife, Messer, Smallsword, or Sidesword & Dagger as a discipline's weapon
- **THEN** the console states that the discipline will carry no HEMA Ratings figures

#### Scenario: Plastic stays unrated
- **WHEN** a snapshot is taken for a plastic longsword discipline with no override configured
- **THEN** that discipline contributes no ratings and no failure is reported

#### Scenario: Earlier snapshot untouched
- **WHEN** a tournament holds a snapshot taken before this mapping took effect
- **THEN** that snapshot still states the ratings it stored, and only a refresh stores ratings read under the new mapping

### Requirement: Category matched by whole normalized name
A fencer's rating category SHALL be found by comparing the whole category name on the fighter's page with the category configured for the taxonomy code, whether that category is a default or an organizer's override. A configured name that appears only inside a longer category name SHALL NOT match. Before the comparison both names SHALL be normalized: a leading list dash (`- `, which the fighter page prints before every category under its weapon heading) is removed, `&` and the word `and` are treated as the same, runs of whitespace collapse to one space, leading and trailing whitespace is removed, and case is ignored. HEMA Ratings spells categories inconsistently ("& Women's" beside "and Women's", a doubled space in Singlestick), and the normalization makes those spellings match without letting one category match another. A weapon heading row (`Longsword`) SHALL match no configured category unless the configured category is that bare heading.

#### Scenario: Women's does not match the URG category
- **WHEN** the configured category is "Women's Steel Longsword" and the fencer's page lists only "Underrepresented Genders & Women's Steel Longsword"
- **THEN** no rating is stored for that code

#### Scenario: Ampersand and "and" match
- **WHEN** the configured category is "Mixed & Men's Steel Rapier & Dagger" and the fencer's page lists "Mixed & Men's Steel Rapier and Dagger"
- **THEN** the rating is stored

#### Scenario: Listed category matches through its dash
- **WHEN** the fencer's page lists "- Mixed & Men's Steel Longsword" under the heading "Longsword"
- **THEN** it matches the configured "Mixed & Men's Steel Longsword"

#### Scenario: Doubled space matches
- **WHEN** the fencer's page lists "Mixed & Men's  Singlestick" with two spaces and the configured category is "Mixed & Men's Singlestick"
- **THEN** the rating is stored

#### Scenario: Override matched the same way
- **WHEN** the organizer overrides longsword with "mixed & men's steel longsword" in lower case
- **THEN** it matches the page's "Mixed & Men's Steel Longsword", and does not match any longer category that contains it
