import type { ReactNode } from "react";

import type { Account } from "./api";
import TopBar from "./TopBar";

/** The four filter tabs the tournament list is cut into. The first three
 *  partition every published tournament — upcoming with registration not open,
 *  upcoming with it open, and already held — while `mine` cuts across them. */
export type HomeTab = "announced" | "open" | "past" | "mine";

export const HOME_TABS: HomeTab[] = ["announced", "open", "past", "mine"];

/** The three a visitor with no account is offered. Mine is an account's own
 *  list and there is no account to list (spec `fencer-home`). */
export const PUBLIC_HOME_TABS: HomeTab[] = ["announced", "open", "past"];

/** The shell both the tournament list and a tournament's detail render
 *  inside, so opening a tournament reads as the same page rather than a
 *  different one (spec: "Tournament detail shares the home heading"). It
 *  carries none of the filter tabs — those belong to the top of the list's
 *  own field, which is what leaves the bar room for a centred title. */
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
  return (
    // The fencer side's skin (spec design-system, Skins): set here, on the
    // root, and read by tokens.css alone.
    <div className="app" data-skin="night">
      <TopBar account={account} signedIn={signedIn} onLogout={onLogout} onSignIn={onSignIn} />
      {children}
    </div>
  );
}
