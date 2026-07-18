import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { type Sheet, type Tournament, api, setToken } from "./api";

const STAGES = ["pre", "in", "post"] as const;
const PHASES = ["load", "parsing", "matching", "dedup", "payments", "export"] as const;
export type Phase = (typeof PHASES)[number];

const BASE_COLUMNS = ["name", "nationality", "club", "hr_id", "disciplines", "vs", "state"];

function StateBadge({ state }: { state: string }) {
  const symbol = state === "paid" ? "✓" : state === "reserved" ? "?" : "✗";
  return <span className={`badge badge-${state}`}>{symbol}</span>;
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
  const [error, setError] = useState(false);

  const refresh = useCallback(() => {
    api.sheet(tournament.slug).then(
      (data) => {
        setSheet(data);
        setError(false);
      },
      () => setError(true),
    );
  }, [tournament.slug]);

  useEffect(refresh, [refresh]);

  const rows = sheet?.rows ?? [];
  const paidCount = rows.filter((row) => row.paid).length;

  return (
    <div className="app">
      <header className="topbar">
        <button className="logo-button" onClick={onBack} title={t("picker.title")}>
          <span className="logo">{t("app.title")}</span>
        </button>
        <nav className="stage-control">
          {STAGES.map((stage) => (
            <button key={stage} className={stage === "pre" ? "active" : ""} disabled={stage !== "pre"}>
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
        <button className="link-button" onClick={() => { setToken(null); onLogout(); }}>
          {t("common.logout")}
        </button>
      </header>

      <nav className="stepper">
        {PHASES.map((p, index) => (
          <div key={p} className="step-slot">
            {index > 0 && <div className="step-connector" />}
            <button
              className={`step ${p === phase ? "active" : ""}`}
              onClick={() => setPhase(p)}
            >
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
                    {BASE_COLUMNS.map((column) => (
                      <th key={column}>{t(`column.${column}`)}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row, index) => (
                    <tr key={row.id}>
                      <td className="col-index">{index + 1}</td>
                      <td>{row.name}</td>
                      <td>{row.nationality ?? "—"}</td>
                      <td>{row.club ?? "—"}</td>
                      <td>{row.hr_id ?? "—"}</td>
                      <td>{row.disciplines.join(", ")}</td>
                      <td>{row.vs}</td>
                      <td className="col-state">
                        <StateBadge state={row.state} />
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

          <section className="rail-card">
            <h2>{t("rail.generalRules")}</h2>
            <p className="rail-hint">{t("rail.rulesHint")}</p>
          </section>

          <section className="rail-card dashed">
            <h2>{t("rail.columnsForStep")}</h2>
            <div className="chips">
              {BASE_COLUMNS.map((column) => (
                <span key={column} className="chip">
                  {t(`column.${column}`)}
                </span>
              ))}
            </div>
          </section>

          <section className="rail-card plain">
            <h2>
              {t("rail.manualEdits")}{" "}
              <span className="rail-count">({sheet?.edits.length ?? 0})</span>
            </h2>
            {(sheet?.edits ?? []).length === 0 ? (
              <p className="rail-hint">{t("rail.noEdits")}</p>
            ) : (
              <ul className="edits-list">
                {sheet!.edits.map((edit, index) => (
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
