## ADDED Requirements

### Requirement: A visitor with no account reads the UI in the default locale
A public screen rendered for a visitor holding no account SHALL render in the application's
default locale, Czech — the locale that is complete and that every other one falls back to.
It SHALL NOT be derived from the browser's detected locale, and SHALL NOT be taken from a
preference left behind by a session that has ended.

This is deliberately not the English the sign-in screen renders in. That screen is pinned to
English by its own requirement, and an *account's* stored default being English is a fact
about accounts, not about what language an anonymous page is written in.

The default SHALL be settled before the first paint, so a public screen is not rendered in
one language and then swapped into another.

Signing in SHALL switch the UI to the account's own preferred language at once, on the screen
the visitor is already on, without a reload. Signing out SHALL return it to the default.

#### Scenario: Anonymous list is in the default locale
- **WHEN** a visitor with no account opens the tournament list
- **THEN** every string on it renders in Czech, including the top bar's title, from the first paint

#### Scenario: A previous session's language does not leak
- **WHEN** a fencer whose UI language was English signs out and stays on the tournament list
- **THEN** the list renders in Czech

#### Scenario: Signing in applies the account's language
- **WHEN** that fencer signs in again from the list
- **THEN** the same list is redisplayed in English, their stored preference, with no reload
