import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, api, getToken } from "./api";

export default function ExportPanel({ slug }: { slug: string }) {
  const { t } = useTranslation();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function runSheets() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const result = await api.exportSheet(slug);
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
      <button className="secondary param-save" disabled={busy} onClick={() => void runSheets()}>
        {busy ? t("common.loading") : t("export.runSheets")}
      </button>
      <button className="secondary param-save" onClick={() => void downloadJson()}>
        {t("export.downloadJson")}
      </button>
      {message && <p className="rail-hint">{message}</p>}
      {error && <p className="login-error">{error}</p>}
    </section>
  );
}
