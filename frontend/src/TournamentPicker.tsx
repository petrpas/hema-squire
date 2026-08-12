import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import AccountMenu from "./AccountMenu";
import { useAuth } from "./RequireAuth";
import { consolePath } from "./routes";
import { ApiError, type Account, type Tournament, type TournamentDetail, api } from "./api";
import FieldError, { invalidProps } from "./FieldError";
import { TournamentModeFields } from "./TournamentModeDialog";
import { useFieldValidation } from "./useFieldValidation";
import { apiErrors, checkString } from "./validation";

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

// Creating a tournament and choosing its mode used to be two modals popped
// one after the other; they are now one window whose content swaps once the
// tournament exists, so the organizer never sees a second window appear
// (openspec/settings_modes.md). The tournament is still created (a real,
// persisted record) before the mode step is shown, so a failure or dismissal
// of the mode step can never lose it (design tournament-modes D11) — dismissal
// just leaves it in the easy mode it was created in, same as confirming does.
function TournamentCreateDialog({
  onDone,
  onClose,
}: {
  onDone: (tournament: TournamentDetail) => void;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const [created, setCreated] = useState<TournamentDetail | null>(null);
  const [displayName, setDisplayName] = useState("");
  const [date, setDate] = useState("");
  const [slug, setSlug] = useState("");
  const [slugEdited, setSlugEdited] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const validation = useFieldValidation();

  useEffect(() => {
    if (!slugEdited) setSlug(deriveSlug(displayName, date));
  }, [displayName, date, slugEdited]);

  function displayNameCheck() {
    return checkString("display_name", "TournamentCreate.display_name", displayName, {
      required: true,
    });
  }
  function slugCheck() {
    return checkString("slug", "TournamentCreate.slug", slug, { required: true });
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (validation.validateAll([displayNameCheck, slugCheck]) > 0) return;
    setBusy(true);
    setError(null);
    try {
      setCreated(
        await api.createTournament({
          slug,
          display_name: displayName,
          date,
        }),
      );
    } catch (err) {
      const fieldErrors = apiErrors(err);
      if (fieldErrors.length > 0) {
        validation.applyApiErrors(fieldErrors);
      } else {
        setError(
          err instanceof ApiError && err.status === 409
            ? t("picker.slugTaken")
            : t("picker.createFailed"),
        );
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={created ? () => onDone(created) : onClose}>
      {created ? (
        <div className="modal" onClick={(event) => event.stopPropagation()}>
          <h2>{t("setup.mode.title")}</h2>
          <TournamentModeFields
            detail={created}
            onApplied={onDone}
            onClose={() => onDone(created)}
          />
        </div>
      ) : (
        <form className="modal" onClick={(event) => event.stopPropagation()} onSubmit={submit}>
          <h2>{t("picker.newTournament")}</h2>
          <p className="tiskopis-number">{t("picker.formNumber")}</p>
          <div className="form-fields">
            <label className="form-field">
              <span>{t("picker.displayName")}</span>
              <input
                value={displayName}
                onChange={(event) => {
                  setDisplayName(event.target.value);
                  validation.clearIfValid("display_name", displayNameCheck);
                }}
                onBlur={() => validation.touch("display_name", displayNameCheck)}
                required
                autoFocus
                {...invalidProps("display_name", validation.errors.display_name)}
              />
              <FieldError field="display_name" error={validation.errors.display_name} />
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
                  validation.clearIfValid("slug", slugCheck);
                }}
                onBlur={() => validation.touch("slug", slugCheck)}
                pattern="[a-z0-9][a-z0-9-]{1,98}"
                required
                {...invalidProps("slug", validation.errors.slug)}
              />
              <FieldError field="slug" error={validation.errors.slug} />
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
      )}
    </div>
  );
}

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

  const canCreate = account !== null && (account.role !== "fencer" || account.is_deployment_owner);

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
          <button className="secondary" onClick={() => setCreating(true)}>
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
