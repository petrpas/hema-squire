import { type ReactNode, useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import {
  api,
  type ExportBandTab,
  type ExportRevenue,
  type ExportSummaryLine,
  type NetChange,
  type RosterFormat,
  type SheetRow,
} from "../api";
import ExportPanel, { offersEnglishTick } from "../ExportPanel";
import { useTabBand } from "../useTabBand";
import { FENCERS_COLUMNS, ITEM_COLUMNS, ROSTER_COLUMNS, toTsv } from "./columns";
import FencersTable from "./FencersTable";
import ItemsTable from "./ItemsTable";
import { activeOnly, rosterOrder } from "./ordering";
import RevenueTable from "./RevenueTable";
import RosterTable from "./RosterTable";
import { revenueLineCount, revenueTsv } from "./revenue";
import { rosterPrint, saveBlob } from "./roster";
import SummaryTable from "./SummaryTable";
import { summaryTsv } from "./summary";
import TableOperations from "./TableOperations";
import { tabCount, tabId, tabLabel } from "./tabs";

/** The Export phase: a band of tables derived from the tournament, in place of
 *  the single fencer table.
 *
 *  The active-only switch and the seeding order hold across tabs: an organizer
 *  who has narrowed to the paid is still reading the paid on the next tab, and
 *  one reading disciplines in seeding order reads the next discipline so too
 *  (owner decision, change export-layouts).
 *
 *  Above the table stands only the band. What acts on the open tab is the
 *  phase's operations and goes into the rail, which the console hands in so
 *  that the tab state stays here, beside the table it drives.
 */
export default function ExportTables({
  slug,
  edits,
  english,
  onEnglishChange,
  onChanged,
  revision,
  renderRail,
}: {
  slug: string;
  /** The phase's manual edits, read to mark a corrected rating as one. */
  edits: NetChange[];
  english: boolean;
  onEnglishChange: (english: boolean) => void;
  onChanged: () => void;
  /** Bumped by the console whenever the tournament's rows changed, so the open
   *  table and the band's counts are re-read rather than left stating what
   *  they stated before. */
  revision: number;
  /** The console's rail, with this phase's cards in its panel slot. */
  renderRail: (panel: ReactNode) => ReactNode;
}) {
  const { t, i18n } = useTranslation();
  const [tabs, setTabs] = useState<ExportBandTab[]>([]);
  const [selected, setSelected] = useState<string>("fencers:");
  const [rows, setRows] = useState<SheetRow[]>([]);
  const [summary, setSummary] = useState<ExportSummaryLine[]>([]);
  const [revenue, setRevenue] = useState<ExportRevenue | null>(null);
  // the Include finances tick: held here rather than with the English tick in
  // the console, so that leaving Export and coming back finds it off — money
  // reaches the shared workbook only by a decision made for that export
  const [finances, setFinances] = useState(false);
  const [active, setActive] = useState(false);
  const [seeded, setSeeded] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [ratingsMessage, setRatingsMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  // the format being typeset, so its button waits without a spinner
  const [printing, setPrinting] = useState<RosterFormat | null>(null);

  const tab = tabs.find((candidate) => tabId(candidate) === selected) ?? null;
  const band = useTabBand(selected);

  // the selection is held by id, so a re-read keeps the open tab open
  const loadTabs = useCallback(() => {
    void api.exportTabs(slug).then(setTabs);
  }, [slug]);

  useEffect(loadTabs, [loadTabs, revision]);

  const reload = useCallback(() => {
    if (tab === null) return;
    // the summary is not a fencer table: its lines are read on their own
    if (tab.kind === "summary") {
      void api.exportSummary(slug).then((read) => setSummary(read.lines));
      return;
    }
    if (tab.kind === "revenue") {
      void api.exportRevenue(slug).then(setRevenue);
      return;
    }
    void api.exportTable(slug, tab.kind, tab.key).then((table) => setRows(table.rows));
  }, [slug, tab]);

  useEffect(reload, [reload, revision]);

  const listed = activeOnly(rows, active);

  async function rate(row: SheetRow, raw: string) {
    const typed = raw.trim();
    if (tab === null) return;
    await api.createRule(slug, {
      phase: "export",
      kind: "rating_override",
      target: row.id,
      payload: {
        discipline: tab.key,
        rating: typed === "" ? null : Number(typed.replace(",", ".")),
      },
    });
    reload();
    onChanged();
  }

  async function refreshRatings() {
    setBusy(true);
    setRatingsMessage(null);
    try {
      const outcome = await api.ratingsSnapshot(slug);
      setRatingsMessage(
        t("export.ratingsDone", { ratings: outcome.ratings, fencers: outcome.fencers }),
      );
      reload();
      onChanged();
    } catch {
      setRatingsMessage(t("export.ratingsFailed"));
    } finally {
      setBusy(false);
    }
  }

  function copy() {
    if (tab === null) return;
    const header = (id: string) =>
      english ? i18n.getFixedT("en")(`export.column.${id}`) : t(`export.column.${id}`);
    const locale = english ? i18n.getFixedT("en") : t;
    if (tab.kind === "summary") {
      void navigator.clipboard.writeText(summaryTsv(locale, summary));
      setMessage(t("export.copied", { count: summary.length }));
      return;
    }
    if (tab.kind === "revenue") {
      if (revenue === null) return;
      void navigator.clipboard.writeText(revenueTsv(locale, revenue));
      setMessage(t("export.copied", { count: revenueLineCount(revenue) }));
      return;
    }
    const columns =
      tab.kind === "fencers"
        ? FENCERS_COLUMNS(locale)
        : tab.kind === "discipline"
          ? ROSTER_COLUMNS(locale, tab.key)
          : ITEM_COLUMNS(locale, tab.key);
    // the copy follows the order on screen, and the line is not part of it
    const ordered =
      tab.kind === "discipline"
        ? rosterOrder(listed, tab.key, tab.capacity, tab.line ?? "capacity", seeded).rows
        : listed;
    void navigator.clipboard.writeText(toTsv(columns, ordered, header));
    setMessage(t("export.copied", { count: ordered.length }));
  }

  async function print(format: RosterFormat) {
    if (tab === null || tab.kind !== "discipline") return;
    const locale = english ? i18n.getFixedT("en") : t;
    setPrinting(format);
    setMessage(null);
    try {
      const blob = await api.exportRoster(
        slug,
        format,
        rosterPrint(locale, listed, tab, seeded, english),
      );
      saveBlob(blob, `${slug}-${tab.key}.${format}`);
    } catch {
      setMessage(t("export.printFailed"));
    } finally {
      setPrinting(null);
    }
  }

  const rated = (row: SheetRow) =>
    tab !== null &&
    edits.some((edit) => edit.target === row.id && edit.field === `rating:${tab.key}`);

  return (
    <>
      <main className="sheet-area">
        {/* the band stands on the title's line: it is what the title names */}
        <div className="sheet-header export-header">
          <h1>{t("export.tablesTitle")}</h1>
          <nav className="stage-control stage-control-band" ref={band}>
            {tabs.map((candidate) => (
              <button
                key={tabId(candidate)}
                type="button"
                className={tabId(candidate) === selected ? "active" : ""}
                aria-pressed={tabId(candidate) === selected}
                onClick={() => {
                  setSelected(tabId(candidate));
                  // a copy's confirmation speaks of the tab it was made on
                  setMessage(null);
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

        {tab === null ? null : tab.kind === "summary" ? (
          <SummaryTable lines={summary} />
        ) : tab.kind === "revenue" ? (
          <RevenueTable revenue={revenue} />
        ) : tab.kind === "fencers" ? (
          <FencersTable rows={listed} />
        ) : tab.kind === "discipline" ? (
          <RosterTable
            rows={listed}
            slug={tab.key}
            capacity={tab.capacity}
            lineKind={tab.line ?? "capacity"}
            seeded={seeded}
            edited={rated}
            onRate={(row, raw) => void rate(row, raw)}
          />
        ) : (
          <ItemsTable rows={listed} category={tab.key} />
        )}
      </main>

      {renderRail(
        <>
          {/* above both cards: it governs what leaves through the tab's copy
              and printouts and through the whole export alike */}
          {offersEnglishTick(i18n.language) && (
            <label className="rail-check export-english">
              <input
                type="checkbox"
                checked={english}
                onChange={(event) => onEnglishChange(event.currentTarget.checked)}
              />
              <span>{t("export.english")}</span>
            </label>
          )}
          {tab !== null && (
            <TableOperations
              title={tabLabel(t, tab)}
              // the summary and the revenue state paid and unpaid side by side:
              // narrowing them would empty one of their columns, so they offer
              // no switch
              active={
                tab.kind === "summary" || tab.kind === "revenue"
                  ? undefined
                  : { checked: active, onChange: setActive }
              }
              seeded={
                tab.kind === "discipline" ? { checked: seeded, onChange: setSeeded } : undefined
              }
              onCopy={copy}
              print={
                tab.kind === "discipline"
                  ? { onPrint: (format) => void print(format), printing }
                  : undefined
              }
              onRefreshRatings={tab.kind === "discipline" ? () => void refreshRatings() : undefined}
              refreshing={busy}
              ratingsMessage={ratingsMessage}
              message={message}
            />
          )}
          <ExportPanel
            slug={slug}
            english={english}
            finances={finances}
            onFinancesChange={setFinances}
          />
        </>,
      )}
    </>
  );
}
