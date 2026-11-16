## ADDED Requirements

### Requirement: Each piste has a keyed link
The organizer SHALL be able to issue a link for a piste: `/floor/ring/:piste` with a
secret key in the URL fragment. As a guest management link's key does, the key stays
out of the address the server sees and out of any referrer.

**Sharing.** The organizer can copy the link or show it as a QR code.

**Revoking.** The organizer can revoke a link, and issuing a new one revokes the old.

**Storage.** Keys SHALL be stored hashed.

#### Scenario: A revoked link stops working
- **WHEN** the organizer revokes piste 3's link
- **THEN** the old link's next request is refused and the screen states that the link is no longer valid

### Requirement: The piste screen shows only its piste's current work
A valid link SHALL open a screen showing only:
- the current pool or elimination bout planned on its piste;
- that pool's bouts, with the next unrecorded bout first;
- a control for each side's score and outcome, sized for a touch screen
  (`responsive-layout`).

The screen SHALL NOT show other pistes, names beyond those fencing there, or anything of
the office.

**Where it runs.** It runs outside the organizer layout and needs no account.

#### Scenario: A volunteer records a bout
- **WHEN** a volunteer with piste 2's link records 5:3 for the current bout
- **THEN** the bout is recorded, the next bout is shown, and the console shows the result within its refresh

### Requirement: What a key can do is narrow
A piste key SHALL allow only two things:
- reading its piste's current work;
- recording or correcting the results of that work, while the discipline's pools or
  the bout's round are not closed.

Every other request made with it SHALL be refused.

**Rate limiting.** Requests made with a key SHALL be rate limited.

#### Scenario: A key cannot reach another piste
- **WHEN** piste 2's key is used to record a bout planned on piste 4
- **THEN** the request is refused
