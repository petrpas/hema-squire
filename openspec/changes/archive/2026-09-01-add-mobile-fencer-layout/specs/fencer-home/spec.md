## MODIFIED Requirements

### Requirement: Fencer identity header
The Fencer Home top bar SHALL show, left to right: the Hema Squire logo, the four tournament filter tabs, the fencer's display name with their hemaratings identity, and the account menu (⋯). WHEN the account has a bound hemaratings profile, the identity SHALL read "HRID: <id>" and link to the fighter's hemaratings.com profile page in a new browser tab. WHEN no hemaratings profile is bound, the identity SHALL read "no hemaratings" and navigate to the Profile page, where binding is offered.

Below 768px that single row does not fit, and the bar SHALL be laid out as two rows instead. The first row SHALL carry the logo at its left and the account menu at its right. The identity — display name and hemaratings identity alike — SHALL fold into the account menu, shown when the menu is opened rather than standing permanently in the bar, and SHALL keep the same link and navigation behaviour there. The second row SHALL carry the four filter tabs as one full-width scrolling band.

The bar SHALL stay at the top of the content as the page scrolls, positioned `sticky`, and SHALL add the device's top safe-area inset to its padding.

#### Scenario: Bound fencer sees HRID link
- **WHEN** a fencer whose account is bound to hemaratings fighter 1234 opens Fencer Home
- **THEN** the header shows their name and "HRID: 1234" linking to the hemaratings fighter page

#### Scenario: Unbound fencer is pointed to binding
- **WHEN** a fencer without a bound hemaratings profile clicks "no hemaratings" in the header
- **THEN** the Profile page opens

#### Scenario: Top bar on a narrow phone
- **WHEN** a fencer opens Fencer Home on a 390px-wide viewport
- **THEN** the first row shows the logo and the account menu alone, the second row shows the four filter tabs as a scrolling band, and no part of the bar overflows the screen

#### Scenario: Identity reachable from the menu on a phone
- **WHEN** that fencer opens the account menu
- **THEN** their display name and hemaratings identity are shown in it, the identity linking to the hemaratings fighter page when bound and to the Profile page when not

#### Scenario: Scrolling the list under the bar
- **WHEN** a fencer scrolls a long tournament list on a mobile browser
- **THEN** the top bar remains at the top of the content without detaching or overlapping the list

### Requirement: Tournament detail — page shell
The tournament detail page SHALL carry a header holding the tournament's display name, a tab control, and a close control, in that order across the header.

Below 768px that header SHALL be laid out on two rows instead: the display name on its own row with the close control at its right, and the tab control below it as one full-width scrolling band. The close control SHALL remain level with the display name.

The tab control SHALL offer a `Tournament` tab, always present, holding the information screen. It SHALL offer a second tab whenever the account holds a registration for that tournament or registration is available to it: labelled `Registered` when a registration is held — active, substituted, or cancelled — and `Register` when none is held and registration is available. When neither condition holds, the tab control SHALL offer the `Tournament` tab alone, and the reason registration is unavailable SHALL be stated on the information screen as it is today.

The tab control SHALL offer a third tab, `Teams`, exactly when the account holds an active registration for that tournament carrying at least one team and the tournament has not yet been held. It SHALL NOT be offered to an account with no registration, with a cancelled or expired registration, or with a registration holding no team, nor on a tournament dated before today, whose rosters are no longer editable. It SHALL stand last in the tab control, after the second tab. WHEN the third tab is offered, the second tab reads `Registered`, since a team is held only through a held registration.

The page SHALL open on the `Tournament` tab from every entry point, including a URL followed directly. The selected tab SHALL NOT be carried in the URL and SHALL NOT push a browser history entry. WHEN a tab in the control ceases to be offered while it is selected, the page SHALL fall back to the `Tournament` tab rather than show a tab that no longer exists.

Amending an existing registration SHALL open the amendment form on the `Registered` tab, in place of the registration it amends, and SHALL return to that registration when it is submitted or abandoned. No further tab SHALL be introduced for it, and leaving the `Registered` tab — for the `Tournament` tab or the `Teams` tab alike — SHALL abandon an amendment in progress as it does today.

