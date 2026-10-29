## 1. Records carry a meaningful language

- [x] 1.1 `backend/app/substitution.py`: the fencer record created for a substitute takes `tournament.language`
- [x] 1.2 `backend/app/issuing.py`: an imported row's language is kept when it is a bundled locale, otherwise the record takes `tournament.language` (replacing `or "en"`)
- [x] 1.3 Tests: substitute on a Czech tournament carries `cs`; import without a language column on an English tournament carries `en`; a row stating `cs` keeps it

## 2. Mail resolves the recipient's language

- [x] 2.1 `backend/app/emails.py`: add `mail_language(tournament, fencer)` (D1) and route every tournament send through it, replacing `lang = tournament.language`
- [x] 2.2 Lines composed ahead of a send take the resolved language as an argument: `send_team_promoted`'s label, `_amount_text`, and any other helper reading `tournament.language` directly (D3)
- [x] 2.3 `send_substitution` and any send looping over recipients resolve per recipient (D4)
- [x] 2.4 Test that enumerates the tournament `send_*` functions and asserts an English recipient on a Czech tournament gets an English subject and body; a recipient with an unbundled language gets the tournament's
- [x] 2.5 Test: a substitution mailed to a Czech and an English party arrives in each one's language

## 3. The communication language is a setting

- [x] 3.1 `backend/app/schemas.py`: drop `TournamentCreate.language`; validate `TournamentUpdate.language` against `catalog.available()`
- [x] 3.2 `backend/app/routers/tournaments.py`: creation sets `language=fencer.language`; `PATCH` refuses a changed `language` with 403 unless the caller owns the tournament (D5); the tenant-isolation test stays green
- [x] 3.3 Tests: a tournament created by an English organizer is `en`; a console team member's language change is refused, the owner's applies
- [x] 3.4 `frontend/src/setup/LanguageSection.tsx` on `OTHER` after `SettingsSection`: a select of the bundled languages applying at once, with a help hint saying it is the language for fencers whose own language Squire does not know; `cs`/`en` locale keys
- [x] 3.5 Frontend test: the section shows the stored language and a change is sent without a tab save
- [x] 3.6 `npm run typecheck`, `npm run check`; `uv run ruff check .`, `uv run basedpyright`; scoped pytest
