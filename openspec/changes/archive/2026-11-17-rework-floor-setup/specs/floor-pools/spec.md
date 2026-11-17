## MODIFIED Requirements

### Requirement: The pools tab follows the discipline's state
The `pools` tab SHALL show the selected discipline in one of four states:
- **draw:** before the announcement (`floor-draw`);
- **running:** after the announcement, while any bout is unrecorded;
- **complete:** every bout is recorded, and the pools are not yet closed;
- **closed:** the ranking is frozen.

Each state's content replaces the previous one's. The tab itself is always present.

**A discipline that takes over.** A discipline that takes over another's pool results
(`floor-setup`) has no pools of its own. Its `pools` tab SHALL state that its pools are
taken over from the source. The statement links to the source's `pools` tab, and the
source's state is given in words.

**On `today`.** The Skupiny column of `today` SHALL state the same four states as
"čeká", "běží", "dokončeny" and "uzavřeny". A discipline that takes over reads "převzaty
z" followed by the source's name.

#### Scenario: The matrix follows the pools
- **WHEN** Sabre's draw is announced and one bout is recorded
- **THEN** Sabre's Skupiny cell on `today` reads "běží"

#### Scenario: A taken-over discipline names its source
- **WHEN** Longsword Teams takes over the pool results of Longsword Open
- **THEN** its Skupiny cell on `today` reads "převzaty z Longsword Open", and its `pools` tab links to Longsword Open's pools

### Requirement: Pool sheets list the bouts in order
Every announced pool SHALL have a sheet stating:
- its discipline and number;
- its piste and planned start, where a schedule is planned;
- the pool bout point target, where the format states one;
- its fencers;
- its bouts, in the standard order for its size.

**Printing.** Sheets SHALL print as PDF from the templates adopted from `hema-agent`.

#### Scenario: A pool of six has fifteen bouts
- **WHEN** a pool of six fencers is announced
- **THEN** its sheet lists fifteen bouts in the standard order for six

#### Scenario: The point target is on the sheet
- **WHEN** Longsword Open's format states 7 points for a pool bout
- **THEN** every Longsword Open pool sheet states the target of 7 points

#### Scenario: A sheet without a schedule
- **WHEN** "Plánovat rozvrh" is off and a pool is announced
- **THEN** its sheet states no piste and no planned start
