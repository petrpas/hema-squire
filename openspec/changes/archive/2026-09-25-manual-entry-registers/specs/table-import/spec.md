## MODIFIED Requirements

### Requirement: External table import
The organizer of a **manual** tournament MAY import an external registration table (CSV, XLSX, or Google Sheet). An import SHALL be refused on an **automatic** tournament, with a reason naming the mode: its entrants register in the application or are entered by hand, and a tournament whose list began elsewhere belongs in manual mode (`tournament-mode`). Rows an automatic tournament already holds from an earlier import SHALL be left as they are. Imported records SHALL retain provenance (source file and row) and the originally registered name (reg_name) whenever a canonical name is later applied.

#### Scenario: Legacy Google Form export
- **WHEN** the organizer imports a Google Form response sheet
- **THEN** each row becomes a fencer record traceable back to its source row

#### Scenario: Import refused on an automatic tournament
- **WHEN** a table is uploaded to an automatic tournament
- **THEN** it is refused with a reason naming the mode, and nothing is stored
