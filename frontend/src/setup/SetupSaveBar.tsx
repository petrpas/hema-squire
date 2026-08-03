import { useEffect, useState, useSyncExternalStore } from "react";
import { useTranslation } from "react-i18next";

import {
  PriceChangeWarning,
  type SaverRegistry,
  type SaveOutcome,
  type SetupTab,
  usePriceChangeGuard,
} from "./shared";

export function SetupSaveBar({
  tab,
  registry,
  hasRegistrations,
  onSaved,
}: {
  tab: SetupTab;
  registry: SaverRegistry;
  hasRegistrations: boolean;
  onSaved: () => void;
}) {
  const { t } = useTranslation();
  useSyncExternalStore(registry.subscribe, registry.getVersion);
  const [busy, setBusy] = useState(false);
  const [report, setReport] = useState<{
    written: number;
    total: number;
    failures: SaveOutcome[];
  } | null>(null);

  const entries = registry.forTab(tab);
  const pendingCount = entries.reduce((sum, entry) => sum + entry.saver.pendingCount, 0);
  const { guard, confirming, confirm, cancel } = usePriceChangeGuard();
  const [invalidCount, setInvalidCount] = useState(0);

  useEffect(() => {
    setReport(null);
    setInvalidCount(0);
  }, [tab]);

  async function doSave() {
    // Re-read the registry live rather than trusting `entries` captured at
    // the last render: notify only fires when a saver's pendingCount or
    // touchesPrice actually changes, so a section that has been dirty for a
    // while (typing more into an already-dirty field, editing another field
    // on an already-dirty row) never re-renders this bar — its closure here
    // would otherwise be stale and flush() would write an old value.
    const liveEntries = registry.forTab(tab);
    setBusy(true);
    setReport(null);
    try {
      const outcomes: SaveOutcome[] = [];
      for (const entry of liveEntries) {
        if (entry.saver.pendingCount === 0) continue;
        outcomes.push(...(await entry.saver.flush()));
      }
      onSaved();
      const failures = outcomes.filter((outcome) => outcome.error !== null);
      setReport({ written: outcomes.length - failures.length, total: outcomes.length, failures });
    } finally {
      setBusy(false);
    }
  }

  function attemptSave() {
    const liveEntries = registry.forTab(tab);
    let total = 0;
    for (const entry of liveEntries) {
      total += entry.saver.validate();
    }
    setInvalidCount(total);
    if (total > 0) return;
    const touchesPriceNow = liveEntries.some(
      (entry) => entry.saver.touchesPrice && entry.saver.pendingCount > 0,
    );
    guard(touchesPriceNow && hasRegistrations, () => void doSave());
  }

  function focusFirstInvalid() {
    const liveEntries = registry.forTab(tab);
    for (const entry of liveEntries) {
      if (entry.saver.validate() > 0) {
        entry.saver.focusFirstInvalid();
        return;
      }
    }
  }

  if (entries.length === 0) return null;

  return (
    <div className="setup-save-bar">
      {confirming && <PriceChangeWarning onConfirm={confirm} onCancel={cancel} />}
      {invalidCount > 0 && (
        <button type="button" className="save-bar-error" onClick={focusFirstInvalid}>
          {t("validation.fieldsNeedAttention", { count: invalidCount })}
        </button>
      )}
      {report && report.failures.length > 0 && (
        <div className="rail-hint">
          <p>
            {t("setup.saveBar.partial", {
              written: report.written,
              total: report.total,
              pending: report.failures.length,
            })}
          </p>
          <ul className="detail-list">
            {report.failures.map((failure, index) => (
              <li key={index}>
                {failure.change}: {failure.error}
              </li>
            ))}
          </ul>
        </div>
      )}
      <button
        type="button"
        className="btn-primary"
        disabled={busy || pendingCount === 0}
        onClick={attemptSave}
      >
        {pendingCount === 0
          ? t("setup.saveBar.nothingToSave")
          : t("setup.saveBar.save", { count: pendingCount })}
      </button>
    </div>
  );
}
