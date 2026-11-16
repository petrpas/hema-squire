## 1. Senders

- [x] 1.1 `send_cancelled_by_organizer` returns without sending when the tournament's `registrations_kept_by` is not `SQUIRE`; its docstring names the manual tournament beside the hand entry and the missing address
- [x] 1.2 `send_team_cancelled` likewise, returning `False` so the console states that nobody was told
- [x] 1.3 Tests in `test_organizer_cancel.py`: on a manual tournament, one imported and one hand-entered registration, both with addresses, are cancelled and the mailbox stays empty; the automatic-tournament mail tests stay as they are
- [x] 1.4 Team-cancellation test: a team cancelled on a manual tournament sends nothing and reports `notified` false

## 2. Dialogs

- [x] 2.1 `CancelRegistrationDialog` takes `automatic` from its caller; on a manual tournament it drops the mail sentence and the note field and confirms with no note
- [x] 2.2 The team-cancellation confirmation drops its mail sentence on a manual tournament
- [x] 2.3 Component tests for both dialogs on a manual tournament

## 3. Checks

- [x] 3.1 `uv run ruff check .`, `uv run basedpyright`, scoped pytest
- [x] 3.2 `npm run typecheck`, `npm run check`, scoped vitest
