## ADDED Requirements

### Requirement: HR identity in the phases after matching
On every phase after Matching — Deduplication, Payments and Export — the table's
three identity columns (name, nationality, club) SHALL state the values of the
HEMA Ratings profile the row is bound to, not the values the fencer registered
under or an import file spelled. The profile's nationality SHALL be stated as the
two-letter ISO country code, the same reading the Matching evidence register
uses, so that one identity column speaks one vocabulary down its whole length.

Where a row is bound to no profile — never matched, or resolved as having none —
those columns SHALL state the registered name, nationality and club, rendered in
italic. The italic SHALL be the whole of the marking: no dash, no badge, no
second column. A row without a profile therefore stays identifiable and stays
comparable against its neighbours, while a reader can see at a glance which lines
of the table the profile stands behind.

The identity columns SHALL be read-only on those phases, whether HR-backed or
italic. An HR-backed value belongs to the profile and is changed by rebinding the
id on Matching; a registered value is corrected where it is claimed, on the
fencer list or on Import. Identity cells SHALL remain editable on Import, on the
fencer list and on Matching, as they are today.

Matching itself SHALL keep the claim-beside-evidence layout fixed by **HR
matching review** unchanged: the registered values and the HR register are shown
side by side there, because comparing them is what the phase is for.

#### Scenario: A matched row is identified by its profile
- **WHEN** the organizer opens Deduplication on a row bound to a profile reading `Lukas Mueller`, `Germany`, `Berlin Schwert`, registered as `Lukáš Müller`, `DE`, `Berlin`
- **THEN** the row's identity columns read `Lukas Mueller`, `DE`, `Berlin Schwert`, upright

#### Scenario: An unmatched row keeps its own words
- **WHEN** the organizer opens Deduplication on a row that no profile is bound to
- **THEN** the row's identity columns state the name, nationality and club it registered under, in italic, and not an em dash

#### Scenario: One vocabulary down the identity column
- **WHEN** two matched rows sit side by side and the index spells one country in English and the other as a code
- **THEN** both nationality cells read the two-letter ISO code

#### Scenario: The same reading on every later phase
- **WHEN** the organizer moves from Deduplication to Payments and on to Export
- **THEN** each phase identifies the row the same way, HR-backed values upright and registered values in italic

#### Scenario: Identity is not rewritten after matching
- **WHEN** the organizer clicks a name, nationality or club cell on Deduplication, Payments or Export
- **THEN** no edit opens, and no field-edit rule can be created from those cells on those phases

#### Scenario: Corrections still have their place
- **WHEN** the organizer clicks the same fencer's name cell on the fencer list
- **THEN** the cell opens for editing as before, and the correction persists as a rule

#### Scenario: Matching still compares claim against evidence
- **WHEN** the organizer opens Matching on a row whose registered club differs from the matched profile's
- **THEN** both the registered values and the HR register are visible on the row at once, unchanged by this requirement

#### Scenario: Resolving a match changes how later phases read the row
- **WHEN** the organizer binds a profile to a row that had none and then opens Payments
- **THEN** the row's identity columns state the profile's values, upright, where they had been the registered ones in italic
