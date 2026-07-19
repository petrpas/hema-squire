## REMOVED Requirements

### Requirement: One account per HR identity
**Reason**: Claims to HR profiles are self-declared and unverifiable, so exclusivity only empowers the first (possibly wrong) claimant to lock out the profile's real owner, and the "account recovery" the rejected fencer was directed to does not exist.
**Migration**: The unique constraint on the account hr_id is dropped; the `hr_id_already_bound` rejection disappears from signup and Profile binding. Existing single claims are unaffected.

## ADDED Requirements

### Requirement: Non-exclusive HR profile claims
The system SHALL allow multiple accounts to claim the same HEMA Ratings profile — a claim to an already-claimed profile SHALL NOT be rejected at signup or Profile binding. Wherever HR candidate profiles are presented for claiming, profiles already claimed by another account SHALL be marked with a non-blocking notice so the fencer can recognize they may already have an account. The admin accounts list SHALL flag accounts whose hr_id is shared with at least one other account; resolution remains the existing administrative unbinding.

#### Scenario: Claiming an already-claimed profile succeeds
- **WHEN** a fencer confirms an HR profile that another account has already claimed, at signup or on the Profile page
- **THEN** the claim succeeds exactly as for an unclaimed profile

#### Scenario: Fencer warned about an existing claim
- **WHEN** HR candidate profiles are listed and one of them is already claimed by another account
- **THEN** that candidate carries a visible notice that it is already claimed, and the fencer may still confirm it

#### Scenario: Admin sees duplicate claims
- **WHEN** an Admin opens the accounts list while two accounts share the same hr_id
- **THEN** both accounts are flagged as sharing their HR profile, and the Admin can resolve the duplicate by unbinding the wrong account
