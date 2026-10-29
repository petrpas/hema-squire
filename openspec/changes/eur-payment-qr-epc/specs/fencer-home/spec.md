## MODIFIED Requirements

### Requirement: In-app payment instructions
WHEN the tournament's payments feature is on and the account holds an unpaid reservation for it, the detail page SHALL display the payment instructions: total amount, bank account (IBAN), variable symbol, the instruction to quote the VS in the payment message for transfers without a VS field, the reservation expiry date, and a payment QR code in the format its currency takes, as fixed by `payments`. The QR code and the full transfer details SHALL always be shown together.

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
