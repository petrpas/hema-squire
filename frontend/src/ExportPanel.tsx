import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { api, type ExportSheetConfig, getToken } from "./api";
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
  // `pending` marks a wizard the export button opened, as against one opened to
  // change an address that already works: only the first owes the organizer the
  // export they pressed for.
  const [wizard, setWizard] = useState<"closed" | "open" | "pending">("closed");

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
      setWizard("pending");
      return;
    }
    void exportNow();
  }

  function saved(url: string) {
    const owed = wizard === "pending";
    setConfig((current) => (current === null ? current : { ...current, output_sheet_url: url }));
    setWizard("closed");
    if (owed) void exportNow();
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
      <p className="rail-hint">{t("export.hint")}</p>
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
      {/* Where the server holds no credentials the export cannot write at all.
          Saying so is better than offering a button that answers 503 once
          pressed, which is what the card did before. */}
      {config !== null && !config.configured && <p className="rail-hint">{t("export.noGoogle")}</p>}
      {config?.configured === true && (
        <>
          <button
            type="button"
            className="secondary param-save"
            disabled={busy}
            onClick={runSheets}
          >
            {busy ? t("common.loading") : t("export.runSheets")}
          </button>
          {/* Absent while the run is in flight, back when it concludes —
              on a failure too, since the spreadsheet is still where it is. */}
          {destination !== null && !busy && (
            <p className="export-destination">
              <a href={destination} target="_blank" rel="noreferrer">
                {t("export.sheetLink")}
              </a>
              {/* Beside the thing it forgets, not among the card's actions:
                  it is about this destination, and it reads as a footnote to
                  the link rather than as a fourth thing the card does. */}
              <button type="button" className="link-button" onClick={() => void forget()}>
                {t("export.forgetSheet")}
              </button>
            </p>
          )}
        </>
      )}
      <button type="button" className="secondary param-save" onClick={() => void downloadJson()}>
        {t("export.downloadJson")}
      </button>
      <button type="button" className="link-button" onClick={() => setWizard("open")}>
        {destination === null ? t("export.wizard.open") : t("export.wizard.change")}
      </button>
      {message && <p className="rail-hint">{message}</p>}
      {error && <p className="login-error">{error}</p>}
      {wizard !== "closed" && config !== null && (
        <SheetWizard
          slug={slug}
          account={config.service_account}
          current={config.output_sheet_url}
          exports={wizard === "pending"}
          onSaved={saved}
          onClose={() => setWizard("closed")}
        />
      )}
    </section>
  );
}
