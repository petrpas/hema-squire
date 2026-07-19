import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import AccountMenu from "./AccountMenu";
import { type Account, type OpenTournament, type PastTournament, api } from "./api";

type Tab = "announced" | "open" | "past";

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
  return (
    <li>
      <button className="rail-card home-card" onClick={() => onOpen(tournament.slug)}>
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
      </button>
    </li>
  );
}

function PastCard({
  tournament,
  onOpen,
}: {
  tournament: PastTournament;
  onOpen: (slug: string, readOnly: boolean) => void;
}) {
  const { t } = useTranslation();
  const participated = tournament.my_registration_state !== "none";

  return (
    <li>
      <button className="rail-card home-card" onClick={() => onOpen(tournament.slug, true)}>
        <div className="home-card-header">
          <div>
            <h2>{tournament.display_name}</h2>
            <p className="rail-hint">
              {tournament.organizer_names.join(", ")} · {new Date(tournament.date).toLocaleDateString("cs")}
              {tournament.location ? ` · ${tournament.location}` : ""}
            </p>
          </div>
          {participated ? (
            <span className="chip">{t(`registration.state.${tournament.my_registration_state}`)}</span>
          ) : (
            <span className="chip organizer-chip">{t("home.organized")}</span>
          )}
        </div>
        <div className="chips">
          {tournament.disciplines.map((d) => (
            <span key={d.code} className="chip">
              {d.code} {d.taken}/{d.capacity}
            </span>
          ))}
        </div>
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
  onOpen: (slug: string, readOnly?: boolean) => void;
  onProfile: () => void;
  onAdmin: () => void;
  onOrganizer: () => void;
  onLogout: () => void;
}) {
  const { t } = useTranslation();
  const [tab, setTab] = useState<Tab>("open");
  const [account, setAccount] = useState<Account | null>(null);
  const [tournaments, setTournaments] = useState<OpenTournament[] | null>(null);
  const [past, setPast] = useState<PastTournament[] | null>(null);

  useEffect(() => {
    api.account().then(setAccount, () => setAccount(null));
    api.openTournaments().then(setTournaments, () => setTournaments([]));
  }, []);

  useEffect(() => {
    if (tab === "past" && past === null) {
      api.pastTournaments().then(setPast, () => setPast([]));
    }
  }, [tab, past]);

  const openList = tournaments?.filter((tt) => tt.registration_status === "open") ?? null;
  const announcedList = tournaments?.filter((tt) => tt.registration_status !== "open") ?? null;

  return (
    <div className="app">
      <header className="topbar">
        <button className="logo-button" title={t("app.title")}>
          <span className="logo">{t("app.title")}</span>
        </button>
        <nav className="stage-control">
          <button
            className={tab === "announced" ? "active" : ""}
            onClick={() => setTab("announced")}
          >
            {t("home.tabs.announced")}
          </button>
          <button className={tab === "open" ? "active" : ""} onClick={() => setTab("open")}>
            {t("home.tabs.open")}
          </button>
          <button className={tab === "past" ? "active" : ""} onClick={() => setTab("past")}>
            {t("home.tabs.past")}
          </button>
        </nav>
        <div className="identity-block">
          <div className="identity-name">{account?.display_name}</div>
          {account && account.hr_id !== null ? (
            <a
              className="identity-hrid"
              href={`https://hemaratings.com/fighters/details/${account.hr_id}/`}
              target="_blank"
              rel="noreferrer"
            >
              {t("home.identity.hrid", { id: account.hr_id })}
            </a>
          ) : (
            <button className="link-button identity-hrid" onClick={onProfile}>
              {t("home.identity.noHemaratings")}
            </button>
          )}
        </div>
        <AccountMenu
          account={account}
          onProfile={onProfile}
          onAdmin={onAdmin}
          onFencer={() => {}}
          onOrganizer={onOrganizer}
          onLogout={onLogout}
        />
      </header>

      <div className="workspace home-workspace">
        {tab === "past" ? (
          past === null ? (
            <p>{t("common.loading")}</p>
          ) : past.length === 0 ? (
            <p className="rail-hint">{t("home.empty.past")}</p>
          ) : (
            <ul className="home-list">
              {past.map((tournament) => (
                <PastCard key={tournament.slug} tournament={tournament} onOpen={onOpen} />
              ))}
            </ul>
          )
        ) : tournaments === null ? (
          <p>{t("common.loading")}</p>
        ) : tab === "open" ? (
          openList!.length === 0 ? (
            <p className="rail-hint">{t("home.empty.open")}</p>
          ) : (
            <ul className="home-list">
              {openList!.map((tournament) => (
                <TournamentCard key={tournament.slug} tournament={tournament} onOpen={onOpen} />
              ))}
            </ul>
          )
        ) : announcedList!.length === 0 ? (
          <p className="rail-hint">{t("home.empty.announced")}</p>
        ) : (
          <ul className="home-list">
            {announcedList!.map((tournament) => (
              <TournamentCard key={tournament.slug} tournament={tournament} onOpen={onOpen} />
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
