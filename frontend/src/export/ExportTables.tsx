import { type ReactNode, useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { api, type ExportBandTab, type NetChange, type SheetRow } from "../api";
import ExportPanel from "../ExportPanel";
import { useTabBand } from "../useTabBand";
import { FENCERS_COLUMNS, ITEM_COLUMNS, ROSTER_COLUMNS, toTsv } from "./columns";
import FencersTable from "./FencersTable";
import ItemsTable from "./ItemsTable";
import { activeOnly, rosterOrder } from "./ordering";
import RosterTable from "./RosterTable";
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
  const [active, setActive] = useState(false);
  const [seeded, setSeeded] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const tab = tabs.find((candidate) => tabId(candidate) === selected) ?? null;
  const band = useTabBand(selected);

  // the selection is held by id, so a re-read keeps the open tab open
  const loadTabs = useCallback(() => {
    void api.exportTabs(slug).then(setTabs);
  }, [slug]);

  useEffect(loadTabs, [loadTabs, revision]);

  const reload = useCallback(() => {
    if (tab === null) return;
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
    setMessage(null);
    try {
      const outcome = await api.ratingsSnapshot(slug);
      setMessage(t("export.ratingsDone", { ratings: outcome.ratings, fencers: outcome.fencers }));
      reload();
      onChanged();
    } catch {
      setMessage(t("export.ratingsFailed"));
    } finally {
      setBusy(false);
    }
  }

  function copy() {
    if (tab === null) return;
    const header = (id: string) =>
      english ? i18n.getFixedT("en")(`export.column.${id}`) : t(`export.column.${id}`);
    const locale = english ? i18n.getFixedT("en") : t;
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
                onClick={() => setSelected(tabId(candidate))}
              >
                {tabLabel(t, candidate)}
                <span className="tab-count">{tabCount(candidate)}</span>
              </button>
            ))}
          </nav>
        </div>

        {tab === null ? null : tab.kind === "fencers" ? (
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
          {tab !== null && (
            <TableOperations
              title={tabLabel(t, tab)}
              active={active}
              onActiveChange={setActive}
              seeded={
                tab.kind === "discipline" ? { checked: seeded, onChange: setSeeded } : undefined
              }
              onCopy={copy}
              onRefreshRatings={tab.kind === "discipline" ? () => void refreshRatings() : undefined}
              refreshing={busy}
              message={message}
            />
          )}
          <ExportPanel slug={slug} english={english} onEnglishChange={onEnglishChange} />
        </>,
      )}
    </>
  );
}
