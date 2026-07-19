import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import AccountMenu from "./AccountMenu";
import { type Account, type OpenTournament, api } from "./api";

const MANAGE_STATES = new Set(["reserved", "paid", "substitute"]);

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

function TournamentCard({
  tournament,
  onOpen,
}: {
  tournament: OpenTournament;
  onOpen: (slug: string) => void;
}) {
  const { t } = useTranslation();
  const manage = MANAGE_STATES.has(tournament.my_registration_state);

  return (
    <li className="rail-card home-card">
      <div className="home-card-header">
        <div>
          <h2>{tournament.display_name}</h2>
          <p className="rail-hint">
            {tournament.organizer_names.join(", ")} · {new Date(tournament.date).toLocaleDateString("cs")}
            {tournament.location ? ` · ${tournament.location}` : ""}
          </p>
        </div>
        <StatusBadge tournament={tournament} />
      </div>
      <div className="chips">
        {tournament.disciplines.map((d) => (
          <span key={d.code} className="chip">
            {d.code} {d.taken}/{d.capacity}
            {d.queue_length > 0 ? ` (+${d.queue_length})` : ""}
          </span>
        ))}
      </div>
      <button className="secondary" onClick={() => onOpen(tournament.slug)}>
        {manage ? t("home.manage") : t("home.register")}
      </button>
    </li>
  );
}

export default function FencerHome({
  onOpen,
  onProfile,
  onAdmin,
  onOrganizer,
  onLogout,
}: {
  onOpen: (slug: string) => void;
  onProfile: () => void;
  onAdmin: () => void;
  onOrganizer: () => void;
  onLogout: () => void;
}) {
  const { t } = useTranslation();
  const [tournaments, setTournaments] = useState<OpenTournament[] | null>(null);
  const [account, setAccount] = useState<Account | null>(null);

  useEffect(() => {
    api.openTournaments().then(setTournaments, () => setTournaments([]));
    api.account().then(setAccount, () => setAccount(null));
  }, []);

  return (
    <div className="login-page">
      <div className="page-menu-corner">
        <AccountMenu
          account={account}
          onProfile={onProfile}
          onAdmin={onAdmin}
          onFencer={() => {}}
          onOrganizer={onOrganizer}
          onLogout={onLogout}
        />
      </div>
      <div className="login-card wide-card">
        <h1>{t("home.title")}</h1>
        {tournaments === null ? (
          <p>{t("common.loading")}</p>
        ) : tournaments.length === 0 ? (
          <p>{t("home.empty")}</p>
        ) : (
          <ul className="home-list">
            {tournaments.map((tournament) => (
              <TournamentCard key={tournament.slug} tournament={tournament} onOpen={onOpen} />
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
