## Context

Every tournament send in `backend/app/emails.py` reads `lang = tournament.language` (about twenty sends). Account mails read the account's language (`send_signup_verification`, `send_password_reset`, `send_password_changed`). `Tournament.language` defaults to `cs` in the model and in `TournamentCreate`, and `TournamentCreateDialog.tsx` never sends one, so every tournament is Czech. `TournamentUpdate.language` already exists but is unvalidated and offered by no screen.

Fencer records get their language from five places: signup and the guest form (the person's choice), hand entry (`tournament.language`), substitution (nothing — the column default `en`), and import (`row.get("language") or "en"`).

## Goals / Non-Goals

**Goals:**
- A tournament mail reads in its recipient's language when Squire has it.
- A fencer record's language is always either the person's choice or the tournament's, never an accidental `en`.
- The communication language is settable after creation, defaulting to the creator's language.

**Non-Goals:**
- Translating organizer-authored text.
- Generated documents (roster PDF, exports) — they already follow the reader or an explicit tick.
- Rewriting stored languages on existing records; production holds no real ones.

## Decisions

**D1. One resolver, keyed on the recipient record.** `mail_language(tournament, fencer) -> str` returns `fencer.language` when it is in `catalog.available()`, else `tournament.language`. Every tournament send calls it once, with the record the message is addressed to, and passes the result to everything it composes. Alternative: a nullable `Fencer.language` meaning "not chosen". Rejected because D2 makes the record's language always meaningful, so the extra state would only add a third case to every read.

**D2. Fill the language at creation, not at send.** Substitution and import set `language=tournament.language` when none (or an unbundled one) is given, as hand entry already does. The record then carries the language its first mail used, which stays true if the tournament's language later changes — a substitute does not silently switch languages mid-season.

**D3. Composed lines take the resolved language.** `send_team_promoted` builds its team label in `tournament.language` and hands it to `send_promoted`. Lines built ahead of a send take the same resolved language as an argument, so one message is never half in one language and half in another. The same goes for `_amount_text`, which reads `tournament.language` directly today.

**D4. Multi-recipient sends resolve per recipient.** `send_substitution` mails both parties; each build resolves its own language. Wherever one send loops over recipients, the resolver goes inside the loop.

**D5. The setting lives on `OTHER`, gated to the owner.** It gets its own section (`LanguageSection.tsx`) with a select that applies at once through `PATCH /api/tournaments/{slug}` — `OTHER`'s sections carry their own actions, and the tab has no save control. `OTHER` is owner-only, so the API refuses a changed `language` from anyone but the owner (403), rather than leaving console team members a write the UI never offers them. The value is validated against `catalog.available()`, like the account language. It is not added to `TournamentSettingsDialog`: that surface is also the creation dialog's second panel, and the owner decided creation does not ask.

**D6. The creator's language at creation.** `TournamentCreate` drops `language`, and `create_tournament` sets `language=fencer.language`. The account language is already validated against the bundled locales, so no fallback is needed there.

## Risks / Trade-offs

- [A send missed by the sweep keeps `tournament.language`] → a test enumerates the `send_*` functions taking a `Fencer` or a `Registration` and asserts each one, given an English recipient on a Czech tournament, produces an English subject. A new send joins the test by existing.
- [The organizer expects the tournament's language to force all mail] → the setting's help hint states that it is the language for fencers whose own language Squire does not know.
- [Changing the language does not move records it already seeded] → intended (D2); stated in the spec.

## Migration Plan

No data migration. Existing tournaments keep their stored `cs`; the owner can now change it on `OTHER`. Deploys with the next ordinary deploy.
