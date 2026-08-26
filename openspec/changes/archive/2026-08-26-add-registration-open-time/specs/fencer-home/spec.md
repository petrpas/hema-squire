## MODIFIED Requirements

### Requirement: Tournament detail — information
The tournament detail page SHALL open, from the list, on an information screen that presents the tournament's full public information and does not itself contain the registration form. It SHALL open with the tournament's identity stated as consecutive lines in this order: the title; the subtitle when set; the date, the location and the qualification statement on one line; the registration opening moment and closing date on one line; the titular organizers; and the description. Parts sharing a line SHALL be separated by the spaced middle dot, and a line whose every part is absent SHALL be omitted rather than left blank. The logo, when set, stands beside these lines.

The opening moment SHALL be stated with its time of day whenever the tournament sets one, and with the zone that time is stated in. Where the tournament sets no opening time, the opening SHALL be stated as a date alone exactly as before, with no invented hour and no zone.

Below them the screen SHALL show three grouped sections. The disciplines section SHALL list each discipline by its name — never its slug (`discipline-identity`) — with its entry fee, its registered count as registered/capacity (or substitute-queue length when full), its optional when/where, and its optional ruleset shown as a short style name linking to the external ruleset document when a link is set. Several disciplines classified alike SHALL each be listed on their own line under their own name, with their own fee and their own count. A team discipline SHALL be listed in the same section, marked as a team event, with its per-team fee, its roster bounds, and its count stated in teams as entered/capacity (or waitlist length when full); the team-event marker SHALL be set off from the discipline's name by horizontal space rather than sitting flush against it. When the tournament sets a team composition deadline and offers at least one team discipline, the deadline SHALL be stated in this section. The discounts section SHALL follow the disciplines section and SHALL list every discount the tournament configures, in configured order, each with its name, its condition stated as text, and its configured value — a fixed amount in each configured currency, or a percentage. The discounts section SHALL NOT show selection markers, since the information screen carries no selection, and SHALL be omitted entirely when the tournament configures no discounts. The other-actions section SHALL list non-purchasable activities — seminars, afterparties, after-sparrings, and accommodation — each with its optional when/where and remark. The information screen SHALL NOT mention gear lending or merch, and SHALL NOT show prices or quantity selectors for the other-actions section. When registration is available, it SHALL be reached through the page's `Register` tab rather than through a control on the information screen itself.

Where a discipline or an action carries any of its optional when/where/ruleset/remark text, that text SHALL be presented as a subordinate line beneath the row, one size down and in faded ink, with its parts separated by the spaced middle dot used elsewhere. The line SHALL NOT be introduced by a leading dash or any other bullet character: its indentation and weight already mark it as subordinate.

#### Scenario: Fencer reviews a tournament
- **WHEN** a fencer opens a tournament's detail from Fencer Home
- **THEN** they read the title, the subtitle, the date · place · qualification line, the registration window line, the organizers and the description in that order, followed by each discipline under its name with its fee, registered/capacity count, and any when/where and ruleset link

#### Scenario: Absent parts collapse
- **WHEN** a tournament has no subtitle, no location and no registration dates
- **THEN** those lines are omitted and no blank line, stray dot, or empty gap is left behind

#### Scenario: Opening moment states its hour
- **WHEN** a fencer opens the detail of a tournament whose registration opens at 18:00 on 1 September
- **THEN** the registration window line states that opening date together with 18:00 and the zone it is stated in

#### Scenario: Date-only opening states no hour
- **WHEN** a fencer opens the detail of a tournament whose registration-opens date carries no time
- **THEN** the line states the date alone, with no time and no zone

#### Scenario: Team marker set off from the name
- **WHEN** a team discipline is listed
- **THEN** its team-event marker is separated from the discipline's name by horizontal space, not placed flush against it

#### Scenario: Tiers listed separately
- **WHEN** a tournament offering two longsword disciplines with different capacities and fees is opened
- **THEN** both are listed on their own lines, each under its own name with its own fee and its own count

#### Scenario: Team discipline presented in teams
- **WHEN** a tournament offering a team discipline with capacity 8 and 5 teams entered is opened
- **THEN** that discipline is listed as a team event with its per-team fee, its roster bounds, and a count of 5/8 teams, alongside the composition deadline when one is set

#### Scenario: Detail line carries no leading dash
- **WHEN** a discipline with a when, a where and a ruleset is presented on the information screen
- **THEN** its subordinate line begins with the when value, with no dash, hyphen or bullet before it, and the three parts are separated by the spaced middle dot

