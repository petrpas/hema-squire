## ADDED Requirements

### Requirement: Fencer Home addressed by URL, filter tab included
Fencer Home SHALL be addressed by `/`, and the selected filter tab SHALL be carried in the
URL as the query parameter `tab`, whose values are `announced`, `open`, `past`, and `mine`.
An absent, empty, or unrecognised `tab` SHALL resolve to the Open tab, so that `/` remains
the landing URL and the rule that the Open tab is selected after login is unchanged.
Selecting a filter tab SHALL change the URL and push a browser history entry; a reload SHALL
reopen the tab named by the URL.

A tournament's detail page SHALL be addressed by `/t/:slug`.

#### Scenario: Tab named in the URL
- **WHEN** a fencer selects the Past tab
- **THEN** the address bar reads `/?tab=past` and the Past list is shown

#### Scenario: Landing URL selects Open
- **WHEN** a fencer opens `/` with no query string
- **THEN** the Open tab is selected

#### Scenario: Unrecognised tab value
- **WHEN** a visitor opens `/?tab=archive`
- **THEN** the Open tab is shown rather than an error or an empty list

#### Scenario: Tab survives a reload
- **WHEN** a fencer on `/?tab=mine` reloads the browser
- **THEN** the Mine tab is shown again

#### Scenario: Back steps between tabs
- **WHEN** a fencer selects Announced and then Mine, and presses Back
- **THEN** the Announced list is shown again

### Requirement: Tournament entries and filter tabs are links
Each tournament card in any of the four lists SHALL be a link to that tournament's `/t/:slug`
URL, and each filter tab SHALL be a link to its own `?tab=` URL, so that middle-click and
modifier-click open them in a new browser tab and the browser offers to copy their addresses.
Both SHALL keep the appearance they have as controls today: no default-blue text, no default
underline, and the same card and tab treatment as before.

#### Scenario: Card links to the tournament
- **WHEN** a fencer middle-clicks a tournament card
- **THEN** that tournament's detail page opens in a new browser tab at `/t/<slug>`

#### Scenario: Filter tab links to its list
- **WHEN** a fencer copies the address of the Mine tab
- **THEN** the copied address is `/?tab=mine`

#### Scenario: Appearance unchanged
- **WHEN** the lists and the tab bar render
- **THEN** cards and tabs look exactly as they did as buttons, with no link colour or underline introduced

## MODIFIED Requirements

### Requirement: Read-only past tournament detail
WHEN a tournament detail is shown for a tournament dated before today, the page SHALL present the tournament information (name, date, location, organizers, disciplines with fees, extra services with prices) and, when the account had a registration, its summary — state, selected disciplines and extra services, and the computed total. The page SHALL NOT offer registration, payment instructions, or cancellation.

Read-only-ness SHALL be a property of the tournament's date rather than of the way the page was reached, so that it holds for a detail opened from the Past tab, from the Mine tab, and from a `/t/:slug` link followed directly.

#### Scenario: Past detail shows history without actions
- **WHEN** a fencer opens a past tournament where they had a paid registration
- **THEN** the detail shows the tournament information and their paid registration summary, with no Register button, payment panel, or cancel action

#### Scenario: Past tournament reached by link
- **WHEN** a fencer follows a `/t/<slug>` link to a tournament dated before today
- **THEN** the detail is read-only, exactly as it is when opened from the Past tab

#### Scenario: Past tournament reached from Mine
- **WHEN** a fencer opens a tournament dated before today from the Mine tab
- **THEN** the detail is read-only

### Requirement: Tournament detail — page shell
The tournament detail page SHALL carry a header holding the tournament's display name, a tab control, and a close control, in that order across the header.

The tab control SHALL offer a `Tournament` tab, always present, holding the information screen. It SHALL offer a second tab whenever the account holds a registration for that tournament or registration is available to it: labelled `Registered` when a registration is held — active, substituted, or cancelled — and `Register` when none is held and registration is available. When neither condition holds, the tab control SHALL offer the `Tournament` tab alone, and the reason registration is unavailable SHALL be stated on the information screen as it is today. The page SHALL open on the `Tournament` tab from every entry point, including a URL followed directly. The selected tab SHALL NOT be carried in the URL and SHALL NOT push a browser history entry.

Amending an existing registration SHALL open the amendment form on the `Registered` tab, in place of the registration it amends, and SHALL return to that registration when it is submitted or abandoned. No third tab SHALL be introduced for it.

The close control SHALL return to the list the page was opened from — the Fencer Home list whose filter tab was selected when the tournament was opened — and SHALL replace the page's back links: no "back to tournaments" link and no "back to information" link SHALL be rendered. WHEN the page was reached by URL rather than from a list, the close control SHALL lead to Fencer Home on its default Open tab. The close control SHALL carry an accessible name naming the action, so it is not announced as an unlabelled glyph.

The page body SHALL scroll to its end whenever its content is taller than the space available, on both tabs. No part of the content SHALL be reachable only by resizing the window.

Sections on either tab SHALL be separated from one another by vertical space, so that no two bordered sections share or abut an edge.

The tournament's logo, where set, SHALL be presented at twice the size it is given on a list card and without a frame around it.

#### Scenario: Detail opens on the tournament tab
- **WHEN** a fencer opens a tournament from Fencer Home
- **THEN** the page shows the tournament name, a tab control resting on `Tournament`, and a close control, with the information screen below

#### Scenario: Register tab offered while registration is available
- **WHEN** a fencer without a registration opens a tournament whose registration is open and has an open slot
- **THEN** the tab control offers `Tournament` and `Register`, and selecting `Register` shows the registration form in place

#### Scenario: Tab reads Registered once a registration is held
- **WHEN** a fencer holding a reservation opens the same tournament
- **THEN** the second tab reads `Registered` and holds the registration, its state, and its actions

#### Scenario: Single tab when registration is impossible
- **WHEN** a fencer without a registration opens a tournament whose registration has closed
- **THEN** only the `Tournament` tab is offered and the information screen states that registration is closed

#### Scenario: Past tournament with a registration
- **WHEN** a fencer opens a past tournament from the Past tab where they held a paid registration
- **THEN** the `Registered` tab holds the read-only summary, and no register, payment, or cancel action is offered on either tab

#### Scenario: Returning to the information screen
- **WHEN** the fencer is on the `Register` or `Registered` tab
- **THEN** the `Tournament` tab returns them to the information screen without leaving the page

#### Scenario: Amending stays on the registered tab
- **WHEN** a fencer holding a reservation starts an amendment
- **THEN** the amendment form opens on the `Registered` tab, the tab control still shows two tabs, and submitting returns to the amended registration on that same tab

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
