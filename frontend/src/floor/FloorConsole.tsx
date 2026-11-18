import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import AccountMenu from "../AccountMenu";
import { type Account, api, type TournamentDetail } from "../api";
import Modal from "../Modal";
import { useAuth } from "../RequireAuth";
import * as routes from "../routes";
import BracketTab from "./bracket/BracketTab";
import CheckinTab from "./checkin/CheckinTab";
import DataTab from "./data/DataTab";
import { FloorLayout } from "./FloorLayout";
import { FloorRail } from "./FloorRail";
import type { FloorSummary } from "./floorApi";
import NotYet from "./NotYet";
import PlanTab from "./plan/PlanTab";
import PoolsTab from "./pools/PoolsTab";
import ResultsTab from "./results/ResultsTab";
import ScheduleTab from "./schedule/ScheduleTab";
import FloorSetupTab from "./setup/FloorSetupTab";
import { barTabs, type FloorTab, IMPLEMENTED, STEP_TABS } from "./tabs";
import TodayTab from "./today/TodayTab";

/** The tournament-day console: the office console's bar across the top, the
 *  tabs as a rail of icons on the left, and each tab's work with its
 *  operations panel beside it, as in the office (spec floor-console). A thin
 *  orchestrator; each tab is its own directory and draws its own frame. */
export default function FloorConsole({
  tournament,
  summary,
  tab,
  discipline,
  onChanged,
}: {
  tournament: TournamentDetail;
  summary: FloorSummary;
  tab: FloorTab;
  /** A step tab's discipline, by slug, from the address (spec floor-today). */
  discipline?: string;
  /** Something was saved; the summary, and with it the badges, is read again. */
  onChanged: () => void;
}) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { onLogout } = useAuth();
  const [account, setAccount] = useState<Account | null>(null);
  const [dirty, setDirty] = useState(false);
  const [pending, setPending] = useState<FloorTab | null>(null);
  // the discipline last chosen on a step tab, carried to the next step tab
  // opened from the rail, through any detour; for the session only (spec
  // floor-console, Step tabs choose their discipline by tabs, kept across
  // the console)
  const [kept, setKept] = useState<string | null>(null);

  useEffect(() => {
    api.account().then(setAccount, () => setAccount(null));
  }, []);

  useEffect(() => {
    if (STEP_TABS.has(tab) && discipline !== undefined) setKept(discipline);
  }, [tab, discipline]);

  const slug = tournament.slug;

  /** Where the rail leads: a step tab at the kept discipline. */
  function pathTo(next: FloorTab): string {
    return routes.floorPath(slug, next, STEP_TABS.has(next) ? (kept ?? undefined) : undefined);
  }

  // Leaving Setup with unsaved changes is confirmed, as in the office console
  // (spec floor-setup, Floor Setup saves as office Setup does).
  function select(next: FloorTab) {
    if (next === tab) return;
    if (tab === "setup" && dirty) setPending(next);
    else navigate(pathTo(next));
  }

  const planned = summary.plan_schedule !== false;
  const fallback = kept ?? undefined;

  return (
    <div className="app">
      <header className="topbar">
        <Link className="logo-button" to={routes.home()} title={t("app.title")}>
          <span className="logo">{t("app.title")}</span>
        </Link>
        <nav className="stage-control">
          <Link to={routes.consolePath(slug)}>{t("stage.pre")}</Link>
          <button type="button" className="active">
            {t("stage.in")}
          </button>
          <button type="button" disabled>
            {t("stage.post")}
          </button>
        </nav>
        <div className="tournament-info">
          <div className="tournament-name">{tournament.display_name}</div>
          <div className="tournament-date">
            {new Date(tournament.date).toLocaleDateString("cs")}
          </div>
        </div>
        <AccountMenu account={account} onLogout={onLogout} />
      </header>

      <div className="floor-body">
        <FloorRail
          tabs={barTabs(planned)}
          tab={tab}
          badges={summary.badges}
          dirty={dirty ? "setup" : null}
          onSelect={select}
        />

        <div
          className="workspace floor-workspace"
          role="tabpanel"
          id={`floor-tabpanel-${tab}`}
          aria-labelledby={`floor-tab-${tab}`}
        >
          {tab === "setup" ? (
            <FloorLayout tab="setup">
              <FloorSetupTab
                slug={slug}
                missing={summary.setup_missing}
                onSaved={onChanged}
                onDirtyChange={setDirty}
              />
            </FloorLayout>
          ) : tab === "today" ? (
            <FloorLayout tab="today">
              <TodayTab slug={slug} />
            </FloorLayout>
          ) : tab === "schedule" ? (
            <ScheduleTab slug={slug} />
          ) : tab === "results" ? (
            <ResultsTab slug={slug} discipline={discipline} fallback={fallback} />
          ) : tab === "bracket" ? (
            <BracketTab slug={slug} discipline={discipline} fallback={fallback} />
          ) : tab === "pools" ? (
            <PoolsTab slug={slug} discipline={discipline} fallback={fallback} />
          ) : tab === "checkin" ? (
            <CheckinTab slug={slug} discipline={discipline} />
          ) : tab === "plan" ? (
            <PlanTab slug={slug} onChanged={onChanged} />
          ) : tab === "data" ? (
            <DataTab
              slug={slug}
              discipline={discipline}
              fallback={fallback}
              keptByOrganizer={tournament.registrations_kept_by === "organizer"}
            />
          ) : (
            !IMPLEMENTED.has(tab) && (
              <FloorLayout tab={tab}>
                <NotYet />
              </FloorLayout>
            )
          )}
        </div>
      </div>

      {pending !== null && (
        <Modal onClose={() => setPending(null)}>
          <div className="modal">
            <h2>{t("console.leaveSetup.title")}</h2>
            <p>{t("console.leaveSetup.body")}</p>
            <div className="modal-actions">
              <button type="button" className="secondary" onClick={() => setPending(null)}>
                {t("common.cancel")}
              </button>
              <button
                type="button"
                className="btn-primary"
                onClick={() => {
                  setDirty(false);
                  navigate(pathTo(pending));
                  setPending(null);
                }}
              >
                {t("console.leaveSetup.confirm")}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
