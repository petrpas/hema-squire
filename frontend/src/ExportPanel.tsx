import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, api, getToken } from "./api";

/** Whether the English tick is offered. Not to an organizer already working in
 *  English, where it would be a tick that changes nothing. */
export function offersEnglishTick(language: string): boolean {
  return !language.startsWith("en");
}

/** The Export phase's rail card for what leaves the phase: the English tick,
 *  the canonical JSON document and the write to the organizer's spreadsheet.
 *  The tick sits here rather than on a tab's card because it governs the copy
 *  and the spreadsheet write alike, not what one tab shows. */
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

  async function runSheets() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const result = await api.exportSheet(slug, english);
      setMessage(t("export.done", { fencers: result.fencers }));
    } catch (failure) {
      if (failure instanceof ApiError && failure.status === 422) {
        setError(t("export.noUrl"));
      } else if (failure instanceof ApiError && failure.status === 503) {
        setError(t("export.notConfigured"));
      } else {
        setError(t("export.failed"));
      }
    } finally {
      setBusy(false);
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
      <button
        type="button"
        className="secondary param-save"
        disabled={busy}
        onClick={() => void runSheets()}
      >
        {busy ? t("common.loading") : t("export.runSheets")}
      </button>
      <button type="button" className="secondary param-save" onClick={() => void downloadJson()}>
        {t("export.downloadJson")}
      </button>
      {message && <p className="rail-hint">{message}</p>}
      {error && <p className="login-error">{error}</p>}
    </section>
  );
}
