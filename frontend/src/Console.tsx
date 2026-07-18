import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import ParamPanel from "./ParamPanel";
import {
  type Sheet,
  type SheetRow,
  type Tournament,
  type TournamentDetail,
  api,
  setToken,
} from "./api";

const STAGES = ["pre", "in", "post"] as const;
const PHASES = ["load", "parsing", "matching", "dedup", "payments", "export"] as const;
export type Phase = (typeof PHASES)[number];

// A phase tab is a view of the whole fencer list plus that operation's
// parameters (design Decision 1). Shared base columns, phase-owned columns.
const BASE_COLUMNS = ["name", "nationality", "club"];

const PHASE_COLUMNS: Record<Phase, string[]> = {
  load: ["disciplines", "weapon_rentals", "afterparty", "registered_at"],
  parsing: ["disciplines", "notes"],
  matching: ["hr_id", "match"],
  dedup: ["hr_id", "state"],
  payments: ["vs", "total_amount", "expires_at", "paid_at", "state"],
  export: ["hr_id", "disciplines", "state"],
};

function StateBadge({ state }: { state: string }) {
  const symbol = state === "paid" ? "✓" : state === "reserved" ? "?" : "✗";
  return <span className={`badge badge-${state}`}>{symbol}</span>;
}

function Cell({ row, column }: { row: SheetRow; column: string }) {
  switch (column) {
    case "state":
      return <StateBadge state={row.state} />;
    case "match":
      return row.hr_id !== null ? (
        <span className="badge badge-paid">✓</span>
      ) : (
        <span className="badge badge-expired">✗</span>
      );
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
      return <>{new Date(row.registered_at).toLocaleDateString("cs")}</>;
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
  onBack,
  onLogout,
}: {
  tournament: Tournament;
  onBack: () => void;
  onLogout: () => void;
}) {
  const { t } = useTranslation();
  const [phase, setPhase] = useState<Phase>("load");
  const [sheet, setSheet] = useState<Sheet | null>(null);
  const [detail, setDetail] = useState<TournamentDetail | null>(null);
  const [error, setError] = useState(false);

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

  const rows = sheet?.rows ?? [];
  const paidCount = rows.filter((row) => row.paid).length;
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
        <main className="sheet-area">
          <div className="sheet-header">
            <div>
              <h1>{t("console.title")}</h1>
              <p className="sheet-stats">
                {t("console.stats", {
                  rows: rows.length,
                  paid: paidCount,
                  reserved: rows.length - paidCount,
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
            ) : rows.length === 0 ? (
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
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row, index) => (
                    <tr key={row.id}>
                      <td className="col-index">{index + 1}</td>
                      {columns.map((column) => (
                        <td
                          key={column}
                          className={PHASE_COLUMNS[phase].includes(column) ? "col-phase" : ""}
                        >
                          <Cell row={row} column={column} />
                        </td>
                      ))}
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
                    <div>
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
                  </li>
                ))}
              </ul>
            )}
          </section>
        </aside>
      </div>
    </div>
  );
}
