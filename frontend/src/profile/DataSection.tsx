import { useState } from "react";
import { useTranslation } from "react-i18next";

import { api } from "../api";

/** The account's own data as a file to keep (spec `privacy`, An account
 *  holder can download their own data): the profile, its change history and
 *  the account's registrations with what was credited to them. */
export default function DataSection() {
  const { t } = useTranslation();
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);

  async function download() {
    setBusy(true);
    setFailed(false);
    try {
      const data = await api.accountExport();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = "squire-my-data.json";
      link.click();
      URL.revokeObjectURL(link.href);
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rail-card">
      <h2>{t("privacy.download.title")}</h2>
      <p className="rail-hint">{t("privacy.download.hint")}</p>
      <button type="button" className="secondary" disabled={busy} onClick={() => void download()}>
        {t("privacy.download.action")}
      </button>
      {failed && <p className="login-error">{t("privacy.download.failed")}</p>}
    </section>
  );
}
