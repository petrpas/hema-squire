## 1. Backend

- [x] 1.1 Extract the cancellation (state, `cancelled_at`, refund state) into one helper; `my-registration/cancel` calls it unchanged
- [x] 1.2 `POST /api/tournaments/{slug}/registrations/{registration_id}/cancel` with optional `note`: console access, published only, 409 `registration_not_live` for a cancelled or expired registration
- [x] 1.3 `emails.send_cancelled_by_organizer` with the substitution's suppression (entered by hand, no address); cs/en catalog strings; sent after commit
- [x] 1.4 `rules.create_rule`: refuse `row_delete` on a live registration's row with 409 `row_has_registration`
- [x] 1.5 `sheet.base_rows`: keep a cancelled registration's source row out (fencer and organizer cancellations alike)

## 2. Backend tests

- [x] 2.1 Organizer cancellation frees the seat, promotes nobody, stops reminders and expiry, records refund state like the fencer's
- [x] 2.2 Mail: sent with note to an in-app registration; not sent for a hand-entered one or one with no address; not sent and refused for an expired one
- [x] 2.3 Deletion refused on a live registration's row; allowed on an expired one and on an unissued imported row; restore of a pre-existing deleted row still works
- [x] 2.4 Manual mode: cancelled issued registration's row is neither listed nor reissued on the next intake
- [x] 2.5 Foreign organizer refused (tenant sweep picks the new route up; add its body)
- [x] 2.6 `uv run ruff check .` and `uv run basedpyright` clean

## 3. Frontend

- [x] 3.1 `api.ts`: `cancelRegistrationAsOrganizer(slug, id, note)`
- [x] 3.2 Fencers phase: Zrušit registraci in Smazat's slot on a live registration's row; Smazat/Obnovit elsewhere as before
- [x] 3.3 Confirmation `Modal` (`src/Modal.tsx`): what happens, whether a mail goes, refund line where paid, optional note, destructive confirm; refresh after
- [x] 3.4 i18n cs/en
- [x] 3.5 Tests: the action shown per row kind, the dialog's statements, the call made
- [x] 3.6 `npm run typecheck`, `npm run check`, `npm test` clean
