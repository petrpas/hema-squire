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
import { FloorTabBar } from "./FloorTabBar";
import type { FloorSummary } from "./floorApi";
import NotYet from "./NotYet";
import PlanTab from "./plan/PlanTab";
import PoolsTab from "./pools/PoolsTab";
import SchedulePanel from "./schedule/SchedulePanel";
import FloorSetupTab from "./setup/FloorSetupTab";
import { barTabs, type FloorBarTab, type FloorTab, IMPLEMENTED, SCHEDULE_TAB } from "./tabs";
import TodayTab from "./today/TodayTab";
import { useNarrow } from "./useNarrow";

/** The tournament-day console: the office console's bar, eight tabs in a
 *  fixed order, and the schedule beside the work (spec floor-console). A thin
 *  orchestrator; each tab is its own directory. */
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
  const narrow = useNarrow();
  // the schedule tab is the bar's, not the address's: selecting it leaves the
  // tab in the address as it was, which is where the console returns when the
  // window widens and the schedule goes back beside the work
  const [scheduleOpen, setScheduleOpen] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [pending, setPending] = useState<FloorTab | null>(null);
  // bumped when a plan changes, so the schedule panel reads it again
  const [revision, setRevision] = useState(0);

  function changed() {
    setRevision((r) => r + 1);
    onChanged();
  }

  useEffect(() => {
    api.account().then(setAccount, () => setAccount(null));
  }, []);

  useEffect(() => {
    if (!narrow) setScheduleOpen(false);
  }, [narrow]);

  const slug = tournament.slug;

  // Leaving Setup with unsaved changes is confirmed, as in the office console
  // (spec floor-setup, Floor Setup saves as office Setup does).
  function select(next: FloorBarTab) {
    if (next === SCHEDULE_TAB) {
      setScheduleOpen(true);
      return;
    }
    setScheduleOpen(false);
    if (next === tab) return;
    if (tab === "setup" && dirty) setPending(next);
    else navigate(routes.floorPath(slug, next));
  }

  const shown: FloorBarTab = scheduleOpen ? SCHEDULE_TAB : tab;
  // beside every tab but Setup, where the screen is wide enough
  const besideWork = !narrow && tab !== "setup";

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

      <FloorTabBar
        tabs={barTabs(narrow)}
        tab={shown}
        badges={summary.badges}
        dirty={dirty ? "setup" : null}
        onSelect={select}
      />

      <div className="workspace floor-workspace">
        <div
          className="floor-work"
          role="tabpanel"
          id={`floor-tabpanel-${tab}`}
          aria-labelledby={`floor-tab-${tab}`}
          hidden={scheduleOpen}
        >
          {tab === "setup" ? (
            <FloorSetupTab slug={slug} onSaved={changed} onDirtyChange={setDirty} />
          ) : tab === "today" ? (
            <TodayTab slug={slug} />
          ) : tab === "bracket" ? (
            <BracketTab slug={slug} discipline={discipline} />
          ) : tab === "pools" ? (
            <PoolsTab slug={slug} discipline={discipline} />
          ) : tab === "checkin" ? (
            <CheckinTab slug={slug} discipline={discipline} />
          ) : tab === "plan" ? (
            <PlanTab slug={slug} onChanged={changed} />
          ) : tab === "data" ? (
            <DataTab
              slug={slug}
              keptByOrganizer={tournament.registrations_kept_by === "organizer"}
            />
          ) : (
            !IMPLEMENTED.has(tab) && <NotYet />
          )}
        </div>
        {(besideWork || scheduleOpen) && (
          <SchedulePanel slug={slug} revision={revision} asTabPanel={scheduleOpen} />
        )}
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
                  navigate(routes.floorPath(slug, pending));
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
