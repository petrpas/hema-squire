import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { type DedupItem, api } from "./api";
import { conclusionText, kindName } from "./operationText";
import type { OperationsView } from "./useOperations";

export default function DedupPanel({
  slug,
  operations,
  onChanged,
}: {
  slug: string;
  operations: OperationsView;
  onChanged: () => void;
}) {
  const { t } = useTranslation();
  const [queue, setQueue] = useState<DedupItem[]>([]);
  const [error, setError] = useState(false);

  const load = useCallback(() => {
    api.dedupQueue(slug).then(setQueue, () => setQueue([]));
  }, [slug]);

  useEffect(load, [load]);

  async function run() {
    setError(false);
    try {
      await api.runDedup(slug);
      operations.refresh();
      onChanged();
    } catch {
      setError(true);
    }
  }

  // the queue is what the last run left behind, so it is reloaded when one
  // lands rather than only when this panel mounts
  const dedup = operations.concluded.dedup;
  useEffect(load, [load, dedup?.id]);

  async function decide(key: string, accept: boolean) {
    await api.dedupDecide(slug, key, accept);
    load();
    onChanged();
  }

  return (
    <section className="rail-card">
      <h2>
        {t("dedup.title")} <span className="rail-count">({queue.length})</span>
      </h2>
      <button
        className="secondary param-save"
        disabled={operations.running !== null}
        onClick={() => void run()}
      >
        {operations.running?.kind === "dedup" ? t("common.loading") : t("dedup.run")}
      </button>
      {operations.running !== null && operations.running.kind !== "dedup" && (
        <p className="rail-hint">
          {t("operation.busy", { kind: kindName(t, operations.running.kind) })}
        </p>
      )}
      {error && <p className="login-error">{t("dedup.notConfigured")}</p>}
      {dedup?.status === "failed" && (
        <p className="login-error">{conclusionText(t, dedup)}</p>
      )}
      {dedup?.status === "interrupted" && (
        <p className="rail-hint">{conclusionText(t, dedup)}</p>
      )}
      {queue.length === 0 ? (
        <p className="rail-hint">{t("dedup.empty")}</p>
      ) : (
        <ul className="edits-list">
          {queue.map((item) => (
            <li key={item.key} className="edit-entry">
              <div className="edit-body">
                <div>{item.rows.map((row) => row.name).join(" + ")}</div>
                <div className="edit-meta">
                  {t(item.kind === "same_id" ? "dedup.sameId" : "dedup.likely")}
                  {item.note ? ` · ${item.note}` : ""}
                </div>
                <div className="dedup-actions">
                  <button className="secondary" onClick={() => void decide(item.key, true)}>
                    {t("dedup.accept")}
                  </button>
                  <button className="row-action" onClick={() => void decide(item.key, false)}>
                    {t("dedup.reject")}
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
