import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { type DedupItem, api } from "./api";

export default function DedupPanel({
  slug,
  onChanged,
}: {
  slug: string;
  onChanged: () => void;
}) {
  const { t } = useTranslation();
  const [queue, setQueue] = useState<DedupItem[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(false);

  const load = useCallback(() => {
    api.dedupQueue(slug).then(setQueue, () => setQueue([]));
  }, [slug]);

  useEffect(load, [load]);

  async function run() {
    setBusy(true);
    setError(false);
    try {
      await api.runDedup(slug);
      load();
      onChanged();
    } catch {
      setError(true);
    } finally {
      setBusy(false);
    }
  }

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
      <button className="secondary param-save" disabled={busy} onClick={() => void run()}>
        {busy ? t("common.loading") : t("dedup.run")}
      </button>
      {error && <p className="login-error">{t("dedup.notConfigured")}</p>}
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
