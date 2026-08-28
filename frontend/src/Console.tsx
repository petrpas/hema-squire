import { IconArrowBackUp, IconTrash } from "@tabler/icons-react";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import AccountMenu from "./AccountMenu";
import DedupPanel from "./DedupPanel";
import EditableCell from "./EditableCell";
import ExportPanel from "./ExportPanel";
import ImportPanel from "./ImportPanel";
import MatchDialog from "./MatchDialog";
import MatchPanel from "./MatchPanel";
import ManualEditsRail from "./ManualEditsRail";
import PaidStamp from "./PaidStamp";
import TolerancePanel from "./TolerancePanel";
import PaymentsPanel from "./PaymentsPanel";
import QueuePanel from "./QueuePanel";
import { useAuth } from "./RequireAuth";
import * as routes from "./routes";
import SetupPanel from "./SetupPanel";
import TeamsPanel from "./TeamsPanel";
import { registeredMoment } from "./momentText";
import { parseInteger } from "./numeric";
import { checkNumeric, checkString, type FieldError } from "./validation";
import {
  type Account,
  type Sheet,
  type SheetRow,
  type Tournament,
  type TournamentDetail,
  type TournamentMode,
  api,
} from "./api";

const STAGES = ["pre", "in", "post"] as const;
// Setup is step 0, ahead of the fencer-list phases (spec: etl-console).
// Teams is a read-only view of team disciplines (design team-disciplines
// 7.2) and Queue is the seating view (design add-payment-modes), both tacked
// on at the end — neither is part of the ETL sequence.
export const PHASES = [
  "setup",
  "load",
  "parsing",
  "matching",
  "dedup",
  "payments",
  "export",
  "teams",
  "queue",
] as const;
export type Phase = (typeof PHASES)[number];

/** The phase the console opens on when the URL names none, and where a URL
 *  naming a phase the mode does not offer lands. */
export const DEFAULT_PHASE: Phase = "load";

/** Which phases the tournament's mode offers, in the fixed order above — the
 *  mode removes phases, it never reorders them (spec: etl-console). The rest
 *  are always offered, since they are what every tournament is made of. */
export function offeredPhases(mode: TournamentMode): Phase[] {
  return PHASES.filter((phase) => {
    if (phase === "payments") return mode.feature_payments;
    if (phase === "teams") return mode.feature_teams;
    return true;
  });
}

// A phase tab is a view of the whole fencer list plus that operation's
// parameters (design Decision 1). Shared base columns, phase-owned columns.
// Setup, Teams and Queue replace the fencer table entirely, so they own no
// columns.
const BASE_COLUMNS = ["name", "nationality", "club"];

const PHASE_COLUMNS: Record<Phase, string[]> = {
  setup: [],
  load: ["disciplines", "weapon_rentals", "afterparty", "registered_at"],
  parsing: ["disciplines", "notes", "problems"],
  matching: ["hr_id", "match"],
  dedup: ["hr_id", "state"],
  payments: ["vs", "total_amount", "expires_at", "paid_at", "state"],
  export: ["hr_id", "disciplines", "state"],
  teams: [],
  queue: [],
};

// Manual edits on these columns become field_edit rules.
const EDITABLE_COLUMNS = new Set(["name", "nationality", "club", "notes", "hr_id"]);

function StateBadge({ id, state }: { id: string; state: string }) {
  const { t } = useTranslation();
  if (state === "paid") return <PaidStamp id={id} label={t("registration.state.paid")} />;
  return <span className="state-text">{state}</span>;
}

/** `timezone` is the tournament's own zone, the frame every moment in the
 *  table is read in; it is null until the tournament detail has arrived
 *  beside the sheet, and the moment falls back to the reader's zone until it
 *  does (design show-register-times D5). */
