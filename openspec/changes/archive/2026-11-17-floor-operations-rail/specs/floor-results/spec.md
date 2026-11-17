## MODIFIED Requirements

### Requirement: The results tab shows, exports and prints
The `results` tab SHALL show the final standing of the discipline current in its
discipline strip (`floor-console`, Step tabs choose their discipline by tabs, kept
across the console). The standing gives each entrant's name, club and nationality. It
states whether the standing is published or still waiting.

**Export.** The tab's operations panel SHALL export the current discipline as CSV:
- the standing;
- every bout of the discipline, with its pool or round, both entrants, the scores and
  the outcomes.

**Print.** The operations panel SHALL print the standing as PDF.

**The gate.** Publishing and withdrawing the standing are actions of the same panel
(Publishing results is a gate).

#### Scenario: Bouts are exported
- **WHEN** the organizer opens `results` at Sabre and exports its bouts from the operations panel
- **THEN** the CSV lists every pool and elimination bout with both entrants, scores and outcomes

#### Scenario: One discipline at a time
- **WHEN** the organizer opens `results` at Sabre on a tournament with three disciplines
- **THEN** only Sabre's standing is shown, and its export, print and publish gate stand in the panel titled "Operace · Výsledky"