The close control SHALL return to the list the page was opened from — the Fencer Home list whose filter tab was selected when the tournament was opened — and SHALL replace the page's back links: no "back to tournaments" link and no "back to information" link SHALL be rendered. WHEN the page was reached by URL rather than from a list, the close control SHALL lead to Fencer Home on its default Open tab. The close control SHALL carry an accessible name naming the action, so it is not announced as an unlabelled glyph.

The page body SHALL scroll to its end whenever its content is taller than the space available, on every tab. No part of the content SHALL be reachable only by resizing the window.

Sections on any tab SHALL be separated from one another by vertical space, so that no two bordered sections share or abut an edge.

The tournament's logo, where set, SHALL be presented at twice the size it is given on a list card and without a frame around it.

Organizer-authored prose on any tab SHALL wrap rather than overflow its column, including an unbroken string such as a bare URL, at every viewport width.

#### Scenario: Detail opens on the tournament tab
- **WHEN** a fencer opens a tournament from Fencer Home
- **THEN** the page shows the tournament name, a tab control resting on `Tournament`, and a close control, with the information screen below

#### Scenario: Detail header on a narrow phone
- **WHEN** a fencer opens a tournament on a 390px-wide viewport
- **THEN** the tournament name occupies its own row with the close control at its right, the tab control sits below it as a full-width scrolling band, and the page does not scroll sideways

#### Scenario: Register tab offered while registration is available
- **WHEN** a fencer without a registration opens a tournament whose registration is open and has an open slot
- **THEN** the tab control offers `Tournament` and `Register`, and selecting `Register` shows the registration form in place

#### Scenario: Tab reads Registered once a registration is held
- **WHEN** a fencer holding a reservation opens the same tournament
- **THEN** the second tab reads `Registered` and holds the registration, its state, and its actions

#### Scenario: Teams tab offered for a registration holding a team
- **WHEN** a fencer holding a reservation that includes one team opens the tournament
- **THEN** the tab control offers `Tournament`, `Registered`, and `Teams` in that order, and selecting `Teams` shows that team's roster editor

#### Scenario: Teams tab withheld from an individual registration
- **WHEN** a fencer holding a registration for individual disciplines only opens the tournament
- **THEN** the tab control offers `Tournament` and `Registered` alone, with no `Teams` tab

#### Scenario: Teams tab withdrawn when the last team is dropped
- **WHEN** a fencer standing on the `Teams` tab amends their registration to remove its only team
- **THEN** the `Teams` tab is no longer offered and the page falls back to the `Tournament` tab

#### Scenario: Single tab when registration is impossible
- **WHEN** a fencer without a registration opens a tournament whose registration has closed
- **THEN** only the `Tournament` tab is offered and the information screen states that registration is closed

#### Scenario: Past tournament with a registration
- **WHEN** a fencer opens a past tournament from the Past tab where they held a paid registration
- **THEN** the `Registered` tab holds the read-only summary, and no register, payment, or cancel action is offered on either tab

#### Scenario: Teams tab withheld on a past tournament
- **WHEN** a fencer opens a tournament dated before today where they held a registration carrying a team
- **THEN** no `Teams` tab is offered, and the team and its members remain readable on the read-only summary

#### Scenario: Returning to the information screen
- **WHEN** the fencer is on the `Register`, `Registered`, or `Teams` tab
- **THEN** the `Tournament` tab returns them to the information screen without leaving the page

#### Scenario: Amending stays on the registered tab
- **WHEN** a fencer holding a reservation starts an amendment
- **THEN** the amendment form opens on the `Registered` tab, the tab control shows the same tabs as before, and submitting returns to the amended registration on that same tab

#### Scenario: Closing the page
- **WHEN** the fencer activates the close control
- **THEN** they return to the list the detail was opened from, on that list's filter tab

