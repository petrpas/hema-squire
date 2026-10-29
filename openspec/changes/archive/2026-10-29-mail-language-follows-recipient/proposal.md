## Why

The first registration on production sent its confirmation in Czech to an account that had chosen English. That is the spec working as written: every tournament mail goes in the tournament's communication language. The creation dialog never sends a language, though, so every tournament is `cs`, and the "promise" that language is meant to make is kept for nobody. HEMA tournaments draw fencers from several countries, and a fencer already tells Squire which language they read when they sign up or fill in the guest form.

## What Changes

- A mail about a tournament SHALL go in **its recipient's language** when that is a bundled locale, falling back to the tournament's communication language. Text the organizer wrote (names, description, disciplines) stays as written; only Squire's text around it is translated. Account mails (verification, password reset and change) already follow the account and are unchanged.
- A fencer record created without a choice of its own — a substitute, a row imported from a table with no language column — SHALL take the tournament's communication language when it is created, instead of the column default `en`. Hand entry already does this. With that, a record's language is always either chosen or the tournament's, and the mail rule needs no notion of "chosen".
- **BREAKING (spec):** the communication language becomes an **editable setting**, on Setup's `OTHER` tab as its own section with its own control. The creation dialog does not offer it; a new tournament takes the creating organizer's UI language instead of a fixed `cs`. The requirement that it "SHALL NOT be exposed as an editable setting" is removed — it guarded a value that governed every mail, and the value now governs only the fallback.
- A change of the language applies to mail sent from then on. Mail already sent, and records that already took the earlier language, are not rewritten.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `localization`: mails follow the recipient's language with the tournament's as fallback; the communication language is editable and defaults to the creator's language; records created without a language take the tournament's; the parity paragraph and the English-confirmation scenario are restated for the recipient.
- `setup-navigation`: `OTHER` carries the communication language section beside the mode section, console team access and the danger zone.

## Impact

- `backend/app/emails.py`: every tournament send resolves its language from the recipient record (one helper), not `tournament.language`; a send addressed to two people (substitution) resolves each separately.
- `backend/app/substitution.py`, `backend/app/issuing.py`: fencer records created there take `tournament.language` when no language is given.
- `backend/app/schemas.py` / `routers/tournaments.py`: `TournamentCreate` loses `language` and the tournament takes the caller's `fencer.language`; `TournamentUpdate.language` is validated against the bundled locales and is refused to anyone but the tournament owner, matching `OTHER`'s owner-only placement.
- `frontend/src/setup/`: a new `LanguageSection.tsx` on `OTHER`; locale keys in `cs`/`en`.
- No migration: existing tournaments keep their stored language, and production holds no real registrations yet.
