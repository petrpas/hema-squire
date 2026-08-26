## ADDED Requirements

### Requirement: A live figure is text, not an animation
A figure that changes because the value it states has changed — a countdown to a known moment being the case this system has — SHALL be admitted, and SHALL be drawn as a line of type in the ordinary ink of its context. It is distinct from the animated progress indicators the prohibitions forbid: those move to suggest progress they do not measure, while a live figure only ever states a measured quantity.

Such a figure SHALL NOT be accompanied by a bar, a ring, a track, a fill, a spinner, or any decoration that moves. No CSS animation and no transition SHALL be attached to it or to its container. It SHALL use tabular numerals at a fixed width so that its line neither reflows nor shifts as its digits change — the jitter, not the change of value, is what would read as animation.

A live figure SHALL update no more often than once per second, and SHALL be shown only while its value is worth watching. Where a figure counts towards a moment, it SHALL stop at that moment rather than continue past it, and SHALL never present a negative quantity.

This requirement admits nothing else: it does not relax the prohibition on skeleton shimmer, spinners, or animated progress bars, and it is not a licence to animate a value that is not being measured.

#### Scenario: A countdown is drawn
- **WHEN** a screen counts down to a known moment
- **THEN** the figure is a line of type in the surrounding ink, with no bar, ring, track, fill, or spinner beside it

#### Scenario: Digits change without moving the line
- **WHEN** a live figure ticks from one value to the next
- **THEN** its line keeps its width and its position, and nothing fades, slides, or fills

#### Scenario: The figure stops at its moment
- **WHEN** a countdown reaches the moment it counts towards
- **THEN** it stops and is replaced by what the moment brings, and no negative figure is shown

#### Scenario: The prohibition still stands
- **WHEN** a screen is waiting on work whose duration is unknown
- **THEN** no spinner, shimmer, or animated progress bar is drawn, and this requirement does not permit one
