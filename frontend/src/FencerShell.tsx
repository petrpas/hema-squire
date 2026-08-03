import { type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import AccountMenu from "./AccountMenu";
import { home, profile } from "./routes";
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
  counts,
  onLogout,
  children,
}: {
  account: Account | null;
  tab: HomeTab;
  /** Entry counts shown beside a tab. Announced and Open only — Past is an
   *  archive and Mine a personal list; neither reads as a queue to clear. */
  counts?: Partial<Record<HomeTab, number>>;
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
              <Link key={name} className={tab === name ? "active" : ""} to={home(name)}>
                {t(`home.tabs.${name}`)}
                {count !== undefined && count > 0 && <span className="tab-count">{count}</span>}
              </Link>
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
            <Link className="link-button identity-hrid" to={profile()}>
              {t("home.identity.noHemaratings")}
            </Link>
          )}
        </div>
        <AccountMenu account={account} onLogout={onLogout} />
      </header>
      {children}
    </div>
  );
}
