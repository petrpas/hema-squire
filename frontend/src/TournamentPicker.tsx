import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import type { Phase } from "./Console";
import { ApiError, type Account, type Plea, type Tournament, api, setToken } from "./api";

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

function deriveSlug(name: string, dateValue: string): string {
  const year = dateValue ? new Date(dateValue).getFullYear() : new Date().getFullYear();
  const base = slugify(name);
  return base ? `${base}-${year}` : "";
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
        <label>
          {t("picker.displayName")}
          <input
            value={displayName}
            onChange={(event) => setDisplayName(event.target.value)}
            required
            autoFocus
          />
        </label>
        <label>
          {t("picker.date")}
          <input
            type="date"
            value={date}
            onChange={(event) => setDate(event.target.value)}
            required
          />
        </label>
        <label>
          {t("picker.slug")}
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
        {error && <p className="login-error">{error}</p>}
        <div className="modal-actions">
          <button type="button" className="secondary" onClick={onClose}>
            {t("common.cancel")}
          </button>
          <button type="submit" disabled={busy || !slug}>
            {t("picker.create")}
          </button>
        </div>
      </form>
    </div>
  );
}

function PleaSection({ plea, onPleaChange }: { plea: Plea; onPleaChange: (plea: Plea) => void }) {
  const { t } = useTranslation();
  const [showForm, setShowForm] = useState(false);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit() {
    setBusy(true);
    try {
      const result = await api.submitPlea(message.trim() === "" ? null : message.trim());
      onPleaChange(result);
      setShowForm(false);
      setMessage("");
    } finally {
      setBusy(false);
    }
  }

  if (plea.state === "pending") {
    return <p className="plea-status">{t("picker.pleaPending")}</p>;
  }

  if (showForm) {
    return (
      <div className="plea-form">
        <textarea
          value={message}
          placeholder={t("picker.pleaMessagePlaceholder")}
          onChange={(event) => setMessage(event.target.value)}
        />
        <div className="modal-actions">
          <button type="button" className="secondary" onClick={() => setShowForm(false)}>
            {t("common.cancel")}
          </button>
          <button type="button" disabled={busy} onClick={() => void submit()}>
            {t("picker.pleaSubmit")}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div>
      {plea.state === "denied" && <p className="plea-status">{t("picker.pleaDenied")}</p>}
      <button className="secondary" onClick={() => setShowForm(true)}>
        {t("picker.requestOrganizer")}
      </button>
    </div>
  );
}

export default function TournamentPicker({
  onPick,
  onLogout,
  onAdmin,
}: {
  onPick: (tournament: Tournament, initialPhase?: Phase) => void;
  onLogout: () => void;
  onAdmin: () => void;
}) {
  const { t } = useTranslation();
  const [tournaments, setTournaments] = useState<Tournament[] | null>(null);
  const [creating, setCreating] = useState(false);
  const [account, setAccount] = useState<Account | null>(null);
  const [plea, setPlea] = useState<Plea | null>(null);

  useEffect(() => {
    api.tournaments().then(setTournaments, () => setTournaments([]));
    api.account().then(setAccount, () => setAccount(null));
  }, []);

  const canCreate = account !== null && (account.role !== "fencer" || account.is_deployment_owner);
  const isAdmin = account !== null && (account.role === "admin" || account.is_deployment_owner);

  useEffect(() => {
    if (account !== null && !canCreate) {
      api.myPlea().then(setPlea, () => setPlea(null));
    }
  }, [account, canCreate]);

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
        {canCreate ? (
          <button className="secondary" onClick={() => setCreating(true)}>
            {t("picker.newTournament")}
          </button>
        ) : (
          plea && <PleaSection plea={plea} onPleaChange={setPlea} />
        )}
        {isAdmin && (
          <button className="secondary" onClick={onAdmin}>
            {t("picker.adminPanel")}
          </button>
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