#### Scenario: Discounts listed below the disciplines
- **WHEN** a fencer opens the information screen of a tournament offering −500 Kč for 2 disciplines and −10 % for early registration
- **THEN** a discounts section appears below the disciplines listing both, each with its name, the condition under which it applies, and its value, with no selection markers

#### Scenario: Discount values shown per configured currency
- **WHEN** the information screen of a CZK + EUR tournament lists a fixed discount configured as 500 Kč / 20 €
- **THEN** the row states both amounts, exactly as discipline and item prices are stated on the same screen

#### Scenario: No discounts, no section
- **WHEN** a fencer opens the information screen of a tournament that configures no discounts
- **THEN** no discounts section and no empty-state text appear

#### Scenario: Actions grouped without gear or merch
- **WHEN** the tournament offers a seminar and an afterparty alongside gear lending and merch items
- **THEN** the information screen lists the seminar and afterparty under other actions with their when/where and remark, and does not show gear lending, merch, prices, or quantity selectors

#### Scenario: Open Register from information
- **WHEN** the fencer views the information screen while registration is available
- **THEN** the page's `Register` tab is offered and opens the registration form, and the information screen itself carries no register button

## ADDED Requirements

### Requirement: Waiting for registration to open
When a fencer opens the detail page of a published tournament whose registration has not yet opened, the page SHALL state the opening moment and SHALL open registration in place when that moment passes, without asking the fencer to reload. Registration opening is the busiest moment of a tournament's life, and a page that requires a manual refresh turns that into a burst of reloads at exactly the wrong time.

Within the last day before the opening moment, the page SHALL additionally show a **live countdown** to it, stated as a figure that decreases once per second. Outside that last day the opening moment SHALL be stated without any counter. The countdown SHALL be text and nothing more, as fixed by `design-system`: it SHALL NOT be accompanied by a bar, a ring, a spinner, or any moving decoration, and its line SHALL NOT reflow, shift, or change width as its digits change. It SHALL stop at the opening moment and be replaced by the opened state; it SHALL NEVER show a negative figure.

The page SHALL measure its own clock against the server's, using the server instant the response carries (`registration`), and SHALL count down and unlock against the corrected time rather than against the device clock. It SHALL NOT poll the server while waiting: the wait SHALL cost no request until the opening moment itself, at which point the page SHALL refresh the tournament once so that seat counts are current as registration opens. A page whose timer did not fire on time — a backgrounded tab, a sleeping device — SHALL re-evaluate the moment when it becomes visible or focused again, so that a fencer returning after the opening finds registration open immediately.

Opening the form in place is presentation only. The system's gate remains the authority (`registration`), and where a submission is nonetheless rejected as not yet open, the page SHALL return to the waiting state with its countdown recomputed from that response rather than showing a generic failure.

#### Scenario: Countdown inside the last day
- **WHEN** a fencer opens the detail page four hours before registration opens
- **THEN** the page states the opening moment and shows a countdown that decreases once per second

#### Scenario: No countdown far out
- **WHEN** a fencer opens the detail page six weeks before registration opens
- **THEN** the page states the opening moment and shows no counter

#### Scenario: Opens in place
- **WHEN** the fencer has the detail page open as the opening moment passes
- **THEN** the countdown ends, the tournament is refreshed once, and the `Register` tab becomes available without the fencer reloading the page

#### Scenario: Waiting costs no requests
- **WHEN** a fencer leaves the detail page open for an hour before the opening moment
- **THEN** the page issues no repeated requests for the tournament during that hour

#### Scenario: Tab returned to after the moment
- **WHEN** a fencer leaves the detail page in a background tab and returns to it ten minutes after registration opened
- **THEN** the page shows registration open as soon as it is looked at again

#### Scenario: Device clock is wrong
- **WHEN** a fencer's device clock is several minutes ahead of the server's
- **THEN** the countdown and the in-place opening still follow the server's clock, and the fencer is not shown a registration form the system would reject

#### Scenario: Submission still beats the gate
- **WHEN** a registration submitted from the opened form is rejected as not yet open
- **THEN** the page returns to stating the opening moment with its countdown, rather than showing a generic error

#### Scenario: The countdown does not move the page
- **WHEN** the countdown ticks from one second to the next
- **THEN** only the digits change: the line keeps its width and position, and nothing animates, fades, fills, or slides
