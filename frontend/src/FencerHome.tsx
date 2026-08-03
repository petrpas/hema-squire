import { type ReactNode, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { type HomeTab } from "./FencerShell";
import { type OpenTournament, api, logoUrl } from "./api";

function StatusBadge({ tournament }: { tournament: OpenTournament }) {
  const { t } = useTranslation();
  if (tournament.registration_status === "open") {
    return <span className="chip status-open">{t("home.status.open")}</span>;
  }
  if (tournament.registration_status === "opens_on") {
    return (
      <span className="chip">
        {t("home.status.opensOn", {
          date: tournament.registration_opens_on
            ? new Date(tournament.registration_opens_on).toLocaleDateString("cs")
            : "",
        })}
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
  if (tournament.my_registration_state !== "none") {
    return (
      <span className="chip">{t(`registration.state.${tournament.my_registration_state}`)}</span>
    );
  }
  if (tournament.organized) {
    return <span className="chip organizer-chip">{t("home.organized")}</span>;
  }
  return <StatusBadge tournament={tournament} />;
}

/** Logo, then four lines: name, subtitle, date and place in the heavier
 *  weight, organizers. Every line degrades cleanly when its field is absent —
 *  no blank line and no stray middle dot is left behind. */
function CardHeading({
  tournament,
  badge,
}: {
  tournament: OpenTournament;
  badge: ReactNode;
}) {
  const dateAndPlace = [
    new Date(tournament.date).toLocaleDateString("cs"),
    tournament.location,
  ].filter(Boolean);

  return (
    <div className="home-card-header">
      {tournament.has_logo && (
        <img className="home-card-logo" src={logoUrl(tournament.slug)} alt="" />
      )}
      <div className="home-card-heading">
        <h2>{tournament.display_name}</h2>
        {tournament.subtitle && (
          <p className="home-card-subtitle">{tournament.subtitle}</p>
        )}
        <p className="home-card-when">{dateAndPlace.join(" · ")}</p>
        {tournament.organizers.length > 0 && (
          <p className="home-card-organizers">
            {tournament.organizers.map((organizer, index) => (
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

function TournamentCard({
  tournament,
  badge,
  onOpen,
}: {
  tournament: OpenTournament;
  badge: ReactNode;
  onOpen: (slug: string) => void;
}) {
  return (
    <li>
      <button className="rail-card home-card" onClick={() => onOpen(tournament.slug)}>
        <CardHeading tournament={tournament} badge={badge} />
        <div className="chips">
          {tournament.disciplines.map((d) => (
            <span key={d.slug} className="chip">
              {d.name} {d.taken}/{d.capacity}
              {d.queue_length > 0 ? ` (+${d.queue_length})` : ""}
            </span>
          ))}
        </div>
      </button>
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

export default function FencerHome({
  tab,
  announced,
  open,
  onOpen,
}: {
  tab: HomeTab;
  announced: OpenTournament[] | null;
  open: OpenTournament[] | null;
  /** `readOnly` marks a tournament already held: its detail opens without
   *  register, payment or cancel actions. */
  onOpen: (slug: string, readOnly?: boolean) => void;
}) {
  const { t } = useTranslation();
  const [held, setHeld] = useState<OpenTournament[] | null>(null);
  const [mine, setMine] = useState<OpenTournament[] | null>(null);

  useEffect(() => {
    if (tab === "past" && held === null) {
      api.heldTournaments().then(setHeld, () => setHeld([]));
    }
    if (tab === "mine" && mine === null) {
      api.myTournaments().then(setMine, () => setMine([]));
    }
  }, [tab, held, mine]);

  const today = new Date().toISOString().slice(0, 10);
  const list =
    tab === "announced" ? announced : tab === "open" ? open : tab === "past" ? held : mine;

  return (
    <div className="workspace home-workspace">
      {list === null ? (
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
              badge={
                tab === "past" || tab === "mine" ? (
                  <BondBadge tournament={tournament} />
                ) : (
                  <StatusBadge tournament={tournament} />
                )
              }
              onOpen={(slug) => onOpen(slug, tournament.date < today)}
            />
          ))}
        </ul>
      )}
    </div>
  );
}
