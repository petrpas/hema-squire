import { type ReactNode } from "react";
import { useTranslation } from "react-i18next";

import AccountMenu from "./AccountMenu";
import { type Account } from "./api";

/** The four filter tabs the fencer's world is cut into. The first three
 *  partition every published tournament — upcoming with registration not open,
 *  upcoming with it open, and already held — while `mine` cuts across them. */
export type HomeTab = "announced" | "open" | "past" | "mine";

export const HOME_TABS: HomeTab[] = ["announced", "open", "past", "mine"];

/** The heading both the tournament list and a tournament's detail render
 *  inside, so opening a tournament reads as the same page rather than a
 *  different one (spec: "Tournament detail shares the home heading"). The
 *  selected tab lives in App, above both, so the two can never disagree. */
export default function FencerShell({
  account,
  tab,
  onSelectTab,
  counts,
  onProfile,
  onAdmin,
  onOrganizer,
  onLogout,
  children,
}: {
  account: Account | null;
  tab: HomeTab;
  onSelectTab: (tab: HomeTab) => void;
  /** Entry counts shown beside a tab. Announced and Open only — Past is an
   *  archive and Mine a personal list; neither reads as a queue to clear. */
  counts?: Partial<Record<HomeTab, number>>;
  onProfile: () => void;
  onAdmin: () => void;
  onOrganizer: () => void;
  onLogout: () => void;
  children: ReactNode;
}) {
  const { t } = useTranslation();

  return (
    <div className="app">
      <header className="topbar">
        <button className="logo-button" title={t("app.title")}>
          <span className="logo">{t("app.title")}</span>
        </button>
        <nav className="stage-control">
          {HOME_TABS.map((name) => {
            const count = counts?.[name];
            return (
              <button
                key={name}
                className={tab === name ? "active" : ""}
                onClick={() => onSelectTab(name)}
              >
                {t(`home.tabs.${name}`)}
                {count !== undefined && count > 0 && <span className="tab-count">{count}</span>}
              </button>
            );
          })}
        </nav>
        <div className="identity-block">
          <div className="identity-name">{account?.display_name}</div>
          {account && account.hr_id !== null ? (
            <a
              className="identity-hrid"
              href={`https://hemaratings.com/fighters/details/${account.hr_id}/`}
              target="_blank"
              rel="noreferrer"
            >
              {t("home.identity.hrid", { id: account.hr_id })}
            </a>
          ) : (
            <button className="link-button identity-hrid" onClick={onProfile}>
              {t("home.identity.noHemaratings")}
            </button>
          )}
        </div>
        <AccountMenu
          account={account}
          onProfile={onProfile}
          onAdmin={onAdmin}
          onFencer={() => {}}
          onOrganizer={onOrganizer}
          onLogout={onLogout}
        />
      </header>
      {children}
    </div>
  );
}
