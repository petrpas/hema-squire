import { useEffect, useState } from "react";
import { Outlet, useLocation, useSearchParams } from "react-router-dom";

import FencerShell, { HOME_TABS, type HomeTab } from "./FencerShell";
import { type FencerOutletContext, useUpcoming } from "./FencerHome";
import { useAuth } from "./RequireAuth";
import { type Account, api } from "./api";

function resolveTab(value: string | null): HomeTab {
  return value !== null && (HOME_TABS as readonly string[]).includes(value)
    ? (value as HomeTab)
    : "open";
}

/** The fencer area's layout route (design D4, formerly `FencerArea`): the
 *  heading both Fencer Home and a tournament's detail render inside, so
 *  navigating between `/` and `/t/:slug` never unmounts it and the account
 *  and upcoming-list fetches never repeat (spec: "Tournament detail shares
 *  the home heading"). Mounted only while authenticated. */
export default function FencerLayout() {
  const [searchParams] = useSearchParams();
  const location = useLocation();
  // `/t/:slug` carries no `?tab=` of its own; the tab a card was opened from
  // rides along as navigation state (set by the card's <Link>) purely so the
  // heading's active marker still names it while the detail is open — the
  // close control reads the same state directly (spec: "Tournament detail
  // shares the home heading").
  const openedFromTab = (location.state as { tab?: HomeTab } | null)?.tab ?? null;
  const tab = resolveTab(searchParams.get("tab") ?? openedFromTab);
  const { onLogout } = useAuth();
  const [account, setAccount] = useState<Account | null>(null);
  const { announced, open } = useUpcoming();

  useEffect(() => {
    api.account().then(setAccount, () => setAccount(null));
  }, []);

  return (
    <FencerShell
      account={account}
      tab={tab}
      counts={{ announced: announced?.length, open: open?.length }}
      onLogout={onLogout}
    >
      <Outlet context={{ tab, announced, open } satisfies FencerOutletContext} />
    </FencerShell>
  );
}
