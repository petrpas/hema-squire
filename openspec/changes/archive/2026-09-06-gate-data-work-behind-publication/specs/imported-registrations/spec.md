## ADDED Requirements

### Requirement: Issuing waits for publication
Registrations SHALL NOT be issued for an imported fencer list while the tournament is
unpublished. Neither route that reaches issuing SHALL run on a draft: not the pass at
the head of a payment intake, and not the endpoint the Payments phase calls when it
opens on a tournament Squire collects nothing for.

This is stated here rather than left to follow from the console being inactive on a
draft (`tournament-publication`), because issuing is the one path by which a draft
could come to hold registrations, and because what it produces there is quietly wrong
rather than merely premature. A manual tournament issues registrations carrying no
variable symbol, correctly — Squire has told no payer a number to quote. A draft may
still change its mode, since publication is what settles it (`tournament-mode`). So a
draft that issued could become an automatic tournament holding registrations with no
symbol on a tournament whose matching resolves through them, and publication would
carry that state forward rather than catch it.

Removing the source rather than guarding the switch is deliberate: the switch is
legitimate on a draft, and it is the participants that do not belong there.

#### Scenario: No issuing on a draft
- **WHEN** the Payments phase is opened on an unpublished tournament that Squire collects nothing for, and an import has left it a fencer list
- **THEN** no registration is issued, and the fencer list is unchanged

#### Scenario: The intake pass does not issue on a draft either
- **WHEN** a payment intake is attempted on a draft
- **THEN** the intake is refused before it issues anything

#### Scenario: A draft carries no symbol-less registration into automatic mode
- **WHEN** an unpublished manual tournament holding an imported fencer list is switched to automatic and then published
- **THEN** it holds no registration, because none was issued while it was a draft

#### Scenario: Issuing runs once published
- **WHEN** that tournament is published and its Payments phase opened
- **THEN** the fencer list is issued as it is on any published tournament, each registration taking the symbol its mode calls for
