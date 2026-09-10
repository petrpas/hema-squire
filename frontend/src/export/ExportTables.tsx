import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { api, type ExportTab, type NetChange, type SheetRow } from "../api";
import { useTabBand } from "../useTabBand";
import { FENCERS_COLUMNS, ITEM_COLUMNS, ROSTER_COLUMNS, toTsv } from "./columns";
import FencersTable from "./FencersTable";
import ItemsTable from "./ItemsTable";
import { activeOnly, rosterOrder } from "./ordering";
import RosterTable from "./RosterTable";

const tabId = (tab: ExportTab) => `${tab.kind}:${tab.key}`;

/** Whether the English tick is offered. Not to an organizer already working in
 *  English, where it would be a tick that changes nothing. */
export function offersEnglishTick(language: string): boolean {
  return !language.startsWith("en");
}

/** The Export phase: a band of tables derived from the tournament, in place of
 *  the single fencer table.
 *
 *  Each tab holds its own all/active-only state, because the tabs answer
 *  different questions — who is coming, who is seeded where, who ordered a
 *  T-shirt — and carrying a filter across would answer one of them with
 *  another's setting.
 */
export default function ExportTables({
  slug,
  edits,
  english,
  onEnglishChange,
  onChanged,
  revision,
}: {
  slug: string;
  /** The phase's manual edits, read to mark a corrected rating as one. */
  edits: NetChange[];
  english: boolean;
  onEnglishChange: (english: boolean) => void;
  onChanged: () => void;
  /** Bumped by the console whenever the tournament's rows changed, so the open
   *  table is re-read rather than left stating what it stated before. */
  revision: number;
}) {
  const { t, i18n } = useTranslation();
  const [tabs, setTabs] = useState<ExportTab[]>([]);
  const [selected, setSelected] = useState<string>("fencers:");
  const [rows, setRows] = useState<SheetRow[]>([]);
  const [actives, setActives] = useState<Record<string, boolean>>({});
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const tab = tabs.find((candidate) => tabId(candidate) === selected) ?? null;
  const active = actives[selected] ?? false;
  const band = useTabBand(selected);

  useEffect(() => {
    void api.exportTabs(slug).then(setTabs);
  }, [slug]);

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
        ? rosterOrder(listed, tab.key, tab.capacity, tab.line ?? "capacity", active).rows
        : listed;
    void navigator.clipboard.writeText(toTsv(columns, ordered, header));
    setMessage(t("export.copied", { count: ordered.length }));
  }

  const rated = (row: SheetRow) =>
    tab !== null &&
    edits.some((edit) => edit.target === row.id && edit.field === `rating:${tab.key}`);

  return (
    <main className="sheet-area">
      <div className="sheet-header">
        <h1>{t("export.tablesTitle")}</h1>
      </div>

      <nav className="stage-control stage-control-band" ref={band}>
        {tabs.map((candidate) => (
          <button
            key={tabId(candidate)}
            type="button"
            className={tabId(candidate) === selected ? "active" : ""}
            aria-pressed={tabId(candidate) === selected}
            onClick={() => setSelected(tabId(candidate))}
          >
            {candidate.kind === "fencers"
              ? t("export.tab.fencers")
              : candidate.kind === "category"
                ? t(`export.category.${candidate.key}`)
                : candidate.label}
          </button>
        ))}
      </nav>

      <div className="export-controls">
        <label>
          <input
            type="checkbox"
            checked={active}
            onChange={(event) =>
              setActives({ ...actives, [selected]: event.currentTarget.checked })
            }
          />
          <span>{t("export.activeOnly")}</span>
        </label>
        <button type="button" className="secondary" onClick={copy}>
          {t("export.copy")}
        </button>
        {offersEnglishTick(i18n.language) && (
          <label>
            <input
              type="checkbox"
              checked={english}
              onChange={(event) => onEnglishChange(event.currentTarget.checked)}
            />
            <span>{t("export.english")}</span>
          </label>
        )}
        {tab?.kind === "discipline" && (
          <button
            type="button"
            className="secondary"
            disabled={busy}
            onClick={() => void refreshRatings()}
            title={t("export.refreshesTournament")}
          >
            {busy ? t("common.loading") : t("export.fetchRatings")}
          </button>
        )}
      </div>
      {tab?.kind === "discipline" && <p className="rail-hint">{t("export.refreshesTournament")}</p>}
      {message && <p className="rail-hint">{message}</p>}

      {tab === null ? null : tab.kind === "fencers" ? (
        <FencersTable rows={listed} />
      ) : tab.kind === "discipline" ? (
        <RosterTable
          rows={listed}
          slug={tab.key}
          capacity={tab.capacity}
          lineKind={tab.line ?? "capacity"}
          seeded={active}
          edited={rated}
          onRate={(row, raw) => void rate(row, raw)}
        />
      ) : (
        <ItemsTable rows={listed} category={tab.key} />
      )}
    </main>
  );
}
