import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import AccountMenu from "./AccountMenu";
import type { Account } from "./api";
import FencerIdentity from "./FencerIdentity";
import { home } from "./routes";

/** The four filter tabs the tournament list is cut into. The first three
 *  partition every published tournament — upcoming with registration not open,
 *  upcoming with it open, and already held — while `mine` cuts across them. */
export type HomeTab = "announced" | "open" | "past" | "mine";

export const HOME_TABS: HomeTab[] = ["announced", "open", "past", "mine"];

/** The three a visitor with no account is offered. Mine is an account's own
 *  list and there is no account to list (spec `fencer-home`). */
export const PUBLIC_HOME_TABS: HomeTab[] = ["announced", "open", "past"];

/** The top bar both the tournament list and a tournament's detail render
 *  inside, so opening a tournament reads as the same page rather than a
 *  different one (spec: "Tournament detail shares the home heading").
 *
 *  Three across: the application's own name at the left, what this page is in
 *  the middle, and the visitor at the right. It carries none of the filter
 *  tabs — those belong to the top of the list's own field, which is what
 *  leaves the bar room for a centred title. */
export default function FencerShell({
  account,
  signedIn,
  onLogout,
  onSignIn,
  children,
}: {
  account: Account | null;
  /** Whether there is an account behind the page at all. Not `account !==
   *  null`: that is also true for the moment before the account request
   *  answers, and the bar must not offer sign-in to someone who is signed in. */
  signedIn: boolean;
  onLogout: () => void;
  /** Offer sign-in, with nothing to explain: the visitor asked for it, so the
   *  sign-in screen states no reason. Renders over the current URL, so they
   *  come back to the page they were reading. */
  onSignIn: () => void;
  children: ReactNode;
}) {
  const { t } = useTranslation();

  return (
    <div className="app">
      {/* The two sides are equal flex tracks and the title is what is left
          between them, which is what puts it at the true centre rather than at
          the centre of whatever the sides did not take. Below 768px the bar
          wraps and the title drops to a full-width second row — order and
          flex-basis do the whole job, so nothing re-renders on a resize and
          there is no first-paint flash of the wrong layout. */}
      <header className="topbar">
        <div className="topbar-side">
          <Link className="logo-button" to={home()} title={t("app.title")}>
            <span className="logo">{t("app.title")}</span>
          </Link>
        </div>
        <span className="topbar-title">{t("app.listTitle")}</span>
        <div className="topbar-side topbar-side-end">
          {signedIn ? (
            <>
              {/* Hidden below 768px, where the same identity is shown inside
                  the account menu instead — the bar has no room for it. */}
              <div className="identity-block">
                <FencerIdentity account={account} />
              </div>
              <AccountMenu account={account} onLogout={onLogout} />
            </>
          ) : (
            /* With no account there is no identity and no menu entry that acts
               on one, so the menu is absent rather than rendered empty, and
               sign-in stands where the name would (spec `public-browsing`). */
            <div className="signin-block">
              <button type="button" className="tertiary" onClick={onSignIn}>
                {t("menu.signIn")}
              </button>
            </div>
          )}
        </div>
      </header>
      {children}
    </div>
  );
}