#### Scenario: Closing a page reached by link
- **WHEN** a fencer who followed a `/t/<slug>` link activates the close control
- **THEN** Fencer Home is shown on the Open tab

#### Scenario: Long tournament read to the end
- **WHEN** a fencer opens a tournament whose information is taller than the window
- **THEN** the page scrolls and the last section is reachable

#### Scenario: Sections stand apart
- **WHEN** the information screen renders the header, disciplines, discounts, and other-actions sections
- **THEN** vertical space separates each from the next, with no two section borders touching

#### Scenario: A bare URL in the organizer's description
- **WHEN** an organizer's description contains a long URL with no spaces and the page renders at 360px
- **THEN** the URL wraps within the column and the page does not scroll sideways

### Requirement: In-app payment instructions
WHEN the tournament's payments feature is on and the account holds an unpaid reservation for it, the detail page SHALL display the payment instructions: total amount, bank account (IBAN), variable symbol, the instruction to quote the VS in the payment message for transfers without a VS field, the reservation expiry date, and an SPAYD QR code. The QR code and the full transfer details SHALL always be shown together.

WHEN the tournament's payments feature is off, no payment instructions SHALL be shown for any registration it holds, whatever that registration owes on paper. There is no account to quote, no variable symbol in use and no expiry to state, and showing a partial set would tell the fencer to do something the tournament is not asking of them.

The QR code presumes two devices — the code on a screen, a phone in hand — and is inert to a fencer reading it on the phone they would pay with. The instructions SHALL therefore also be actionable on a single device, at every viewport width:

- The slip SHALL offer an action that hands the QR image to the device, so it can be taken into a banking application. Where the browser can share a file, the action SHALL offer the image to the system share sheet, from which it can be saved to the photo library or sent directly to an application. Where it cannot, the action SHALL fall back to downloading the image. The action SHALL NOT be offered as a download alone, because a downloaded file does not reach the photo library that banking applications read from on all platforms.
- Each transfer detail that must be entered by hand — bank account number, IBAN, variable symbol, and amount — SHALL offer an action to copy its value to the clipboard.
- A copy action SHALL be offered only where the browser exposes a clipboard, which requires a secure context; where it does not, the action SHALL be absent rather than present and failing.
- Confirmation that a value was copied SHALL be static text beside the field, leaving by fade-out. No toast, no entrance animation, and no animated indicator SHALL be used.

Below 480px the slip SHALL stack in the order the fencer needs it: the QR image first, centred and sized to the narrower of its intrinsic width and a fraction of the column; the actions below it; the transfer details last.

#### Scenario: Payment panel after registering
- **WHEN** a fencer completes a registration for a payments-enabled tournament
- **THEN** the page shows the QR code alongside IBAN, amount, VS, and the VS-in-message instruction, and states when the reservation expires

#### Scenario: No instructions for a payments-off tournament
- **WHEN** a fencer opens the detail page of a payments-off tournament they are registered for
- **THEN** no payment instructions, account, variable symbol, QR code or expiry date is shown

#### Scenario: Paying on the device showing the QR code
- **WHEN** a fencer on a phone opens the payment slip for an unpaid reservation
- **THEN** the slip offers an action that hands the QR image to the device's share sheet, from which it can be saved to the photo library or opened in a banking application

#### Scenario: Copying the variable symbol
- **WHEN** a fencer activates the copy action beside the variable symbol on a secure origin
- **THEN** the variable symbol is placed on the clipboard and a static note beside the field states that it was copied, then fades out

#### Scenario: Copy actions on a desktop
- **WHEN** the payment slip is shown at 1024px
- **THEN** the copy actions and the QR action are offered there too

#### Scenario: Clipboard unavailable
- **WHEN** the payment slip is shown on an origin where the browser exposes no clipboard
- **THEN** no copy action is rendered, and the values remain readable

#### Scenario: Payment slip on a narrow phone
- **WHEN** the payment slip renders at 390px
- **THEN** the QR image stands first and centred, the actions follow it, the transfer details follow those, and the fields are not compressed into a narrow column beside the code
