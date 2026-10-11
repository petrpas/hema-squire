import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";
import { type Account, api, type Tournament } from "./api";
import MenuPage from "./MenuPage";
import { consolePath } from "./routes";
import TournamentCreateDialog, { canCreateTournament } from "./TournamentCreateDialog";

export default function TournamentPicker() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [tournaments, setTournaments] = useState<Tournament[] | null>(null);
  const [creating, setCreating] = useState(false);
  const [account, setAccount] = useState<Account | null>(null);

  useEffect(() => {
    api.tournaments().then(setTournaments, () => setTournaments([]));
    api.account().then(setAccount, () => setAccount(null));
  }, []);

  const canCreate = canCreateTournament(account);

  return (
    <MenuPage title={t("picker.title")} account={account} wide={false}>
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
      {creating && (
        <TournamentCreateDialog
          onClose={() => setCreating(false)}
          onDone={(tournament) => {
            setCreating(false);
            navigate(consolePath(tournament.slug, "setup"));
          }}
        />
      )}
    </MenuPage>
  );
}
