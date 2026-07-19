import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import DedupPanel from "./DedupPanel";
import EditableCell from "./EditableCell";
import ExportPanel from "./ExportPanel";
import ImportPanel from "./ImportPanel";
import MatchDialog from "./MatchDialog";
import MatchPanel from "./MatchPanel";
import ParamPanel from "./ParamPanel";
import SetupPanel from "./SetupPanel";
import {
  type Sheet,
  type SheetRow,
  type Tournament,
  type TournamentDetail,
  api,
  setToken,
} from "./api";

const STAGES = ["pre", "in", "post"] as const;
// Setup is step 0, ahead of the fencer-list phases (spec: etl-console).
const PHASES = ["setup", "load", "parsing", "matching", "dedup", "payments", "export"] as const;
export type Phase = (typeof PHASES)[number];

// A phase tab is a view of the whole fencer list plus that operation's
// parameters (design Decision 1). Shared base columns, phase-owned columns.
// Setup replaces the fencer table entirely, so it owns no columns.
const BASE_COLUMNS = ["name", "nationality", "club"];

const PHASE_COLUMNS: Record<Phase, string[]> = {
  setup: [],
  load: ["disciplines", "weapon_rentals", "afterparty", "registered_at"],
  parsing: ["disciplines", "notes", "problems"],
  matching: ["hr_id", "match"],
  dedup: ["hr_id", "state"],
  payments: ["vs", "total_amount", "expires_at", "paid_at", "state"],
  export: ["hr_id", "disciplines", "state"],
};

// Manual edits on these columns become field_edit rules.
const EDITABLE_COLUMNS = new Set(["name", "nationality", "club", "notes", "hr_id"]);

function StateBadge({ state }: { state: string }) {
  const symbol =
    state === "paid" ? "✓" : state === "reserved" ? "?" : state === "imported" ? "•" : "✗";
  return <span className={`badge badge-${state}`}>{symbol}</span>;
}

function CellDisplay({ row, column }: { row: SheetRow; column: string }) {
  switch (column) {
    case "state":
      return <StateBadge state={row.state} />;
    case "disciplines":
      return (
        <>
          {row.disciplines.join(", ")}
          {row.substitute_for.length > 0 && (
            <span className="muted"> (+{row.substitute_for.join(", ")})</span>
          )}
        </>
      );
    case "weapon_rentals":
      return <>{row.weapon_rentals.length > 0 ? row.weapon_rentals.join(", ") : "—"}</>;
    case "afterparty":
      return <>{row.afterparty ? "✓" : "—"}</>;
    case "registered_at":
      return (
        <>{row.registered_at ? new Date(row.registered_at).toLocaleDateString("cs") : "—"}</>
      );
    case "expires_at":
    case "paid_at": {
      const value = row[column];
      return <>{value ? new Date(value as string).toLocaleDateString("cs") : "—"}</>;
    }
    default: {
      const value = row[column];
      return <>{value === null || value === undefined || value === "" ? "—" : String(value)}</>;
    }
  }
}

