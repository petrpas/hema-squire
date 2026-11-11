## MODIFIED Requirements

### Requirement: Global prohibitions
The implementation SHALL NOT use: gradients, `box-shadow`/`text-shadow`, blur, or glow; zebra-striped tables; `border-radius` greater than 2px, EXCEPT through the skin geometry tokens `--radius-card`, `--radius-pill`, `--radius-plate` and `--radius-chip`, which are 2px in the day skin and larger only under `[data-skin="night"]`; pure `#FFF` or `#000`; default browser blue links or blue focus outlines; emoji or filled icons; skeleton shimmer, spinners, or animated progress bars; toast entrance animations; font weight 600+, EXCEPT `--weight-display` on display headings, which is 500 in the day skin and 700 only under `[data-skin="night"]`; Title Case or exclamation marks in system copy; more than one saturated color (`--stamp` is the only one, in either skin); or any hex value outside `tokens.css`, EXCEPT a national flag stating a nationality on the public entrants roster (`public-entrants`).

`--radius` itself stays 2px in both skins: form fields, tags and table cells keep it, and only cards, pills, plates and status chips round. Everything else on this list binds both skins. A small solid dot marking a status beside its words is a mark, not an icon, and is not a filled icon.

A national flag on the public entrants roster is a picture of a country, not a color of the system: its colors are the country's, it is exempt from the one-saturated-color rule and from the hex rule, and from nothing else. It casts no shadow, rounds no more than `--radius`, and is never an emoji. The carve-out names that one place; a flag anywhere else is a second saturated color.

#### Scenario: Auditing any screen against the prohibition list
- **WHEN** any Squire screen is inspected
- **THEN** none of the prohibited patterns (gradients, shadows, zebra stripes, radius > 2px outside the skin geometry tokens, pure white/black, blue links, emoji/filled icons, shimmer/spinners, toast entrance animation, weight 600+ outside `--weight-display`, Title Case, exclamation marks, a second saturated color, hex outside `tokens.css`) are present

#### Scenario: The carve-outs do not reach the day
- **WHEN** an organizer screen is inspected
- **THEN** no element has a radius above 2px and no text is heavier than 500, the skin tokens resolving to their day values

#### Scenario: The carve-outs do not reach a literal
- **WHEN** the stylesheet is searched for a `border-radius` or `font-weight` value
- **THEN** every radius above 2px and every weight above 500 is read through a skin token, never written as a literal

#### Scenario: A flag outside its carve-out
- **WHEN** a screen other than the public entrants roster is inspected
- **THEN** no national flag is drawn on it
