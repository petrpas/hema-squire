import { type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import AccountMenu from "./AccountMenu";
import FencerIdentity from "./FencerIdentity";
import { useTabBand } from "./useTabBand";
import { home } from "./routes";
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
  const band = useTabBand(tab);

  return (
    <div className="app">
      {/* One flat row of four children. Below 768px the bar wraps and the tab
          band is pushed onto a second line by CSS order and flex-basis alone —
          no width branch in JavaScript, so nothing re-renders on a resize and
          there is no first-paint flash of the wrong layout. */}
      <header className="topbar">
        <button className="logo-button" title={t("app.title")}>
          <span className="logo">{t("app.title")}</span>
        </button>
        <nav className="stage-control stage-control-band" ref={band}>
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
        {/* Hidden below 768px, where the same identity is shown inside the
            account menu instead — the bar has no room for it there. */}
        <div className="identity-block">
          <FencerIdentity account={account} />
        </div>
        <AccountMenu account={account} onLogout={onLogout} />
      </header>
      {children}
    </div>
  );
}
