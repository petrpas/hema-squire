## REMOVED Requirements

### Requirement: A tournament states who keeps its registrations
**Reason**: The capability is right and its name is not. What it describes is the tournament's **mode** — stored, two values, and it changes what the system does — which is exactly what the product had been calling four unstored feature flags.
**Migration**: Becomes `tournament-mode`'s **A tournament has a mode, and it is the only thing so called**, stating both names for one setting: `registrations_kept_by` in storage, *režim: automatický / manuální* on every surface an organizer reads. No column changes and nothing behaves differently.

### Requirement: Squire runs nothing against a tournament it does not keep
**Reason**: Renamed capability.
**Migration**: Moves to `tournament-mode` as **Squire runs nothing against a manual tournament**, unchanged in substance — the exclusion is still made once over tournaments rather than as a condition inside each pass.

### Requirement: Organizer-kept is a cause of registration dormancy
**Reason**: Renamed capability.
**Migration**: Moves to `tournament-mode` as **Manual mode is a cause of registration dormancy**. The predicate, its causes and the per-registration mark it stands beside are all unchanged.

### Requirement: In-app registration never opens on an organizer-kept tournament
**Reason**: Renamed capability.
**Migration**: Moves to `tournament-mode` as **In-app registration never opens on a manual tournament**. The refusal is still answered before every other reason and still never reported as `closed`.

### Requirement: The choice is made at creation and changed in Setup
**Reason**: The mode is no longer chosen on a surface of its own. It is the first row of the one settings surface, which also carries the payments setting and the three inclusions — so where it is asked is a statement about how Setup is arranged rather than about the mode.
**Migration**: `setup-navigation`'s **The tournament's settings are configured on one surface** fixes both places the mode is offered, and states that it leads the surface because it is the most consequential choice on it.

### Requirement: Changing who keeps the registrations is confirmed and states its effect
**Reason**: Renamed capability.
**Migration**: Moves to `tournament-mode` as **Changing the mode is confirmed and states its effect**, still confirming in both directions, still counting the in-app registrations Squire would stop managing, and still writing no registration.