export function CellDisplay({
  row,
  column,
  timezone,
}: {
  row: SheetRow;
  column: string;
  timezone: string | null;
}) {
  switch (column) {
    case "state":
      return <StateBadge id={row.id} state={row.state} />;
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
      return <>{registeredMoment(row.registered_at, timezone)}</>;
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
  phase,
}: {
  tournament: Tournament;
  phase: Phase;
}) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { onLogout } = useAuth();
  const [sheet, setSheet] = useState<Sheet | null>(null);
  const [detail, setDetail] = useState<TournamentDetail | null>(null);
  const [error, setError] = useState(false);
  const [matchRow, setMatchRow] = useState<SheetRow | null>(null);
  const [account, setAccount] = useState<Account | null>(null);
  const [setupDirty, setSetupDirty] = useState(false);
  const [pendingPhase, setPendingPhase] = useState<Phase | null>(null);

  useEffect(() => {
    api.account().then(setAccount, () => setAccount(null));
  }, []);

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

  function cellCheck(field: string, raw: string): FieldError | null {
    switch (field) {
      case "hr_id":
        return checkNumeric(field, "RosterMemberIn.hr_id", raw);
      case "name":
        return checkString(field, "RosterMemberIn.name", raw, { required: true });
      case "club":
        return checkString(field, "RosterMemberIn.club", raw);
      case "nationality":
        return checkString(field, "RosterMemberIn.nationality", raw);
      default:
        return null;
    }
  }

  function saveEdit(row: SheetRow, field: string, raw: string) {
    const value =
      field === "hr_id"
        ? raw === ""
          ? null
          : (() => {
              const result = parseInteger(raw);
              return result.ok ? result.value : null;
            })()
        : raw === ""
          ? null
          : raw;
    void addRule("field_edit", row.id, { field, value });
  }

  /** Undoing a log entry removes every rule behind it, so the cell returns to
   *  its source value in one action (spec `edit-rules`, Audit of applied
   *  changes). */
  async function undoEdit(ruleIds: number[]) {
    for (const ruleId of ruleIds) {
      await api.deleteRule(tournament.slug, ruleId);
    }
    refresh();
  }

  function resolveMatch(row: SheetRow, hrId: number | null) {
    setMatchRow(null);
    void addRule("match_resolution", row.id, { field: "hr_id", value: hrId });
  }

  // Leaving Setup dirty is confirmed (spec: setup-navigation); switching
  // between Setup's own tabs never goes through this, since it isn't a phase change.
  function requestPhase(next: Phase) {
    if (phase === "setup" && setupDirty && next !== "setup") {
      setPendingPhase(next);
    } else {
      navigate(routes.consolePath(tournament.slug, next));
    }
  }

  const rows = sheet?.rows ?? [];
  const visibleRows = rows;
  const activeRows = rows.filter((row) => !row._deleted);
  const paidCount = activeRows.filter((row) => row.paid).length;
  // from the refreshed detail where there is one, so applying a mode in Setup
  // adds and removes phases at once rather than on the next load
  const phases = offeredPhases(detail ?? tournament);
  const columns = [...BASE_COLUMNS, ...PHASE_COLUMNS[phase]];
  const phaseEdits = (sheet?.edits ?? []).filter((edit) => edit.phase === phase);

  return (
    <div className="app">
      <header className="topbar">
        <Link className="logo-button" to={routes.picker()} title={t("picker.title")}>
          <span className="logo">{t("app.title")}</span>
        </Link>
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
        <AccountMenu account={account} onLogout={onLogout} />
      </header>

      <nav className="stepper">
        {phases.map((p, index) => (
          <div key={p} className="step-slot">
            {index > 0 && <div className="step-connector" />}
            <button
              className={`step ${p === phase ? "active" : ""}`}
              onClick={() => requestPhase(p)}
            >
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
            onDeleted={() => navigate(routes.picker())}
            onDirtyChange={setSetupDirty}
          />
        ) : phase === "teams" ? (
          <TeamsPanel slug={tournament.slug} />
        ) : phase === "queue" ? (
          <QueuePanel slug={tournament.slug} timezone={detail?.timezone ?? null} />
        ) : (
          <>
        <main className="sheet-area">
          <div className="sheet-header">
            <h1>{t("console.title")}</h1>
            <button className="secondary" onClick={refresh}>
              {t("console.refresh")}
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
                                  <span className="tag tag-seal-green">
                                    {t("match.verdict.confirmed")}
                                  </span>
                                ) : row.match_verdict === "none_found" ? (
                                  <span className="state-text">{t("match.verdict.noneFound")}</span>
                                ) : row.match_verdict === "proposed" ? (
                                  <span className="tag tag-form-yellow">
                                    {t("match.verdict.proposed")}
                                  </span>
                                ) : (
                                  <span className="state-text">{t("match.verdict.unknown")}</span>
                                )}
                              </button>
                            ) : editable ? (
                              <EditableCell
                                display={
                                  <CellDisplay
                                    row={row}
                                    column={column}
                                    timezone={detail?.timezone ?? null}
                                  />
                                }
                                value={row[column]}
                                onSave={(raw) => saveEdit(row, column, raw)}
                                validate={(raw) => cellCheck(column, raw)}
                              />
                            ) : (
                              <CellDisplay
                                row={row}
                                column={column}
                                timezone={detail?.timezone ?? null}
                              />
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
                            <IconArrowBackUp size={16} stroke={1.5} />
                          </button>
                        ) : (
                          <button
                            className="row-action"
                            title={t("actions.delete")}
                            onClick={() => void addRule("row_delete", row.id, {})}
                          >
                            <IconTrash size={16} stroke={1.5} />
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {!error && visibleRows.length > 0 && (
            <div className="doc-footer">
              <span>
                {t("console.footerStats", { rows: activeRows.length, paid: paidCount })}
              </span>
              <span>
                {t("console.footerNote")}{" "}
                <span className="doc-footer-revision">
                  {t("console.footerRevision", { n: sheet?.edits.length ?? 0 })}
                </span>
              </span>
            </div>
          )}
        </main>

        <aside className="rail">
          <div className="rail-title">
            {t("rail.operations")} · {t(`phase.${phase}`)}
          </div>

          {/* a phase carries only its own operation's parameters; tournament
              configuration is Setup's, and a phase with none shows no panel
              (spec etl-console: "Operation parameters") */}
          {phase === "load" && <ImportPanel slug={tournament.slug} onImported={refresh} />}
          {phase === "matching" && <MatchPanel slug={tournament.slug} onChanged={refresh} />}
          {phase === "dedup" && <DedupPanel slug={tournament.slug} onChanged={refresh} />}
          {phase === "payments" && (
            <>
              <TolerancePanel detail={detail} slug={tournament.slug} onSaved={refresh} />
              <PaymentsPanel slug={tournament.slug} onChanged={refresh} />
            </>
          )}
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

          <ManualEditsRail
            entries={phaseEdits}
            rows={rows}
            timezone={detail?.timezone ?? null}
            onUndo={(ruleIds) => void undoEdit(ruleIds)}
          />
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

      {pendingPhase !== null && (
        <div className="modal-backdrop" onClick={() => setPendingPhase(null)}>
          <div className="modal" onClick={(event) => event.stopPropagation()}>
            <h2>{t("console.leaveSetup.title")}</h2>
            <p>{t("console.leaveSetup.body")}</p>
            <div className="modal-actions">
              <button
                type="button"
                className="secondary"
                onClick={() => setPendingPhase(null)}
              >
                {t("common.cancel")}
              </button>
              <button
                type="button"
                className="btn-primary"
                onClick={() => {
                  navigate(routes.consolePath(tournament.slug, pendingPhase));
                  setPendingPhase(null);
                }}
              >
                {t("console.leaveSetup.confirm")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
