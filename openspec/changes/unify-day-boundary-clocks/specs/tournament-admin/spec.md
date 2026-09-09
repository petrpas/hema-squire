## ADDED Requirements

### Requirement: Date-valued price thresholds are read in the tournament's zone
A price threshold expressed as a date — the tournament-wide early-bird date that
switches disciplines between their standard and early prices, and the
`registration date on or before a configured date` discount condition — SHALL be
compared against the registration's moment resolved to a day in the
**tournament's own timezone**, as `day-boundaries` fixes for every date the
organizer entered. It SHALL NOT be compared against that moment's UTC day.

A registration SHALL therefore be priced by the day it was made where the
tournament is held, so the early price runs to the end of the cutoff day there
and no longer. The same rule SHALL govern the price preview offered before
registering and the repricing a later correction performs, so a preview, the
total stored at registration, and a correction of it cannot disagree.

Totals already stored on registrations SHALL NOT be recomputed by this rule.
They are written once at registration and are not revisited except by a
correction, which reprices and records what it changed.

#### Scenario: Early bird ends at the local midnight
- **WHEN** a tournament held in a zone ahead of UTC has an early-bird date of the 20th, and a fencer registers after midnight UTC on the 21st but before midnight where the tournament is held
- **THEN** the early price applies

#### Scenario: Early bird does not outlive the local day
- **WHEN** a tournament held in a zone behind UTC has an early-bird date of the 20th, and a fencer registers after midnight locally on the 21st while it is still the 20th in UTC
- **THEN** the standard price applies

#### Scenario: Preview and stored total agree
- **WHEN** a fencer previews a selection and immediately registers it
- **THEN** the previewed total and the stored total apply the same early-bird answer

#### Scenario: A stored total is not moved by the rule alone
- **WHEN** a registration priced before this rule took effect is read
- **THEN** its stored total is unchanged
