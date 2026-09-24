## MODIFIED Requirements

### Requirement: A tournament has a mode, and it is the only thing so called
Each tournament SHALL have a **mode** with exactly two values: **automatic**, in which Squire keeps the tournament's list of entrants — fencers register in the application and Squire manages the window, the clocks, the mail and the queue — and **manual**, in which the organizer keeps the list outside Squire and it reaches Squire by import — the only mode that imports — Squire cleaning, matching, pricing and exporting it while running nothing against it.

This SHALL be the only thing in the product called a mode. It qualifies because it is stored, has a small closed set of values, and changes what the system does. No label derived from other settings SHALL be given the name, and in particular the features fixed by `tournament-features` SHALL NOT be described as a mode however many of them are enabled.

The mode SHALL be stored as `registrations_kept_by`, whose values name who keeps the registrations rather than repeating the adjective: a stored value reading `manual` would not say manual *what*, while the surfaces an organizer reads say *režim: automatický / manuální*. The two names SHALL be understood as one setting, the way a payments column and the word *Platby* already are.

It SHALL be a property of the tournament, not of the account reading it: every member of a tournament's console team SHALL see the same mode. It SHALL NOT be derived or re-derived from the tournament's contents at any point. A tournament with imported rows and no in-app registrations SHALL NOT become manual on that evidence, and one that has been registered for SHALL NOT become automatic on that evidence; the value records what the organizer decided.

A tournament created after this capability exists SHALL be automatic unless the organizer chooses otherwise. Every tournament that existed before it SHALL be automatic, because that is what all of them were.

The mode SHALL be independent of the features fixed by `tournament-features` and of the payments setting fixed by `payments`. A manual tournament MAY collect payments and an automatic one MAY collect none; both combinations are ordinary and neither setting SHALL be inferred from the other.

#### Scenario: Stored with the tournament
- **WHEN** two organizers on one tournament's console team open its Setup phase
- **THEN** both see the same mode

#### Scenario: Not derived from contents
- **WHEN** a manual tournament holds fifty entrants all entered by hand and no imported row
- **THEN** it stays manual

#### Scenario: An automatic tournament takes no import
- **WHEN** an organizer uploads a table of fifty entrants to an automatic tournament
- **THEN** the upload is refused, the tournament stays automatic, and nothing is stored

#### Scenario: Existing tournaments are automatic
- **WHEN** a tournament that existed before this capability is read
- **THEN** it is automatic, whatever it holds

#### Scenario: Manual with payments collected
- **WHEN** an organizer sets a tournament to manual and leaves payments on
- **THEN** both settings hold, the roster arrives by import, and Squire still reconciles the tournament's bank statement

#### Scenario: The features are not a mode
- **WHEN** an organizer reads a tournament with none of the three features enabled
- **THEN** nothing describes it as being in a mode on that account, and its mode is whichever of automatic or manual it is
