## Context

The Sheets export has two preconditions and states neither of them until it fails.

The first is the destination: `tournament.output_sheet_url` (`models.py:456`), edited today
by `setup/ExportSheetSection.tsx` on Setup's OTHER tab, saved through that tab's
`useSectionSaver` registry. `POST /api/tournaments/{slug}/export/sheet`
(`export_api.py:76`) answers 422 `output_sheet_url_not_set` when it is absent, which
`ExportPanel.tsx` renders as "Nejdřív nastav URL výstupní tabulky (parametr vlevo)" — a
sentence pointing at a screen the organizer is not on.

The second is sharing. `GspreadSheetsClient` opens the spreadsheet as a **service account**
(`sheets_export.py:266-273`), an identity of its own. The organizer's own access to their
spreadsheet grants that identity nothing, and read access is not enough to write. Nothing
in the console has ever named that identity, so the correct action — share this document
for writing with `…@….iam.gserviceaccount.com` — is unguessable. It is only documented in
`README.md:78` and `deploy/.env.example:12`, both of which are for whoever deploys the
server, not for the organizer who owns the spreadsheet.

The third state is the server's own: with `HEMA_SQUIRE_GOOGLE_CREDENTIALS_PATH` unset the
dependency yields `None` (`sheets_export.py:300-306`) and the endpoint answers 503. The
console offers the button anyway and reports the 503 only afterwards.

This change is drafted against a working tree that already carries the uncommitted
`export-layouts` change, which moved the English tick into `ExportPanel` and gave it an
`onEnglishChange` prop. The wizard builds on that shape.

## Goals / Non-Goals

**Goals:**

- One screen holds the export and everything the export needs.
- The service account's address is stated by the console, sourced from the credentials the
  server actually uses.
- The organizer meets the setup procedure once, before the first export, not as a sequence
  of two error messages.
- A run that has finished is visible as such, without inventing a progress indicator for an
  operation that has no progress to report.

**Non-Goals:**

- No change to what the export writes, to the merge semantics, or to `output_sheet_url`'s
  storage, validation or update API.
- Squire does not create the spreadsheet or share it on the organizer's behalf. That would
  need Drive scopes and an OAuth flow against the organizer's own Google account; the
  service account can only be granted access, never grant it.
- The export does not become a console operation (`console-operations`). It is a
  synchronous request, and this change does not make it survive a reload.
- No verification that the share actually happened before the export runs. The check that
  matters is the export itself.

## Decisions

### D1: The wizard reads the service account from the credentials file, not from a setting

A new read on the export router — `GET /api/tournaments/{slug}/export/sheet-config` — returns
`{ configured: bool, service_account: str | null }`. `sheets_export` gains a function that
opens `settings.google_credentials_path` and returns its `client_email`, cached for the
process since the file does not change under a running server.

*Alternative rejected:* a second env var naming the address. Two sources for one fact, and
the failure mode is silent: organizers share their spreadsheets with an identity that
cannot open them, and the export fails with a permission error naming the other address.

The read is gated by `require_console_access` like every other export read. It is not
`require_published` — configuring the destination is preparation, and gating it behind
publication would put the wizard out of reach exactly when an organizer is setting things
up. The export itself keeps its publication gate.

The file read is blocking I/O, so the endpoint is `def`, not `async def` — the same shape the
rest of the router already has, and what the `ASYNC` ruff rules require.

### D2: The wizard is a `Modal`, its steps a numbered list, its copy the `PaymentSlipBlock` pattern

`src/Modal.tsx` is the only dialog in Squire. The copy control follows
`PaymentSlipBlock.tsx`: offered only where `navigator.clipboard.writeText` exists, since it
is absent over a LAN IP, and a static "zkopírováno" that fades rather than a toast that
animates in.

The link field reuses `checkUrl` against `TournamentUpdate.output_sheet_url` and the
`useFieldValidation` / `FieldError` pair the deleted section used, so the 500-character
limit and the URL shape are enforced exactly as before.

Confirming calls `api.updateTournament(slug, { output_sheet_url: value })` directly. The
wizard is its own dialog with its own confirm control, so it does not join a save-bar
registry — and `setup-navigation` already says OTHER carries no save control.

