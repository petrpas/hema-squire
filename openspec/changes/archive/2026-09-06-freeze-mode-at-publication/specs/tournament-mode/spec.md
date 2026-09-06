## ADDED Requirements

### Requirement: The mode is fixed at publication
A tournament's mode SHALL be settled by publication. It SHALL be chosen when the tournament is created and SHALL be freely changeable for as long as the tournament is a draft; publishing SHALL fix it, and no action thereafter SHALL change it.

An attempt to change the mode on a published tournament SHALL be **refused with a stated reason**, never accepted and never silently ignored, so that an organizer who tries learns why rather than wondering whether it took.

Publication is the boundary because publication is where the promise is made. A published manual tournament has told the world where to register; a published automatic one has opened its own form. Both statements are made at publication rather than at the first person who acts on them, and both become false the moment the mode moves.

Being fixed SHALL be a property of the mode alone. The payments setting and the features fixed by `tournament-features` SHALL remain changeable after publication, as they are: they govern what Squire does with money and what Setup offers, and nothing downstream of either assumes it holds still.

A published tournament SHALL NOT be capable of being made incomplete by a change of mode. The mandatory items a mode implies — the external registration address on a manual tournament — are guaranteed by the completeness rule at the moment of publication, and this is what keeps that guarantee true afterwards.

#### Scenario: A draft switches freely
- **WHEN** the organizer of an unpublished tournament changes its mode
- **THEN** the change is accepted, whichever direction it goes

#### Scenario: Publication settles it
- **WHEN** the organizer of a published tournament attempts to change its mode
- **THEN** the attempt is refused with a stated reason and the mode is unchanged

#### Scenario: The other settings are unaffected
- **WHEN** the organizer of a published tournament turns the payments setting off, or turns a feature on
- **THEN** both changes are accepted as before

#### Scenario: No published tournament is made incomplete by a mode
- **WHEN** any published tournament is read
- **THEN** nothing it is missing is missing on account of a mode changed after it was published

## REMOVED Requirements

### Requirement: Changing the mode is confirmed and states its effect
**Reason**: Its whole content was a warning that counts the in-app registrations Squire would stop managing. With the mode changeable only on a draft, that count can never be anything but zero — the registration gate requires publication, so a draft holds no in-app registrations by construction. A draft may hold registrations issued from an import, but those are dormant by origin and unaffected by the mode, so there is nothing to count there either.
**Migration**: What remains worth saying — that a manual tournament takes no registrations in Squire and that Squire writes to nobody — is already said by the settings surface beside each answer, at the moment the organizer chooses (`setup-navigation`). It belongs there rather than in a dialog after the fact. The rule that no registration is deleted, cancelled or moved by a change of mode is preserved by **The mode is fixed at publication**, under which the only tournaments that can change hold nothing to move.
