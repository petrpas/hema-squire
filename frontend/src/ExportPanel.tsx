import { IconBraces, IconExternalLink, IconLinkOff, IconTableExport } from "@tabler/icons-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { api, type ExportSheetConfig, getToken } from "./api";
import HintedAction from "./export/HintedAction";
import SheetWizard from "./export/SheetWizard";

/** Whether the English tick is offered. Not to an organizer already working in
 *  English, where it would be a tick that changes nothing. */
export function offersEnglishTick(language: string): boolean {
  return !language.startsWith("en");
}

/** The Export phase's rail card for what leaves the phase: the English tick,
 *  the canonical JSON document and the write to the organizer's spreadsheet.
 *  The tick sits here rather than on a tab's card because it governs the copy
 *  and the spreadsheet write alike, not what one tab shows.
 *
 *  The destination lives here too, as the dialog that states how to prepare
 *  one. It used to be a field in Setup two tabs away, which is where an
 *  organizer was sent by an error message after pressing the button on this
 *  card — and even having found it, nothing said that the spreadsheet has to be
 *  shared with the service account for the export to write anything. */
export default function ExportPanel({
  slug,
  english,
  onEnglishChange,
}: {
  slug: string;
  english: boolean;
  onEnglishChange: (english: boolean) => void;
}) {
  const { t, i18n } = useTranslation();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [config, setConfig] = useState<ExportSheetConfig | null>(null);
  // The wizard opens only from an export pressed with no destination stored,
  // so confirming it always owes the organizer the export they pressed for. A
  // destination is changed by forgetting it and exporting again.
  const [wizard, setWizard] = useState(false);

  useEffect(() => {
    void api.exportSheetConfig(slug).then(setConfig);
  }, [slug]);

  async function exportNow() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const result = await api.exportSheet(slug, english);
      setMessage(t("export.done", { fencers: result.fencers }));
    } catch {
      setError(t("export.failed"));
    } finally {
      setBusy(false);
    }
  }

  /** A destination the console does not have is the next step, not a mistake:
   *  the dialog opens instead of an error, and the press is honoured once the
   *  address is stored. The server keeps its refusal for an address-less
   *  export; it is the guarantee behind this, not something an organizer is
   *  meant to meet. */
  function runSheets() {
    if (config === null) return;
    if (config.output_sheet_url === null) {
      setWizard(true);
      return;
    }
    void exportNow();
  }

  function saved(url: string) {
    setConfig((current) => (current === null ? current : { ...current, output_sheet_url: url }));
    setWizard(false);
    void exportNow();
  }

  /** Forgets the destination, so the next export asks for one again.
   *
   *  Unconfirmed on purpose. It destroys nothing — the spreadsheet and
   *  everything written into it stay where they are — and what it costs to
   *  undo is pasting a link the organizer still has. A confirmation here would
   *  weigh more than the act. */
  async function forget() {
    setError(null);
    setMessage(null);
    try {
      await api.updateTournament(slug, { output_sheet_url: null });
      setConfig((current) => (current === null ? current : { ...current, output_sheet_url: null }));
    } catch {
      setError(t("export.failed"));
    }
  }

  async function downloadJson() {
    const response = await fetch(`/api/tournaments/${slug}/export/json`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    });
    const blob = await response.blob();
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `${slug}-export.json`;
    link.click();
    URL.revokeObjectURL(link.href);
  }

  const destination = config?.output_sheet_url ?? null;

  return (
    <section className="rail-card">
      <h2>{t("export.title")}</h2>
      {/* Where the server holds no credentials the export cannot write at all.
          Saying so is better than offering a button that answers 503 once
          pressed, which is what the card did before. */}
      {config !== null && !config.configured && <p className="rail-hint">{t("export.noGoogle")}</p>}
      <div className="export-actions">
        {config?.configured === true && (
          <HintedAction hint={t("export.hints.runSheets")}>
            {(hintId) => (
              <button
                type="button"
                className="icon-action"
                disabled={busy}
                aria-describedby={hintId}
                onClick={runSheets}
              >
                <IconTableExport size={18} stroke={1.5} />
                <span className="visually-hidden">{t("export.runSheets")}</span>
              </button>
            )}
          </HintedAction>
        )}
        {/* Absent while the run is in flight, back when it concludes — on a
            failure too, since the spreadsheet is still where it is. */}
        {config?.configured === true && destination !== null && !busy && (
          <>
            <HintedAction hint={t("export.hints.sheetLink")}>
              {(hintId) => (
                <a
                  className="icon-action export-open"
                  href={destination}
                  target="_blank"
                  rel="noreferrer"
                  aria-describedby={hintId}
                >
                  <IconExternalLink size={18} stroke={1.5} />
                  <span className="visually-hidden">{t("export.sheetLink")}</span>
                </a>
              )}
            </HintedAction>
            <HintedAction hint={t("export.hints.forgetSheet")}>
              {(hintId) => (
                <button
                  type="button"
                  className="icon-action"
                  aria-describedby={hintId}
                  onClick={() => void forget()}
                >
                  <IconLinkOff size={18} stroke={1.5} />
                  <span className="visually-hidden">{t("export.forgetSheet")}</span>
                </button>
              )}
            </HintedAction>
          </>
        )}
        {/* the canonical document touches no Google service, so it is offered
            whether or not the server can write a spreadsheet */}
        <HintedAction hint={t("export.hints.downloadJson")}>
          {(hintId) => (
            <button
              type="button"
              className="icon-action"
              aria-describedby={hintId}
              onClick={() => void downloadJson()}
            >
              <IconBraces size={18} stroke={1.5} />
              <span className="visually-hidden">{t("export.downloadJson")}</span>
            </button>
          )}
        </HintedAction>
      </div>
      {offersEnglishTick(i18n.language) && (
        <label className="rail-check">
          <input
            type="checkbox"
            checked={english}
            onChange={(event) => onEnglishChange(event.currentTarget.checked)}
          />
          <span>{t("export.english")}</span>
        </label>
      )}
      {message && <p className="rail-hint">{message}</p>}
      {error && <p className="login-error">{error}</p>}
      {wizard && config?.service_account != null && (
        <SheetWizard
          slug={slug}
          account={config.service_account}
          onSaved={saved}
          onClose={() => setWizard(false)}
        />
      )}
    </section>
  );
}
