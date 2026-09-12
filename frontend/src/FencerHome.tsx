import { type ReactNode, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useOutletContext } from "react-router-dom";
import { api, logoUrl, type OpenTournament } from "./api";
import DotJoined from "./DotJoined";
import { HOME_TABS, type HomeTab, PUBLIC_HOME_TABS } from "./FencerShell";
import { openingHourIn } from "./openingMoment";
import { consolePath, detail, home } from "./routes";
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

function StatusBadge({ tournament }: { tournament: OpenTournament }) {
  const { t } = useTranslation();
  if (tournament.registration_status === "open") {
    return <span className="chip status-open">{t("home.status.open")}</span>;
  }
  if (tournament.registration_status === "elsewhere") {
    // states where registration is, never that it is closed: this tournament
    // never had a window here (design add-registrations-kept-by D4)
    return <span className="chip">{t("home.status.elsewhere")}</span>;
  }
  if (tournament.registration_status === "opens_on") {
    // the status itself is the server's, computed against the same resolved
    // moment the detail page reads, so the card, the tabs and the page cannot
    // disagree at the boundary. The hour is stated only where the organizer
    // set one (change add-registration-open-time)
    const date = tournament.registration_opens_on
      ? new Date(tournament.registration_opens_on).toLocaleDateString("cs")
      : "";
    const hour = openingHourIn(tournament.registration_opens_at, tournament.timezone);
    return (
      <span className="chip">
        {hour ? t("home.status.opensAt", { date, time: hour }) : t("home.status.opensOn", { date })}
      </span>
    );
  }
  return <span className="chip status-closed">{t("home.status.closed")}</span>;
}

/** What the account's own bond to a listed tournament is: its registration
 *  state where it holds or held one, an organizer mark where that is the only
 *  bond, and the registration status otherwise. */
function BondBadge({ tournament }: { tournament: OpenTournament }) {
  const { t } = useTranslation();
  const state = tournament.my_registration_state;
  // Absent, not "none", when there is no account behind the page — a visitor
  // without one has no standing to state (spec `public-browsing`).
  if (state !== undefined && state !== "none") {
    return <span className="chip">{t(`registration.state.${state}`)}</span>;
  }
  if (tournament.organized === true) {
    return <span className="chip organizer-chip">{t("home.organized")}</span>;
  }
  return <StatusBadge tournament={tournament} />;
}

/** Logo, then four lines: name, subtitle, date and place in the heavier
 *  weight, organizers. Every line degrades cleanly when its field is absent —
 *  no blank line and no stray middle dot is left behind. */
function CardHeading({ tournament, badge }: { tournament: OpenTournament; badge: ReactNode }) {
  return (
    <div className="home-card-header">
      {tournament.has_logo && (
        <img className="home-card-logo" src={logoUrl(tournament.slug)} alt="" />
      )}
      <div className="home-card-heading">
        <h2>{tournament.display_name}</h2>
        {tournament.subtitle && <p className="home-card-subtitle">{tournament.subtitle}</p>}
        {/* the town alone, as plain text: everyone knows where Brno is, and
            the card is itself a link, so a link inside it has nowhere to go.
            Where in town is read on the tournament's own page. */}
        <DotJoined
          className="home-card-when"
          parts={[
            new Date(tournament.date).toLocaleDateString("cs"),
            tournament.city?.trim() ? tournament.city : null,
          ]}
        />
        {tournament.organizers.length > 0 && (
          <p className="home-card-organizers">
            {tournament.organizers.map((organizer, index) => (
              // biome-ignore lint/suspicious/noArrayIndexKey: a read-only list rebuilt from props; position is the only identity these rows have
              <span key={index}>
                {index > 0 && ", "}
                {organizer.link ? (
                  <a
                    className="detail-inline-link"
                    href={organizer.link}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {organizer.name}
                  </a>
                ) : (
                  organizer.name
                )}
              </span>
            ))}
          </p>
        )}
      </div>
      {badge}
    </div>
  );
}

/** One entry of the list.
 *
 *  The card is a container rather than one big link, because an organizer's
 *  Manage control is a link of its own and a nested interactive element inside
 *  an anchor is invalid and behaves unpredictably (design Decision 6). The
 *  card's whole body remains the link to the tournament, and the hover
 *  treatment stays on the card, so nothing about it reads differently. */
function TournamentCard({
  tournament,
  badge,
  tab,
}: {
  tournament: OpenTournament;
  badge: ReactNode;
  tab: HomeTab | null;
}) {
  const { t } = useTranslation();
  return (
    <li className="rail-card home-card">
      <Link
        className="home-card-body"
        to={detail(tournament.slug)}
        state={tab === null ? undefined : { tab }}
      >
        <CardHeading tournament={tournament} badge={badge} />
        <div className="chips">
          {tournament.disciplines.map((d) => (
            <span key={d.slug} className="chip">
              {d.name} {d.taken}/{d.capacity}
              {d.queue_length > 0 ? ` (+${d.queue_length})` : ""}
            </span>
          ))}
        </div>
      </Link>
      {/* Present only for an account that may manage this tournament, and the
          only thing that makes an organizer's list differ from anyone else's
          (spec `fencer-home`, Managing a tournament from its card). A link,
          so middle-click opens the console in a new tab. */}
      {tournament.organized === true && (
        <Link className="tertiary home-card-manage" to={consolePath(tournament.slug)}>
          {t("home.manage")}
        </Link>
      )}
    </li>
  );
}

/** The upcoming list, fetched once and split by registration status — the two
 *  upcoming tabs are two views of one payload, so switching between them costs
 *  no request. */
export function useUpcoming(): {
  announced: OpenTournament[] | null;
  open: OpenTournament[] | null;
} {
  const [upcoming, setUpcoming] = useState<OpenTournament[] | null>(null);

  useEffect(() => {
    api.openTournaments().then(setUpcoming, () => setUpcoming([]));
  }, []);

  return {
    announced: upcoming?.filter((tt) => tt.registration_status !== "open") ?? null,
    open: upcoming?.filter((tt) => tt.registration_status === "open") ?? null,
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
    <nav className="stage-control stage-control-band home-tabs" ref={band}>
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
  const { tab, signedIn, counts, announced, open, mine } = useOutletContext<FencerOutletContext>();
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
            {list.map((tournament) => (
              <TournamentCard
                key={tournament.slug}
                tournament={tournament}
                tab={tab}
                badge={
                  tab === "past" || tab === "mine" ? (
                    <BondBadge tournament={tournament} />
                  ) : (
                    <StatusBadge tournament={tournament} />
                  )
                }
              />
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