### D3: Pressing Export without a destination opens the wizard, and the wizard can hand back to the export

`runSheets` checks the destination before calling the API; absent, it opens the wizard
instead.

The destination reaches the panel on the configuration read rather than from
`TournamentDetail`: `ExportPanel` is mounted inside `ExportTables`, which carries no
tournament detail of its own, and threading one down two components to deliver a single
string is a worse seam than one endpoint answering the whole card. `ExportSheetConfigOut`
therefore carries `output_sheet_url` alongside `configured` and `service_account`. Confirming the wizard stores the URL and — when
the wizard was opened *by* the export button rather than by its own control — runs the export
immediately, so the organizer's press is honoured rather than swallowed.

*Alternative rejected:* let the 422 open the wizard. That is a round-trip to learn something
the client already knows, and it couples the dialog to an error path that also fires for
reasons the wizard cannot fix.

The 422 stays on the server. It is the guarantee behind the behaviour, not something an
organizer meets, and it is what protects a direct API call.

### D4: The destination link is rendered from the stored URL, withdrawn by `busy`

The link is `output_sheet_url` rendered as an anchor, shown whenever the tournament has one
and `busy` is false. The panel holds it in the configuration state and updates that state
when the wizard saves, so the link follows an address the organizer has just changed
without a second read. That gives the owner-chosen behaviour — present on arrival, gone for the
run, back when the run concludes — from one existing piece of state, with no export-result
plumbing.

The export response (`{worksheets, fencers}`) carries no URL and does not need to: it wrote to
the spreadsheet the tournament names, which is the one being linked.

Because the link's absence is the only signal that a run is in flight, it must not be
accompanied by a spinner or an animated bar — the design prohibitions rule those out anyway.
The button's label change to `common.loading` and the link's withdrawal are the whole of it.

### D5: No credentials, no export control

`ExportPanel` reads the config once on mount. With `configured: false` the Sheets button is
not rendered at all and the card states that Google access is not configured; the JSON
download, which touches no Google service, stays. The wizard, if opened, replaces its second
step with the same statement — the organizer can still record a link, it simply will not be
written to until the server is configured.

This turns a 503 discovered by pressing a button into a state the card reads out. The 503
remains on the server for a direct call.

### D6: `ExportSheetSection` is deleted rather than left hidden

The file goes, its import and use in `SetupPanel.tsx:225` go, and its `setup.exportSheet.*`
i18n keys go with it. The delta to `setup-navigation` is what records that OTHER lost a
section; leaving a dead section behind would leave the spec and the code disagreeing about
where the field lives.

### D7: Component seams

`ExportPanel.tsx` is already near its limit with the English tick, two buttons and the
message lines. The wizard goes under `src/export/`, matching the convention that a panel's
parts live in a directory named after it:

- `export/SheetWizard.tsx` — the modal, the three steps, the confirm.
- `export/ServiceAccountStep.tsx` — step 2, the address and its copy control, or the
  not-configured statement. Its own file because it owns the clipboard state and the
  fade-out.

`ExportPanel` keeps the config fetch, the destination link and the decision of when the
wizard opens.

## Risks / Trade-offs

- **The credentials JSON is read on a request path** → It is read once per process and the
  result cached; a malformed or unreadable file yields `configured: false` rather than a 500,
  which is the same thing the organizer sees today when the path is unset.
- **The service account's address is exposed to console members** → It is an operational
  address, not a secret; knowing it grants nothing without the private key. It is stated only
  inside the wizard, to accounts that already have console access to the tournament.
- **An organizer can enter a link to a spreadsheet they never shared** → The export then fails
  with a permission error from Google. The wizard reduces this to a mistake rather than the
  default path, but cannot prevent it without a write probe, which would mean writing to the
  organizer's spreadsheet to find out whether it can be written to.
- **The link's withdrawal is a subtle signal** → It is paired with the button's disabled state
  and its label change, both of which are already there. Where the export finishes fast the
  flicker is brief; the completion message states the outcome regardless.
- **Direct conflict with the working tree's `export-layouts` change** → Resolved: that
  change was committed and archived (8428ba7) before this one was implemented.
