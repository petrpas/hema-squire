import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { type HRStatus, api } from "./api";
import { conclusionText, kindName } from "./operationText";
import type { OperationsView } from "./useOperations";

export default function MatchPanel({
  slug,
  operations,
  pending,
  onChanged,
}: {
  slug: string;
  operations: OperationsView;
  /** Rows still owing the organizer a verdict — the queue this phase holds
   *  (spec `etl-console`, The ledger idiom). */
  pending: number;
  onChanged: () => void;
}) {
  const { t } = useTranslation();
  const [error, setError] = useState(false);
  const [hrStatus, setHrStatus] = useState<HRStatus | null>(null);
  // The index refresh is not a tournament operation — it belongs to the
  // deployment, not to this tournament — so it keeps its own state and is not
  // subject to the one-at-a-time lock.
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
    setError(false);
    try {
      await api.runMatching(slug);
      operations.refresh();
      onChanged();
    } catch {
      setError(true);
    }
  }

  const running = operations.running;
  const match = operations.concluded.match;
  const conclusion = match ? conclusionText(t, match) : null;
  const outcome = match?.status === "done" ? match.outcome : null;

  return (
    <section className="rail-card">
      <h2>
        {t("match.runTitle")} <span className="rail-count">({pending})</span>
      </h2>
      <p className="rail-hint">{t("match.runHint")}</p>
      <button
        className="secondary param-save"
        disabled={running !== null}
        onClick={() => void run()}
      >
        {running?.kind === "match" ? t("common.loading") : t("match.run")}
      </button>
      {running !== null && running.kind !== "match" && (
        <p className="rail-hint">{t("operation.busy", { kind: kindName(t, running.kind) })}</p>
      )}
      {error && <p className="login-error">{t("match.notConfigured")}</p>}
      {match?.status === "failed" && <p className="login-error">{conclusion}</p>}
      {match?.status === "interrupted" && <p className="rail-hint">{conclusion}</p>}
      {outcome && (
        <p className="rail-hint">
          {t("match.runResult", {
            matched: outcome.matched as number,
            unmatched: outcome.unmatched as number,
          })}
        </p>
      )}

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
