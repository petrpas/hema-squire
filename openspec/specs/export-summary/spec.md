# export-summary Specification

## Purpose
Fix the Export phase's Summary tab: how many of each discipline and extra item the tournament offers, paid and unpaid — which lines it holds and in what order, how a discipline splits its seated from its queue, how an item counts pieces and breaks down by its option, and how the table leaves the screen.

## Requirements
### Requirement: The summary states what the tournament offers
The Summary tab SHALL be one table of three columns: **Item**, **Paid**, **Unpaid**.
It SHALL be as wide as its content rather than the phase's full width, so that
the counts stand beside what they count.

Its rows SHALL be derived from what the tournament offers, not from what was
chosen. The rows come in this order:
- each individual discipline, in the tournament's discipline order, named as its
  tab is named;
- then each extra item the tournament offers, grouped by category in the order
  the band lists categories, and within a category in the order the tournament
  holds its items.

Every category the tournament offers SHALL be summarised, whatever it is. A
category the tournament does not offer SHALL have no row. An item the tournament
offers SHALL have a row even where nobody chose it, stating 0 and 0, because
knowing that nobody wants something is a total too. A team discipline SHALL have
no row, for the reason it has no tab.

#### Scenario: Disciplines first, then items by category
- **WHEN** a tournament offers Longsword and Sabre, a rental of a mask, a T-shirt and an afterparty
- **THEN** the summary lists Longsword, Sabre, the mask, the T-shirt and the afterparty, in that order

#### Scenario: The table is as wide as its content
- **WHEN** the organizer opens the Summary tab on a wide screen
- **THEN** the table ends after its Unpaid column, not at the screen's edge

#### Scenario: Nobody chose it
- **WHEN** the tournament offers a seminar that nobody has chosen
- **THEN** the seminar has a row reading 0 and 0

#### Scenario: Not offered, not listed
- **WHEN** the tournament offers no merch
- **THEN** the summary has no merch row

#### Scenario: A team discipline has no row
- **WHEN** the tournament offers individual and team longsword
- **THEN** only the individual discipline has a row

### Requirement: A discipline counts its seated and its queue apart
A discipline's row SHALL count the fencers holding a seated entry in it. Directly
under it, a row named as the discipline followed by `(fronta)` (`(queue)` in
English) SHALL count the fencers holding a substitute entry in it.

The queue row SHALL be stated only where at least one fencer holds a substitute
entry in the discipline, as the tab leaves out its `+ 0`. On a tournament whose
conduct creates no substitute placements it SHALL therefore never appear.

The counts SHALL be the tab's own: a seated count and a queue count that differ
from the numbers the discipline's tab states would leave the organizer two
answers to one question.

#### Scenario: Seated and queued, paid and unpaid
- **WHEN** Longsword has 44 paid and 4 unpaid fencers seated, and 2 paid and 12 unpaid fencers queued
- **THEN** the summary reads Longsword 44 / 4 and, beneath it, Longsword (fronta) 2 / 12

#### Scenario: No queue, no queue row
- **WHEN** Sabre has nobody queued
- **THEN** Sabre has one row and no queue row

#### Scenario: The summary agrees with the tab
- **WHEN** the Sabre Open tab reads 24 + 3
- **THEN** the Sabre Open row's paid and unpaid add up to 24, and its queue row's to 3

### Requirement: An item counts pieces, broken down by its option
An item's row SHALL count the pieces chosen: the sum of the quantities of every
selection of that item, so an order of two T-shirts counts two.

An item that asks the fencer an option SHALL be stated as one row per answer,
named as the item followed by the answer (`Triko – XL`), in place of a single row
for the item:
- where the item declares its choices, one row per declared choice, in the order
  the organizer declared them, including a choice nobody picked; an answer stored
  before the choices were edited and no longer among them SHALL have a row of its
  own after the declared ones;
- where the answer is free text, one row per distinct answer, answers differing
  only in letter case or surrounding spaces being one answer, in the order the
  answers first appear; where nobody chose the item, a single row for the item,
  at 0 and 0;
- a selection that gave no answer SHALL be counted on a row named as the item
  followed by `neuvedeno` (`not given` in English), stated only where it counts
  something.

An item that asks no option SHALL have one row, whatever answers its selections
may carry from before the option was removed.

This holds in every category. A rental with a size is broken down as a T-shirt is.

#### Scenario: Pieces, not people
- **WHEN** one fencer ordered two XL T-shirts and another ordered one
- **THEN** the Triko – XL row counts 3

#### Scenario: Declared sizes in their order, zeros included
- **WHEN** the T-shirt declares the sizes S, M, L and XL and nobody ordered an S
- **THEN** the summary lists Triko – S at 0 and 0, then M, L and XL

#### Scenario: A free-text option
- **WHEN** a rental jacket asks for a size as free text and three fencers answered "L", "l " and "XL"
- **THEN** the summary lists the jacket with L counting two and XL counting one

#### Scenario: An unanswered selection
- **WHEN** a selection of the T-shirt carries no size
- **THEN** it is counted on the Triko – neuvedeno row

#### Scenario: An item without an option
- **WHEN** the afterparty asks no option and 30 fencers chose it
- **THEN** the afterparty has one row counting 30

### Requirement: Paid is the registration's settled state
A fencer's entries and pieces SHALL be counted as paid where their registration is
settled, and as unpaid otherwise, exactly as the paid column of every other tab
reads it (`export-tables`). Settlement belongs to the registration and not to its
items, so a settled registration counts every entry and item it holds as paid,
and one not yet settled counts every one of them as unpaid. A partial payment is
not apportioned across items.

A row a deletion has taken out of the table SHALL count nowhere.

The counts SHALL follow the tournament's rows. A registration entered, deleted,
settled, or moved in or out of a queue SHALL be reflected on the next read.

#### Scenario: An unsettled registration's items are unpaid
- **WHEN** a fencer entered in Longsword who ordered a T-shirt has not paid
- **THEN** they count on Longsword's unpaid side and the shirt on its row's unpaid side

#### Scenario: A queued fencer priced at zero is unpaid
- **WHEN** a fencer's only entry sits in a queue and they have been credited nothing
- **THEN** they count on the queue row's unpaid side

#### Scenario: A deleted row counts nowhere
- **WHEN** the organizer deletes a row that held an XL T-shirt
- **THEN** the Triko – XL row counts one fewer

### Requirement: The summary leaves as the other tables do
The summary's copy action SHALL put the table on the clipboard as tab-separated
values with the header row Item, Paid, Unpaid, its counts as digits, and no
position column. The English tick SHALL render its header and its `(fronta)` and
`neuvedeno` in English and leave the discipline and item names as the organizer
wrote them.

The Sheets export SHALL write the same table as the `Summary` worksheet
(`data-export`).

#### Scenario: A copied summary
- **WHEN** the organizer copies the Summary tab and pastes into a spreadsheet
- **THEN** each line lands in three cells under Item, Paid and Unpaid, the counts as numbers

#### Scenario: An English copy
- **WHEN** a Czech-speaking organizer ticks English and copies the summary
- **THEN** the header reads Item, Paid, Unpaid and the queue row reads Longsword (queue)

