import { type ReactNode, useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError, api, type ExportBandTab, type Queue, type SheetRow } from "../api";
import { tabCount, tabId, tabLabel } from "../export/tabs";
import { useTabBand } from "../useTabBand";
import QueueRoster from "./QueueRoster";
import SeatingCard from "./SeatingCard";

/** The Queue phase: a band of rosters, one per individual discipline, with the
 *  two arrows that change who holds a seat and the settle action in the rail
 *  (spec seating-queue, Queue view for the organizer).
 *
 *  The rows are each discipline's export table and the summary is `/queue`:
 *  deadline, settlement, and every discipline's free places (design
 *  queue-rosters D1). After an action all three are read again, and the
 *  console is told, since a promotion or a return moves money its other
 *  readers show (D6). */
export default function QueuePhase({
  slug,
  timezone,
  revision,
  onChanged,
  renderRail,
}: {
  slug: string;
  timezone: string | null;
  /** Bumped by the console whenever the tournament changed elsewhere. */
  revision: number;
  onChanged: () => void;
  renderRail: (panel: ReactNode) => ReactNode;
}) {
  const { t, i18n } = useTranslation();
  const [tabs, setTabs] = useState<ExportBandTab[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [rows, setRows] = useState<SheetRow[]>([]);
  const [summary, setSummary] = useState<Queue | null>(null);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const [settled, setSettled] = useState<number | null>(null);

  const disciplines = tabs.filter((tab) => tab.kind === "discipline");
  const tab = disciplines.find((candidate) => tabId(candidate) === selected) ?? disciplines[0];
  const band = useTabBand(tab ? tabId(tab) : "");
  const places = summary?.disciplines.find((discipline) => discipline.slug === tab?.key) ?? null;

  const loadBand = useCallback(() => {
    void api.exportTabs(slug).then(setTabs);
    void api.queue(slug).then(setSummary);
  }, [slug]);

  useEffect(loadBand, [loadBand, revision]);

  const tabKey = tab?.key;
  const loadRows = useCallback(() => {
    if (tabKey === undefined) return;
    void api.exportTable(slug, "discipline", tabKey).then((table) => setRows(table.rows));
  }, [slug, tabKey]);

  useEffect(loadRows, [loadRows, revision]);

  /** A refusal is stated in words naming why. The arrows are offered only
   *  where the server would act, so one arriving here is a race — another
   *  organizer acting first — and the code it carries is translated rather
   *  than shown (design queue-rosters D2). */
  function refusal(err: unknown, action: string): string {
    const code = err instanceof ApiError && typeof err.detail === "string" ? err.detail : null;
    const key = code === null ? null : `queue.refused.${code}`;
    return key !== null && i18n.exists(key)
      ? t(key)
      : t("queue.refused.fallback", { action: t(action) });
  }

  async function act(action: string, run: () => Promise<unknown>) {
    setFailure(null);
    setBusy(true);
    try {
      await run();
    } catch (err) {
      setFailure(refusal(err, action));
    } finally {
      setBusy(false);
      loadBand();
      loadRows();
      onChanged();
    }
  }

  const promote = (registrationId: number) => {
    if (tab === undefined) return;
    void act("queue.promote", () => api.admitSubstitute(slug, registrationId, tab.key));
  };
  const giveBack = (registrationId: number) => {
    if (tab === undefined) return;
    void act("queue.returnToQueue", () => api.returnToQueue(slug, registrationId, tab.key));
  };
  const settle = () =>
    void act("queue.settle", async () => {
      const result = await api.settleSeating(slug);
      setSettled(result.demoted);
    });

  return (
    <>
      <main className="sheet-area">
        <div className="sheet-header export-header">
          <h1>{t("queue.title")}</h1>
          <nav className="stage-control stage-control-band" ref={band}>
            {disciplines.map((candidate) => (
              <button
                key={tabId(candidate)}
                type="button"
                className={candidate === tab ? "active" : ""}
                aria-pressed={candidate === tab}
                onClick={() => {
                  setSelected(tabId(candidate));
                  setFailure(null);
                }}
              >
                {tabLabel(t, candidate)}
                {tabCount(candidate) !== null && (
                  <span className="tab-count">{tabCount(candidate)}</span>
                )}
              </button>
            ))}
          </nav>
        </div>
        {failure !== null && <p className="field-error">{failure}</p>}
        {tabs.length > 0 && tab === undefined ? (
          <p className="sheet-empty">{t("queue.noDisciplines")}</p>
        ) : tab !== undefined ? (
          <QueueRoster
            rows={rows}
            slug={tab.key}
            capacity={tab.capacity}
            freeBySlug={Object.fromEntries(
              (summary?.disciplines ?? []).map((discipline) => [discipline.slug, discipline.free]),
            )}
            timezone={timezone}
            busy={busy}
            onPromote={promote}
            onReturn={giveBack}
          />
        ) : null}
      </main>

      {renderRail(
        summary !== null && (
          <SeatingCard
            summary={summary}
            discipline={places}
            timezone={timezone}
            busy={busy}
            outcome={settled}
            onSettle={settle}
          />
        ),
      )}
    </>
  );
}
