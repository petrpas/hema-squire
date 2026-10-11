import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useOutletContext } from "react-router-dom";
import { api, type OpenTournament } from "./api";
import { HOME_TABS, type HomeTab, PUBLIC_HOME_TABS } from "./FencerShell";
import NextOpening from "./NextOpening";
import { home } from "./routes";
import TournamentCard from "./TournamentCard";
import { useTabBand } from "./useTabBand";

/** What `FencerLayout` provides its two child routes through the outlet
 *  (design D4): the resolved filter tab, whether there is an account behind
 *  the page, and the lists it fetches once, so opening a tournament never
 *  refetches them.
 *
 *  `tab` is null only while the default is still being resolved from those
 *  lists (spec `fencer-home`, The default filter tab follows what there is to
 *  show); the list shows the loading treatment until it is known. */
/** The detail tab a sign-in was reached from; there is one such action. */
export type ResumeTab = "registration";

export interface FencerOutletContext {
  tab: HomeTab | null;
  signedIn: boolean;
  counts: Partial<Record<HomeTab, number>>;
  announced: OpenTournament[] | null;
  open: OpenTournament[] | null;
  mine: OpenTournament[] | null;
  /** Fetch the upcoming list again — once, at a registration opening the
   *  list was counting down to. */
  refreshUpcoming: () => void;
  /** Offer sign-in, optionally stating why (a locale key) and naming the
   *  detail tab the visitor was reaching for. */
  onSignIn: (reason?: string, resume?: ResumeTab) => void;
  /** The tab a signed-out visitor was reaching for when they were sent to
   *  sign in, held by the layout because the screen that asked for it
   *  unmounted while the sign-in form stood in its place. The detail reads it
   *  once the tab exists and then clears it. */
  resume: ResumeTab | null;
  clearResume: () => void;
}

/** The upcoming list, fetched once and split by registration status — the two
 *  upcoming tabs are two views of one payload, so switching between them costs
 *  no request. */
export function useUpcoming(): {
  announced: OpenTournament[] | null;
  open: OpenTournament[] | null;
  refresh: () => void;
} {
  const [upcoming, setUpcoming] = useState<OpenTournament[] | null>(null);
  const refresh = useCallback(() => {
    api.openTournaments().then(setUpcoming, () => setUpcoming([]));
  }, []);

  useEffect(refresh, [refresh]);

  return {
    announced: upcoming?.filter((tt) => tt.registration_status !== "open") ?? null,
    open: upcoming?.filter((tt) => tt.registration_status === "open") ?? null,
    refresh,
  };
}

/** The filter tabs, at the top of the list's own field rather than in the top
 *  bar, which is what leaves the bar room for the application's title (spec
 *  `fencer-home`). Three tabs without an account: Mine is an account's own
 *  list and there is none to list. */
function TabBand({
  tab,
  signedIn,
  counts,
}: {
  tab: HomeTab | null;
  signedIn: boolean;
  counts: Partial<Record<HomeTab, number>>;
}) {
  const { t } = useTranslation();
  const band = useTabBand(tab ?? "");
  return (
    <nav className="stage-control stage-control-band stage-control-pill home-tabs" ref={band}>
      {(signedIn ? HOME_TABS : PUBLIC_HOME_TABS).map((name) => {
        const count = counts[name];
        return (
          <Link key={name} className={tab === name ? "active" : ""} to={home(name)}>
            {t(`home.tabs.${name}`)}
            {count !== undefined && count > 0 && <span className="tab-count">{count}</span>}
          </Link>
        );
      })}
    </nav>
  );
}

export default function FencerHome() {
  const { tab, signedIn, counts, announced, open, mine, refreshUpcoming } =
    useOutletContext<FencerOutletContext>();
  const { t } = useTranslation();
  const [held, setHeld] = useState<OpenTournament[] | null>(null);

  useEffect(() => {
    // The Past list takes no part in the default tab, so it stays lazy — it is
    // an archive, fetched when asked for.
    if (tab === "past" && held === null) {
      api.heldTournaments().then(setHeld, () => setHeld([]));
    }
  }, [tab, held]);

  const list =
    tab === null
      ? null
      : tab === "announced"
        ? announced
        : tab === "open"
          ? open
          : tab === "past"
            ? held
            : mine;

  return (
    <div className="workspace home-workspace">
      <div className="home-column">
        {announced !== null && <NextOpening announced={announced} onOpened={refreshUpcoming} />}
        <TabBand tab={tab} signedIn={signedIn} counts={counts} />
        {list === null || tab === null ? (
          <p>{t("common.loading")}</p>
        ) : list.length === 0 ? (
          <>
            <p className="rail-hint">{t(`home.empty.${tab}`)}</p>
            {tab === "open" && announced !== null && announced.length > 0 && (
              <p className="rail-hint">{t("home.empty.openSeeAnnounced")}</p>
            )}
          </>
        ) : (
          <ul className="home-list">
            {list.map((tournament, index) => (
              <TournamentCard
                key={tournament.slug}
                tournament={tournament}
                tab={tab}
                position={index + 1}
              />
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
