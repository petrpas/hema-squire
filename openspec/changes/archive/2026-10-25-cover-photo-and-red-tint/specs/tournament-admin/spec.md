## RENAMED Requirements

- FROM: `### Requirement: The organizer chooses the cover tint`
- TO: `### Requirement: The organizer chooses the cover ground`

## MODIFIED Requirements

### Requirement: The organizer chooses the cover ground
Beside the logo in Setup the organizer SHALL be offered the ground the tournament's card and detail cover wear (`fencer-home`), under the label "Pozadí pruhu", as one choice among: following the logo, the file-blue tint, the seal-green tint, the form-yellow tint, the ledger-red tint, and a photo. Following the logo is the default, and its option SHALL name the tint it gives now. A chosen tint or photo SHALL win over the logo's band and over the slug, SHALL outlive a change or removal of the logo, and SHALL be saved with the rest of the tournament's identity. Choosing to follow the logo again SHALL clear it.

The photo option SHALL carry the cover photo's upload and removal controls, in the treatment of the logo's (`Logo control is a tertiary text action`). It SHALL be choosable only while a photo is stored: choosing it without one SHALL offer the upload, and a successful upload SHALL select it. Choosing a tint while a photo is stored SHALL keep the photo, so the organizer can return to it without uploading again.

Only the four tint tokens SHALL be offered as colors: the cover renders no color from anywhere else (`design-system`).

#### Scenario: A tricolour event
- **WHEN** the organizer of a tournament whose red-white-blue logo reads as warm chooses the file-blue tint and saves
- **THEN** its card and detail cover wear the file-blue tint

#### Scenario: A red event
- **WHEN** the organizer chooses the ledger-red tint and saves
- **THEN** its card and detail cover wear the ledger-red tint

#### Scenario: Back to the logo
- **WHEN** the organizer chooses to follow the logo again and saves
- **THEN** the cover wears the tint the logo's band gives, or the slug's where it has none

#### Scenario: Choice kept through a new logo
- **WHEN** the organizer who chose the seal-green tint uploads a different logo
- **THEN** the cover still wears the seal-green tint

#### Scenario: Photo chosen by uploading it
- **WHEN** the organizer of a tournament with no cover photo chooses the photo option and uploads a photograph
- **THEN** the photo option is selected, and once saved the card and detail cover show the photograph

#### Scenario: A tint chosen over a stored photo
- **WHEN** the organizer whose cover wears a photo chooses the form-yellow tint and saves
- **THEN** the cover wears the form-yellow tint, and the photo option can be chosen again without a new upload

## ADDED Requirements

### Requirement: The cover photo is stored bounded and bare
An organizer SHALL be able to upload one cover photo per tournament, replace it, and remove it. The server SHALL accept an upload up to the logo's size cap, apply the orientation the image records, re-encode it to a bounded image whose longer side is at most 1600 pixels, and store only that. The stored image SHALL carry no metadata from the upload — no location, camera or author — since the photo is served publicly and an organizer's phone photograph would otherwise publish where it was taken.

A failed upload SHALL be reported by its cause exactly as a failed logo upload is (`Logo upload failure reporting`).

Removing the photo SHALL delete it, and where the cover wore it the choice SHALL return to following the logo. The photo SHALL be independent of the logo: uploading, replacing or removing either SHALL leave the other untouched.

The photo SHALL be readable by anyone, like the logo: it is public-facing information about the tournament.

#### Scenario: A phone photograph
- **WHEN** the organizer uploads a 4000×3000 JPEG of a few megabytes, taken in portrait, carrying GPS coordinates
- **THEN** the stored photo is upright, its longer side is 1600 pixels, and it carries no GPS or other metadata

#### Scenario: Oversized photo named as oversized
- **WHEN** the uploaded file exceeds the size cap
- **THEN** the message states that the file is too large

#### Scenario: Removing the worn photo
- **WHEN** the organizer whose cover wears the photo removes it
- **THEN** no photo is stored and the cover follows the logo

#### Scenario: Logo removal keeps the photo
- **WHEN** the organizer whose cover wears a photo removes the logo
- **THEN** the cover still shows the photo, and the plate shows the short code or monogram
