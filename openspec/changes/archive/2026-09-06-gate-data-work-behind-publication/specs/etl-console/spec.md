## ADDED Requirements

### Requirement: The console states what it is waiting for on a draft
On an unpublished tournament every phase the tournament's settings offer SHALL still be
drawn, in its fixed place in the phase order, and none of them SHALL act. Each such
phase SHALL state, in place of its own body, that the work it holds begins at
publication.

Drawn rather than hidden, because a tab that vanishes teaches nothing about when it
returns, and "where did Import go?" is a question the surface raises and should
therefore answer. The console has settled this twice already: the Payments phase on a
tournament Squire collects nothing for is boned out rather than removed, and a
published tournament's mode is stated rather than hidden.

The statement SHALL be made once per phase, in the phase's body. It SHALL NOT be
repeated on the tab, on each panel, or beside each control the phase would otherwise
offer: a phase whose five panels each explain the same wait states it four times too
often.

Setup SHALL be exempt and SHALL behave exactly as it does on a published tournament,
being what a draft is for.

The phase order, which phases the settings offer, and the URL a phase is addressed by
SHALL be unaffected by publication. A draft's phase is reachable, states its wait, and
becomes the phase it always was when the tournament is published — what publication
changes is the body, never the strip.

#### Scenario: A draft's phases are present and inactive
- **WHEN** an organizer opens the console of a draft
- **THEN** every phase its settings offer appears in the usual order, and each one other than Setup states that its work begins at publication instead of showing its table, panels or controls

#### Scenario: Setup is untouched
- **WHEN** the organizer opens Setup on that draft
- **THEN** the configuration forms and the completeness checklist are shown and save as usual

#### Scenario: The wait is stated once
- **WHEN** the organizer opens the Payments phase of a draft, which on a published tournament carries five views and a table
- **THEN** the phase states its wait once, rather than once per view

#### Scenario: A phase is addressable on a draft
- **WHEN** the organizer opens a URL naming the Matching on HR phase of a draft
- **THEN** the console opens on that phase and states its wait, rather than redirecting to the default phase

#### Scenario: Publication turns the phases on
- **WHEN** the draft is published and the organizer returns to the console
- **THEN** every phase shows its own body, with no phase having moved or changed its address

### Requirement: Manual entry of a fencer waits for publication
Entering a fencer by hand SHALL be refused on an unpublished tournament, and the
control that offers it SHALL NOT be presented there.

It is the one path by which a participant could reach a tournament without an import
or an in-app registration, so leaving it open would defeat the rule by the least
visible route available (`tournament-publication`).

#### Scenario: No hand entry on a draft
- **WHEN** the organizer opens the Fencers phase of a draft
- **THEN** the phase states its wait and offers no control to enter a fencer

#### Scenario: The endpoint refuses it too
- **WHEN** a hand-entered fencer is posted to a draft directly
- **THEN** it is refused with a reason naming publication, and the tournament holds no manual row
