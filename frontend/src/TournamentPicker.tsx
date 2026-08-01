import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import AccountMenu from "./AccountMenu";
import type { Phase } from "./Console";
import { ApiError, type Account, type Tournament, api } from "./api";

// slug = slugified display name + event year, editable before submission
// (design D7); the server remains the validator on collision (409).
function slugify(text: string): string {
  return text
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "") // strip combining diacritics after NFKD
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

const YEAR_TOKEN = /(^|-)(19|20)\d{2}(-|$)/;

function deriveSlug(name: string, dateValue: string): string {
  const year = dateValue ? new Date(dateValue).getFullYear() : new Date().getFullYear();
  const base = slugify(name);
  if (!base) return "";
  return YEAR_TOKEN.test(base) ? base : `${base}-${year}`;
}

function NewTournamentDialog({
  onCreated,
  onClose,
}: {
  onCreated: (tournament: Tournament) => void;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const [displayName, setDisplayName] = useState("");
  const [date, setDate] = useState("");
  const [slug, setSlug] = useState("");
  const [slugEdited, setSlugEdited] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!slugEdited) setSlug(deriveSlug(displayName, date));
  }, [displayName, date, slugEdited]);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const tournament = await api.createTournament({
        slug,
        display_name: displayName,
        date,
      });
      onCreated(tournament);
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 409
          ? t("picker.slugTaken")
          : t("picker.createFailed"),
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <form className="modal" onClick={(event) => event.stopPropagation()} onSubmit={submit}>
        <h2>{t("picker.newTournament")}</h2>
        <p className="tiskopis-number">{t("picker.formNumber")}</p>
        <div className="form-fields">
          <label className="form-field">
            <span>{t("picker.displayName")}</span>
            <input
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              required
              autoFocus
            />
          </label>
          <label className="form-field">
            <span>{t("picker.date")}</span>
            <input
              type="date"
              value={date}
              onChange={(event) => setDate(event.target.value)}
              required
            />
          </label>
          <label className="form-field">
            <span>{t("picker.slug")}</span>
            <input
              value={slug}
              onChange={(event) => {
                setSlug(event.target.value);
                setSlugEdited(true);
              }}
              pattern="[a-z0-9][a-z0-9-]{1,98}"
              required
            />
          </label>
        </div>
        {error && <p className="login-error">{error}</p>}
        <div className="modal-actions">
          <button type="button" className="secondary" onClick={onClose}>
            {t("common.cancel")}
          </button>
          <button type="submit" className="btn-primary" disabled={busy || !slug}>
            {t("picker.create")}
          </button>
        </div>
      </form>
    </div>
  );
}

export default function TournamentPicker({
  onPick,
  onLogout,
  onAdmin,
  onProfile,
  onFencer,
}: {
  onPick: (tournament: Tournament, initialPhase?: Phase) => void;
  onLogout: () => void;
  onAdmin: () => void;
  onProfile: () => void;
  onFencer: () => void;
}) {
  const { t } = useTranslation();
  const [tournaments, setTournaments] = useState<Tournament[] | null>(null);
  const [creating, setCreating] = useState(false);
  const [account, setAccount] = useState<Account | null>(null);

  useEffect(() => {
    api.tournaments().then(setTournaments, () => setTournaments([]));
    api.account().then(setAccount, () => setAccount(null));
  }, []);

  const canCreate = account !== null && (account.role !== "fencer" || account.is_deployment_owner);

  return (
    <div className="login-page">
      <div className="page-menu-corner">
        <AccountMenu
          account={account}
          onProfile={onProfile}
          onAdmin={onAdmin}
          onFencer={onFencer}
          onOrganizer={() => {}}
          onLogout={onLogout}
        />
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
                <button onClick={() => onPick(tournament)}>
                  <strong>{tournament.display_name}</strong>
                  <span>{new Date(tournament.date).toLocaleDateString("cs")}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
        {canCreate && (
          <button className="secondary" onClick={() => setCreating(true)}>
            {t("picker.newTournament")}
          </button>
        )}
      </div>
      {creating && (
        <NewTournamentDialog
          onClose={() => setCreating(false)}
          onCreated={(tournament) => {
            setCreating(false);
            onPick(tournament, "setup");
          }}
        />
      )}
    </div>
  );
}
