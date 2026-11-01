import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import AdminTabs, { type AdminTab } from "./admin/AdminTabs";
import PeopleTab from "./admin/PeopleTab";
import { sharedHrGroups } from "./admin/sharedHr";
import TasksTab from "./admin/TasksTab";
import TournamentsTab from "./admin/TournamentsTab";
import {
  type Account,
  type AdminAccount,
  type AdminTournament,
  api,
  type PleaQueueItem,
} from "./api";
import MenuPage from "./MenuPage";

/** The admin panel: pending tasks, people and tournaments, one tab at a time
 *  (spec user-roles, Admin panel). Loads the lists and holds the tab; each tab
 *  is its own section under `admin/`. */
export default function AdminPanel() {
  const { t } = useTranslation();
  const [accounts, setAccounts] = useState<AdminAccount[] | null>(null);
  const [pleas, setPleas] = useState<PleaQueueItem[] | null>(null);
  const [tournaments, setTournaments] = useState<AdminTournament[] | null>(null);
  const [error, setError] = useState(false);
  const [account, setAccount] = useState<Account | null>(null);
  const [tab, setTab] = useState<AdminTab>("tasks");

  function refresh() {
    api.adminAccounts().then(setAccounts, () => setError(true));
    api.adminPleas().then(setPleas, () => setError(true));
    api.adminTournaments().then(setTournaments, () => setError(true));
  }

  useEffect(refresh, []);
  useEffect(() => {
    api.account().then(setAccount, () => setAccount(null));
  }, []);

  const sharedHr = useMemo(() => sharedHrGroups(accounts ?? []), [accounts]);

  return (
    <MenuPage title={t("admin.title")} account={account}>
      {error ? (
        <p className="login-error">{t("admin.error")}</p>
      ) : accounts === null || pleas === null || tournaments === null ? (
        <p>{t("common.loading")}</p>
      ) : (
        <div className="page-card-body">
          <AdminTabs active={tab} openTasks={pleas.length + sharedHr.length} onChoose={setTab} />
          <div role="tabpanel" id={`admin-tabpanel-${tab}`} aria-labelledby={`admin-tab-${tab}`}>
            {tab === "tasks" && <TasksTab pleas={pleas} sharedHr={sharedHr} onChanged={refresh} />}
            {tab === "people" && <PeopleTab accounts={accounts} onChanged={refresh} />}
            {tab === "tournaments" && (
              <TournamentsTab tournaments={tournaments} onChanged={refresh} />
            )}
          </div>
        </div>
      )}
    </MenuPage>
  );
}
