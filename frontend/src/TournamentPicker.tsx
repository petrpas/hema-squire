import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { type Tournament, api, setToken } from "./api";

export default function TournamentPicker({
  onPick,
  onLogout,
}: {
  onPick: (tournament: Tournament) => void;
  onLogout: () => void;
}) {
  const { t } = useTranslation();
  const [tournaments, setTournaments] = useState<Tournament[] | null>(null);

  useEffect(() => {
    api.tournaments().then(setTournaments, () => setTournaments([]));
  }, []);

  return (
    <div className="login-page">
      <div className="login-card">
        <h1>{t("picker.title")}</h1>
        {tournaments === null ? (
          <p>{t("common.loading")}</p>
        ) : tournaments.length === 0 ? (
          <p>{t("picker.empty")}</p>
        ) : (
          <ul className="picker-list">
            {tournaments.map((tournament) => (
              <li key={tournament.slug}>
                <button onClick={() => onPick(tournament)}>
                  <strong>{tournament.display_name}</strong>
                  <span>{new Date(tournament.date).toLocaleDateString("cs")}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
        <button
          className="link-button"
          onClick={() => {
            setToken(null);
            onLogout();
          }}
        >
          {t("common.logout")}
        </button>
      </div>
    </div>
  );
}