export default function Console({
  tournament,
  initialPhase,
  onBack,
  onLogout,
}: {
  tournament: Tournament;
  initialPhase?: Phase;
  onBack: () => void;
  onLogout: () => void;
}) {
  const { t } = useTranslation();
  const [phase, setPhase] = useState<Phase>(initialPhase ?? "load");
  const [sheet, setSheet] = useState<Sheet | null>(null);
  const [detail, setDetail] = useState<TournamentDetail | null>(null);
  const [error, setError] = useState(false);
  const [matchRow, setMatchRow] = useState<SheetRow | null>(null);

  const refresh = useCallback(() => {
    api.sheet(tournament.slug).then(
      (data) => {
        setSheet(data);
        setError(false);
      },
      () => setError(true),
    );
    api.tournament(tournament.slug).then(setDetail, () => {});
  }, [tournament.slug]);

  useEffect(refresh, [refresh]);

  async function addRule(kind: string, target: string, payload: Record<string, unknown>) {
    await api.createRule(tournament.slug, { phase, kind, target, payload });
    refresh();
  }

  function saveEdit(row: SheetRow, field: string, raw: string) {
    const value =
      field === "hr_id" ? (raw === "" ? null : Number(raw)) : raw === "" ? null : raw;
    void addRule("field_edit", row.id, { field, value });
  }

  async function removeRule(ruleId: number) {
    await api.deleteRule(tournament.slug, ruleId);
    refresh();
  }

  function resolveMatch(row: SheetRow, hrId: number | null) {
    setMatchRow(null);
    void addRule("match_resolution", row.id, { field: "hr_id", value: hrId });
  }

  const rows = sheet?.rows ?? [];
  const visibleRows = rows;
  const activeRows = rows.filter((row) => !row._deleted);
  const paidCount = activeRows.filter((row) => row.paid).length;
  const columns = [...BASE_COLUMNS, ...PHASE_COLUMNS[phase]];
  const phaseEdits = (sheet?.edits ?? []).filter((edit) => edit.phase === phase);

  return (
    <div className="app">
      <header className="topbar">
        <button className="logo-button" onClick={onBack} title={t("picker.title")}>
          <span className="logo">{t("app.title")}</span>
        </button>
        <nav className="stage-control">
          {STAGES.map((stage) => (
            <button
              key={stage}
              className={stage === "pre" ? "active" : ""}
              disabled={stage !== "pre"}
            >
              {t(`stage.${stage}`)}
            </button>
          ))}
        </nav>
        <div className="tournament-info">
          <div className="tournament-name">{tournament.display_name}</div>
          <div className="tournament-date">
            {new Date(tournament.date).toLocaleDateString("cs")}
          </div>
        </div>
        <button
          className="link-button"
          onClick={() => {
            setToken(null);
            onLogout();
          }}
        >
          {t("common.logout")}
        </button>
      </header>

      <nav className="stepper">
        {PHASES.map((p, index) => (
          <div key={p} className="step-slot">
            {index > 0 && <div className="step-connector" />}
            <button className={`step ${p === phase ? "active" : ""}`} onClick={() => setPhase(p)}>
              <span className="step-number">{index + 1}</span>
              <span className="step-label">{t(`phase.${p}`)}</span>
            </button>
          </div>
        ))}
      </nav>

      <div className="workspace">
        {phase === "setup" ? (
          <SetupPanel
            detail={detail}
            slug={tournament.slug}
            onSaved={refresh}
            hasRegistrations={activeRows.length > 0}
            onDeleted={onBack}
          />
        ) : (
          <>
        <main className="sheet-area">
          <div className="sheet-header">
            <div>
              <h1>{t("console.title")}</h1>
              <p className="sheet-stats">
                {t("console.stats", {
                  rows: activeRows.length,
                  paid: paidCount,
                  reserved: activeRows.length - paidCount,
                })}
              </p>
            </div>
            <button className="secondary" onClick={refresh}>
              ↻ {t("console.refresh")}
            </button>
          </div>

          <div className="sheet-scroll">
            {error ? (
              <p className="sheet-empty">{t("console.error")}</p>
            ) : visibleRows.length === 0 ? (
              <p className="sheet-empty">{t("sheet.empty")}</p>
            ) : (
              <table className="sheet-table">
                <thead>
                  <tr>
                    <th className="col-index">#</th>
                    {columns.map((column) => (
                      <th
                        key={column}
                        className={PHASE_COLUMNS[phase].includes(column) ? "col-phase" : ""}
                      >
                        {t(`column.${column}`)}
                      </th>
                    ))}
                    <th className="col-actions" />
                  </tr>
                </thead>
                <tbody>
                  {visibleRows.map((row, index) => (
                    <tr key={row.id} className={row._deleted ? "row-deleted" : ""}>
                      <td className="col-index">{index + 1}</td>
                      {columns.map((column) => {
                        const phaseOwned = PHASE_COLUMNS[phase].includes(column);
                        const editable = EDITABLE_COLUMNS.has(column) && !row._deleted;
                        const isMatch = column === "match";
                        return (
                          <td
                            key={column}
                            className={`${phaseOwned ? "col-phase" : ""} ${
                              isMatch ? "col-state" : ""
                            }`}
                          >
                            {isMatch ? (
                              <button
                                className="badge-button"
                                title={t("match.title")}
                                onClick={() => setMatchRow(row)}
                                disabled={row._deleted === true}
                              >
                                {row.match_verdict === "confirmed" ? (
                                  <span className="badge badge-paid">✓</span>
                                ) : row.match_verdict === "none_found" ? (
                                  <span className="badge badge-expired">✗</span>
                                ) : row.match_verdict === "proposed" ? (
                                  <span className="badge badge-reserved">?</span>
                                ) : (
                                  <span className="badge badge-imported">?</span>
                                )}
                              </button>
                            ) : editable ? (
                              <EditableCell
                                display={<CellDisplay row={row} column={column} />}
                                value={row[column]}
                                onSave={(raw) => saveEdit(row, column, raw)}
                              />
                            ) : (
                              <CellDisplay row={row} column={column} />
                            )}
                          </td>
                        );
                      })}
                      <td className="col-actions">
                        {row._deleted ? (
                          <button
                            className="row-action"
                            title={t("actions.restore")}
                            onClick={() => void addRule("row_restore", row.id, {})}
                          >
                            ↺
                          </button>
                        ) : (
                          <button
                            className="row-action"
                            title={t("actions.delete")}
                            onClick={() => void addRule("row_delete", row.id, {})}
                          >
                            ✕
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </main>

        <aside className="rail">
          <div className="rail-title">
            {t("rail.operations")} · {t(`phase.${phase}`)}
          </div>

          <ParamPanel phase={phase} detail={detail} slug={tournament.slug} onSaved={refresh} />

          {phase === "load" && <ImportPanel slug={tournament.slug} onImported={refresh} />}
          {phase === "matching" && <MatchPanel slug={tournament.slug} onChanged={refresh} />}
          {phase === "dedup" && <DedupPanel slug={tournament.slug} onChanged={refresh} />}
          {phase === "export" && <ExportPanel slug={tournament.slug} />}

          <section className="rail-card dashed">
            <h2>{t("rail.columnsForStep")}</h2>
            <div className="chips">
              {PHASE_COLUMNS[phase].map((column) => (
                <span key={column} className="chip">
                  {t(`column.${column}`)}
                </span>
              ))}
            </div>
          </section>

          <section className="rail-card plain">
            <h2>
              {t("rail.manualEdits")}{" "}
              <span className="rail-count">({phaseEdits.length})</span>
            </h2>
            {phaseEdits.length === 0 ? (
              <p className="rail-hint">{t("rail.noEdits")}</p>
            ) : (
              <ul className="edits-list">
                {phaseEdits.map((edit, index) => (
                  <li key={index} className="edit-entry">
                    <span className="edit-icon">~</span>
                    <div className="edit-body">
                      <div>
                        {edit.field}: {String(edit.before ?? "—")} → {String(edit.after)}
                      </div>
                      <div className="edit-meta">
                        {edit.target} · {edit.actor} ·{" "}
                        {new Date(edit.at).toLocaleTimeString("cs", {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </div>
                    </div>
                    <button
                      className="row-action"
                      title={t("actions.removeRule")}
                      onClick={() => void removeRule(edit.rule_id)}
                    >
                      ✕
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </aside>
          </>
        )}
      </div>

      {matchRow && (
        <MatchDialog
          row={matchRow}
          onResolve={(hrId) => resolveMatch(matchRow, hrId)}
          onClose={() => setMatchRow(null)}
        />
      )}
    </div>
  );
}
