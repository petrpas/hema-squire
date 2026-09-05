## REMOVED Requirements

### Requirement: A tournament carries four feature flags
**Reason**: The four were never one kind of thing. Three govern which controls Setup offers and change nothing a fencer experiences; the fourth, payments, suspends machinery — which is why this capability had to carry a requirement whose whole job was to say one member was different.
**Migration**: The three move to `tournament-features` as **A tournament carries three feature flags**, which states the property they share without an exception. Payments moves to `payments`. No stored column changes.

### Requirement: Easy mode is the absence of every feature
**Reason**: It named a state that was never stored. `isEasyMode` derived it wherever it was needed, and because the creation dialog offered it as a choice anyway, this requirement had to answer what happens when an organizer picks advanced and ticks nothing — a case invented by the mismatch between a control and the absence of anything behind it.
**Migration**: Removed outright, not renamed. A tournament with no feature enabled is described by that, and `tournament-features` forbids deriving a name from how many are on. The word *mode* moves to `tournament-mode`, which is stored and does change behaviour.

### Requirement: The mode is chosen in a dialog of its own at creation
**Reason**: Creation now asks for the mode, the payments setting and the three inclusions on one screen rather than in a dialog of its own after another dialog.
**Migration**: `setup-navigation`'s **The tournament's settings are configured on one surface** fixes that screen, including that it is dismissible and that dismissing it leaves the tournament exactly as created.

### Requirement: The mode is stated and changed on OTHER
**Reason**: `OTHER` carried a mode section and, after `add-registrations-kept-by`, a registrations section beside it — two sections describing one configuration.
**Migration**: `setup-navigation`'s settings requirement fixes the single section that states all three tiers and reopens the settings surface.

### Requirement: Disabling a feature hides its settings without changing them
**Reason**: Renamed capability.
**Migration**: Moves to `tournament-features` unchanged in substance, with its "Except for payments" clause removed — there is no longer a member of this set that withdraws a product.

### Requirement: Turning off a feature the tournament uses is warned and confirmed
**Reason**: Renamed capability.
**Migration**: Moves to `tournament-features`, no longer naming the payment settings among what a warning counts.

### Requirement: The schedule feature governs the disciplines' when and where
**Reason**: Renamed capability.
**Migration**: Moves to `tournament-features` unchanged.

### Requirement: The team feature governs the team surfaces
**Reason**: Renamed capability.
**Migration**: Moves to `tournament-features` unchanged.

### Requirement: The extra services feature governs the EXTRA tab
**Reason**: Renamed capability.
**Migration**: Moves to `tournament-features` unchanged.

### Requirement: The payments feature suspends the payment machinery
**Reason**: It is the only requirement here describing what happens to money, reservations and mail. It lived in a capability about modes because the flag did, not because the behaviour belongs there.
**Migration**: Moves to `payments` as **The payments setting suspends the payment machinery**, stating that it stands beside the mode rather than among the features. Every effect it fixes is unchanged.

### Requirement: Tournaments predating the mode are derived from what they use
**Reason**: Renamed capability.
**Migration**: Moves to `tournament-features` as **Tournaments predating the features are derived from what they use**, still deriving the payments setting by the same one-shot pass.
