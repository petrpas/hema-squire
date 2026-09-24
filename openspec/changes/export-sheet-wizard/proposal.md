## Why

The address the Sheets export writes to lives in Setup → OTHER, three clicks and a tab
away from the button that uses it. An organizer who presses **Export do Google Sheets**
without one is told to go set a parameter "vlevo" that is not on the screen they are on —
and even having found the field, nothing tells them the part that actually decides whether
the export works: the spreadsheet must be shared for writing with the service account's
own address, which the console has never stated anywhere.

The result is that the first export of every tournament fails twice — once for the missing
URL, once for the missing share — and neither failure names what to do.

## What Changes

- The export sheet address **moves out of Setup** into the Export phase's rail, beside the
  button that uses it. **BREAKING** for anyone who navigates to it: the OTHER tab no longer
  carries the field.
- Setting it becomes a small **three-step wizard** in a modal rather than a bare text field:
  create an empty spreadsheet, share it for writing with the service account's address
  (stated, with a copy action), paste the link.
- The service account's address becomes **readable by the console**, from the credentials
  the server is configured with. It is stated only inside the wizard, to an organizer of
  that tournament.
- Pressing **Export** with no address stored **opens the wizard** instead of reporting a
  parameter error. Once an address is stored, export runs straight through and never asks
  again; the wizard stays reachable by its own control for changing the address later.
- The rail states the destination as a **link** whenever the tournament has one. The link
  is withdrawn while an export is running and returns when it finishes, so the organizer
  can see that the run is over and open what it wrote.
- Where the server has no Google credentials at all, the wizard says so in place of step 2
  and the export control is not offered — the present behaviour is a 503 discovered only
  after pressing the button.

## Capabilities

### New Capabilities

_None._ The wizard is a new surface for an existing capability, not a new one.

### Modified Capabilities

- `data-export`: the export's destination becomes a stated, guided setting — where it is
  configured, what the organizer is told in order to configure it correctly, when the
  console asks for it, and how the written spreadsheet is offered back as a link.
- `setup-navigation`: OTHER loses the export sheet address, and the rule that no tournament
  parameter is offered in a phase panel gains its one stated exception — a destination for
  a tool, not a fact about the tournament.

## Impact

- Frontend: `ExportPanel.tsx` gains the wizard, the destination link and the busy
  withdrawal; a new wizard component and its steps under `src/export/`;
  `setup/ExportSheetSection.tsx` is deleted and its registration in `SetupPanel.tsx`
  removed, along with its save-bar participation.
- Backend: `export_api.py` gains a read of the export's configuration — whether Google
  access is configured and, when it is, the service account's address —
  read from the credentials JSON in `sheets_export.py`. `POST /export/sheet` keeps its 422
  for a missing address; the console simply stops reaching it.
- `tournament.output_sheet_url` is unchanged in storage, validation and API. Nothing
  migrates.
- i18n: the `setup.exportSheet.*` keys give way to an `export.wizard.*` group, Czech and
  English.
