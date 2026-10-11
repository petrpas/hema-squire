## ADDED Requirements

### Requirement: A logo's hue band is recorded on upload
When a logo is uploaded the system SHALL derive and store the logo's hue band, one of `blue`, `green` or `warm`, or none. The band is read from the logo's opaque pixels whose color is saturated and neither near-white nor near-black; each such pixel votes for the band its hue falls in, weighted by its saturation, and the band with the greatest weight wins. Hues from cyan through violet are `blue`, from yellow-green through teal are `green`, and the rest — magenta, pink, red, orange and yellow — are `warm`. Where such pixels make up less than a tenth of the opaque pixels, the logo is achromatic and the band is none.

Deleting the logo SHALL clear the band. A logo stored before this requirement SHALL have its band derived once from the stored image. The band SHALL be carried on each entry of the public tournament list; it states a property of a public image and nothing about any caller.

#### Scenario: A green crest
- **WHEN** an organizer uploads a logo that is mostly a saturated green shield on a transparent ground
- **THEN** the tournament's logo band is `green`

#### Scenario: A red logo is warm
- **WHEN** the uploaded logo is mostly saturated red on white
- **THEN** the band is `warm`, the white ground having cast no vote

#### Scenario: A black-and-white logo
- **WHEN** the uploaded logo is black lettering on white with no saturated pixels
- **THEN** no band is stored

#### Scenario: Logo removed
- **WHEN** the organizer deletes the logo
- **THEN** no band is stored
