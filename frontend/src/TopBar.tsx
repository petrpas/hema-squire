import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import AccountMenu from "./AccountMenu";
import type { Account } from "./api";
import FencerIdentity from "./FencerIdentity";
import { home } from "./routes";

/** The bar across the top of the fencer's screens and of the pages reached
 *  from the account menu. Its application name is the way back to the
 *  tournament list from any of them (spec profile-page, "Account menu").
 *
 *  Three across: the application's own name at the left, what this page is in
 *  the middle, and the visitor at the right. It sets no skin: the page around
 *  it decides that. */
export default function TopBar({
  account,
  signedIn,
  onLogout,
  onSignIn,
}: {
  account: Account | null;
  /** Whether there is an account behind the page at all. Not `account !==
   *  null`: that is also true for the moment before the account request
   *  answers, and the bar must not offer sign-in to someone who is signed in. */
  signedIn: boolean;
  onLogout: () => void;
  /** Offer sign-in. Absent on a page that is only reached signed in. */
  onSignIn?: () => void;
}) {
  const { t } = useTranslation();

  return (
    // The two sides are equal flex tracks and the title is what is left
    // between them, which is what puts it at the true centre rather than at
    // the centre of whatever the sides did not take. Below 768px the bar wraps
    // and the title drops to a full-width second row — order and flex-basis do
    // the whole job, so nothing re-renders on a resize and there is no
    // first-paint flash of the wrong layout.
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
          onSignIn !== undefined && (
            <div className="signin-block">
              <button type="button" className="button-pill" onClick={onSignIn}>
                {t("menu.signIn")}
              </button>
            </div>
          )
        )}
      </div>
    </header>
  );
}
