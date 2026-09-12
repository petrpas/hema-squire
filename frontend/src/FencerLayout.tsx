import { useEffect, useMemo, useRef, useState } from "react";
import { Outlet, useLocation, useSearchParams } from "react-router-dom";
import { type Account, api, type OpenTournament } from "./api";
import { type FencerOutletContext, type ResumeTab, useUpcoming } from "./FencerHome";
import FencerShell, { HOME_TABS, type HomeTab } from "./FencerShell";
import i18n from "./i18n";
import Login from "./Login";
import { credentialChanged, useCredential, useSignOut } from "./session";

function namedTab(value: string | null): HomeTab | null {
  return value !== null && (HOME_TABS as readonly string[]).includes(value)
    ? (value as HomeTab)
    : null;
}

/** The tab to open when the URL names none: the first of Mine, Open,
 *  Announced that has something in it (spec `fencer-home`, The default filter
 *  tab follows what there is to show). `null` while the lists it reads have
 *  not arrived — the caller shows the loading treatment rather than choosing
 *  on incomplete information and swapping afterwards.
 *
 *  An anonymous visitor has no Mine and starts the sequence at Open, which is
 *  what passing `mine: undefined` means here. */
function resolveDefault(lists: {
  mine?: OpenTournament[] | null;
  open: OpenTournament[] | null;
  announced: OpenTournament[] | null;
}): HomeTab | null {
  if (lists.open === null || lists.announced === null) return null;
  if (lists.mine === null) return null;
  if (lists.mine !== undefined && lists.mine.length > 0) return "mine";
  if (lists.open.length > 0) return "open";
  return "announced";
}

/** The fencer area's layout route (design D4, formerly `FencerArea`): the
 *  heading both the tournament list and a tournament's detail render inside,
 *  so navigating between `/` and `/t/:slug` never unmounts it and the account
 *  and list fetches never repeat (spec: "Tournament detail shares the home
 *  heading").
 *
 *  Mounted whether or not there is an account: both routes under it are public
 *  (spec `public-browsing`). The one tab that is not — Mine, which is an
 *  account's own list — is gated here rather than by splitting `/` in the
 *  route table, since both halves are otherwise the same screen. */
export default function FencerLayout() {
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const signedIn = useCredential() !== null;
  const onLogout = useSignOut();
  // `/t/:slug` carries no `?tab=` of its own; the tab a card was opened from
  // rides along as navigation state (set by the card's <Link>) so the detail's
  // close control returns to the list the tournament was opened from.
  const openedFromTab = (location.state as { tab?: HomeTab } | null)?.tab ?? null;
  const named = namedTab(searchParams.get("tab") ?? openedFromTab);
  const [account, setAccount] = useState<Account | null>(null);
  const { announced, open } = useUpcoming();
  const [mine, setMine] = useState<OpenTournament[] | null>(null);
  // A visitor who reached for something needing an account. The sign-in screen
  // renders over the current URL and the reason is stated on it, so they come
  // back to the page they were reading (spec `public-browsing`).
  const [prompt, setPrompt] = useState<{ reason?: string; resume?: ResumeTab } | null>(null);
  // Outlives the sign-in screen, which is the point: the screen that asked for
  // it is unmounted while the form stands in its place, so it cannot keep the
  // intent itself, and navigation state lands a commit too late to be read as
  // that screen's initial state.
  const [resume, setResume] = useState<ResumeTab | null>(null);

  useEffect(() => {
    if (!signedIn) {
      setAccount(null);
      setMine(null);
      // back to the locale a visitor with no account reads, so a preference
      // left behind by a session that has ended does not outlive it
      void i18n.changeLanguage("cs");
      return;
    }
    api.account().then(
      (it) => {
        setAccount(it);
        // the account's own language, applied on the screen already open rather
        // than waiting for a navigation (spec `localization`)
        void i18n.changeLanguage(it.language);
      },
      () => setAccount(null),
    );
    // Fetched here rather than lazily by the list, because whether it is empty
    // is what the default tab turns on. One extra request per visit for an
    // account, none for a visitor without one.
    api.myTournaments().then(setMine, () => setMine([]));
  }, [signedIn]);

  const resolved = resolveDefault({
    mine: signedIn ? mine : undefined,
    open,
    announced,
  });
  // Latched: resolution happens once per visit to the bare URL and is never
  // recomputed, so a list that empties while the visitor reads it does not
  // move them off the tab they are on, and a tab they selected stands.
  const latched = useRef<HomeTab | null>(null);
  if (latched.current === null && resolved !== null) latched.current = resolved;
  const tab = named ?? latched.current;

  const counts = useMemo(
    () => ({ announced: announced?.length, open: open?.length }),
    [announced, open],
  );

  // Mine is the one tab behind the gate. Login renders in place, leaving
  // `/?tab=mine` in the address bar, so signing in lands on the list asked for.
  const gated = named === "mine" && !signedIn;
  if (gated || prompt !== null) {
    return (
      <Login
        notice={gated ? "menu.signInForMine" : prompt?.reason}
        onLogin={() => {
          setResume(prompt?.resume ?? null);
          setPrompt(null);
          credentialChanged();
        }}
      />
    );
  }

  /** `reason` is a locale key naming why an account is needed, stated on the
   *  sign-in screen. Absent where the visitor asked to sign in outright and
   *  there is nothing to explain. */
  function onSignIn(reason?: string, wanted?: ResumeTab) {
    setPrompt({ reason, resume: wanted });
  }

  return (
    <FencerShell
      account={account}
      signedIn={signedIn}
      onLogout={onLogout}
      onSignIn={() => onSignIn()}
    >
      <Outlet
        context={
          {
            tab,
            signedIn,
            counts,
            announced,
            open,
            mine,
            onSignIn,
            resume,
            clearResume: () => setResume(null),
          } satisfies FencerOutletContext
        }
      />
    </FencerShell>
  );
}
