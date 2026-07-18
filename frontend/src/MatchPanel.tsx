import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { type HRStatus, api } from "./api";

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
  const [hrStatus, setHrStatus] = useState<HRStatus | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshError, setRefreshError] = useState(false);

  const loadStatus = useCallback(() => {
    api.hrStatus().then(setHrStatus, () => setHrStatus(null));
  }, []);

  useEffect(loadStatus, [loadStatus]);

  async function refreshIndex() {
    setRefreshing(true);
    setRefreshError(false);
    try {
      await api.hrRefresh();
      loadStatus();
    } catch {
      setRefreshError(true);
      loadStatus(); // rejected refreshes still update the diagnostics line
    } finally {
      setRefreshing(false);
    }
  }

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

      <h2 className="rail-subhead">{t("match.indexTitle")}</h2>
      <p className="rail-hint">
        {hrStatus === null
          ? t("common.loading")
          : t("match.indexStatus", { fighters: hrStatus.fighters })}
      </p>
      <button
        className="secondary param-save"
        disabled={refreshing}
        onClick={() => void refreshIndex()}
      >
        {refreshing ? t("common.loading") : t("match.indexRefresh")}
      </button>
      {refreshError && <p className="login-error">{t("match.indexRefreshFailed")}</p>}
    </section>
  );
}
