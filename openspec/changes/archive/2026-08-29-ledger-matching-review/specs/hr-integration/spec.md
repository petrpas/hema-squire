## MODIFIED Requirements

### Requirement: Canonical naming
The HR canonical name SHALL be the display name for HR-bound fencers; the
originally registered name SHALL be preserved alongside it.

A fencer becomes HR-bound by a verdict — an organizer's resolution, or an id the
fencer supplied — and not by the existence of a match proposal. While a match is
only proposed, the registered name, club and nationality SHALL remain the
fencer's as given, and the profile's SHALL be shown alongside them as the
evidence for the proposal rather than in their place.

#### Scenario: Name normalization
- **WHEN** an imported fencer is bound to an HR profile with a differently spelled name
- **THEN** the HR spelling becomes the display name and the original stays retrievable

#### Scenario: Proposal does not normalize
- **WHEN** a match is proposed for an imported fencer but no verdict has been reached
- **THEN** the fencer's registered name, club and nationality are unchanged, and the profile's appear beside them
