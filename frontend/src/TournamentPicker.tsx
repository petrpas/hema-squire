import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";
import AccountMenu from "./AccountMenu";
import { type Account, api, type Tournament } from "./api";
import { useAuth } from "./RequireAuth";
import { consolePath } from "./routes";
import TournamentCreateDialog, { canCreateTournament } from "./TournamentCreateDialog";

export default function TournamentPicker() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { onLogout } = useAuth();
  const [tournaments, setTournaments] = useState<Tournament[] | null>(null);
  const [creating, setCreating] = useState(false);
  const [account, setAccount] = useState<Account | null>(null);

  useEffect(() => {
    api.tournaments().then(setTournaments, () => setTournaments([]));
    api.account().then(setAccount, () => setAccount(null));
  }, []);

  const canCreate = canCreateTournament(account);

  return (
    <div className="login-page">
      <div className="page-menu-corner">
        <AccountMenu account={account} onLogout={onLogout} />
      </div>
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
                <Link to={consolePath(tournament.slug)}>
                  <strong>{tournament.display_name}</strong>
                  <span className="picker-meta">
                    {/* drafts and published tournaments both live here; only the
                        draft state is marked, published being the resting one */}
                    {tournament.published_at === null && (
                      <span className="picker-draft">{t("picker.draft")}</span>
                    )}
                    <span>{new Date(tournament.date).toLocaleDateString("cs")}</span>
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
        {canCreate && (
          <button type="button" className="secondary" onClick={() => setCreating(true)}>
            {t("picker.newTournament")}
          </button>
        )}
      </div>
      {creating && (
        <TournamentCreateDialog
          onClose={() => setCreating(false)}
          onDone={(tournament) => {
            setCreating(false);
            navigate(consolePath(tournament.slug, "setup"));
          }}
        />
      )}
    </div>
  );
}
