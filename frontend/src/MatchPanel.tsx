import { useState } from "react";
import { useTranslation } from "react-i18next";

import { api } from "./api";

export default function MatchPanel({
  slug,
  onChanged,
}: {
  slug: string;
  onChanged: () => void;
}) {
  const { t } = useTranslation();
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState(false);

  async function run() {
    setBusy(true);
    setError(false);
    try {
      const outcome = await api.runMatching(slug);
      setResult(
        t("match.runResult", { matched: outcome.matched, unmatched: outcome.unmatched }),
      );
      onChanged();
    } catch {
      setError(true);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rail-card">
      <h2>{t("match.runTitle")}</h2>
      <p className="rail-hint">{t("match.runHint")}</p>
      <button className="secondary param-save" disabled={busy} onClick={() => void run()}>
        {busy ? t("common.loading") : t("match.run")}
      </button>
      {error && <p className="login-error">{t("match.notConfigured")}</p>}
      {result && <p className="rail-hint">{result}</p>}
    </section>
  );
}
