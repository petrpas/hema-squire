## 1. Backend: the export's configuration is readable

- [x] 1.1 Add `service_account_email()` to `app/sheets_export.py`: reads `client_email` from the JSON at `settings.google_credentials_path`, returns `None` when the path is unset or the file is unreadable or malformed, and caches the answer for the process (D1).
- [x] 1.2 Add `ExportSheetConfigOut` to `app/schemas.py` — `configured: bool`, `service_account: str | None`.
- [x] 1.3 Add `GET /{slug}/export/sheet-config` to `app/routers/export_api.py`: `def`, not `async def`; gated by `require_console_access` only, not `require_published` (D1). Returns `configured=False, service_account=None` where the server holds no credentials.
- [x] 1.4 Tests in `backend/tests/`: the endpoint states the address from a credentials file written by the test; states `configured=False` with no path set and with a malformed file; is refused for an account without console access; is answered for an unpublished tournament.
- [x] 1.5 `uv run ruff check .` and `uv run basedpyright` clean from `backend/`.

## 2. Frontend: the wizard

- [x] 2.1 Add `exportSheetConfig(slug)` to `src/api.ts` with its response type.
- [x] 2.2 Add `export/ServiceAccountStep.tsx`: states the service account's address in full with a copy control following the `PaymentSlipBlock` pattern — offered only where `navigator.clipboard.writeText` exists, static "zkopírováno" that fades, no toast (D2). States that the server has no Google access where `configured` is false.
- [x] 2.3 Add `export/SheetWizard.tsx`: a `Modal` holding the three numbered steps, the link field validated with `checkUrl` against `TournamentUpdate.output_sheet_url` through `useFieldValidation`/`FieldError`, a confirm that calls `api.updateTournament`, and a dismiss that stores nothing (D2).
- [x] 2.4 The wizard reports a failed save in place rather than closing on it, reusing the `apiErrors` handling the deleted section had.

## 3. Frontend: the Export rail

- [x] 3.1 `ExportPanel.tsx` fetches the sheet config on mount; the destination arrives on that same read rather than by threading `TournamentDetail` through `ExportTables.tsx` (D3).
- [x] 3.2 Pressing export with no stored URL opens the wizard instead of calling the API; confirming a wizard that the export button opened runs the export straight after storing (D3).
- [x] 3.3 Render the destination as a link below the export control whenever a URL is stored and `busy` is false, so it withdraws for the run and returns on both success and failure (D4).
- [x] 3.4 Offer a control that opens the wizard on its own, so a stored address can be changed.
- [x] 3.5a Offer a clearing control beside the stated destination, unconfirmed, shown only where one is stored.
- [x] 3.5 Where `configured` is false, do not render the Sheets export control; state that Google access is not configured, and keep the JSON download (D5).
- [x] 3.6 Drop `export.noUrl` and `export.notConfigured` from the panel's error handling where they are no longer reachable; keep `export.failed`.

## 4. Frontend: Setup loses the section

- [x] 4.1 Delete `src/setup/ExportSheetSection.tsx`, its import and its use in `SetupPanel.tsx`, and its entry in the section-saver registry (D6).
- [x] 4.2 Remove the `setup.exportSheet.*` keys from `i18n/cs.json` and `i18n/en.json`; add the `export.wizard.*` group in both, Czech and English.
- [x] 4.3 Check no test or helper still reaches for the Setup section.

## 5. Design conformance and checks

- [x] 5.1 Read the wizard against the prohibition list in `CLAUDE.md`: no emoji, no filled icons, no shadow, no radius over 2px, no toast entrance animation, no spinner, no second saturated colour, no hex outside `tokens.css`.
- [x] 5.2 Frontend tests: the wizard opens from an export press with no URL and does not call the export API; a stored URL exports without a dialog; the link is present on arrival, absent while busy, present again after both a success and a failure; no export control where the server is unconfigured.
- [x] 5.3 `npm run typecheck` and `npm run check` clean from `frontend/`.
- [x] 5.4 Run the app and walk the procedure once against a real spreadsheet: wizard, copy, share, paste, export, link.
