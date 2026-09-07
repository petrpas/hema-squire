import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";
import AccountMenu from "./AccountMenu";
import {
  type Account,
  ApiError,
  api,
  type RegistrationsKeptBy,
  type Tournament,
  type TournamentDetail,
  type TournamentFlags,
} from "./api";
import FieldError, { invalidProps } from "./FieldError";
import { useAuth } from "./RequireAuth";
import { consolePath } from "./routes";
import { TournamentSettingsFields } from "./TournamentSettingsDialog";
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

/** The tournament as it would be created: automatic, and every flag off —
 *  which is what `POST /tournaments` actually makes, so the panel opens on the
 *  truth rather than on a preference. The settings panel needs something to open on
 *  and to compute its warnings against, and before the tournament exists this
 *  is the honest answer — it holds no discipline, no extra item and no
 *  registration, so nothing can be warned about. */
const DRAFT_SETTINGS = {
  registrations_kept_by: "squire",
  in_app_registrations: 0,
  feature_schedule: false,
  feature_payments: false,
  feature_teams: false,
  feature_extras: false,
  payment_mode: "immediate",
  bank_account: null,
  deposit_amount: null,
  disciplines: [],
  extra_items: [],
} as unknown as TournamentDetail;

const MODE_FLAG_KEYS = [
  "feature_schedule",
  "feature_payments",
  "feature_teams",
  "feature_extras",
] as const;

function deriveSlug(name: string, dateValue: string): string {
  const year = dateValue ? new Date(dateValue).getFullYear() : new Date().getFullYear();
  const base = slugify(name);
  if (!base) return "";
  return YEAR_TOKEN.test(base) ? base : `${base}-${year}`;
}

// Creating a tournament and choosing its settings used to be two modals popped
// one after the other; they are one window whose content swaps, so the
// organizer never sees a second window appear (openspec/settings_modes.md).
//
// **Nothing is created until the settings step is confirmed.** The tournament
// used to be persisted before that step was shown, so that dismissing it could
// not lose the record; the cost was a tournament brought into existence by an
// act the organizer then backed out of. Cancelling now returns to the first
// panel with every field as it was typed, and no tournament has been made. The
// request that creates it carries the settings with it, so there is no moment
// in between where one exists without them.
function TournamentCreateDialog({
  onDone,
  onClose,
}: {
  onDone: (tournament: TournamentDetail) => void;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  // The second panel is reached by naming the tournament, not by creating it.
  const [naming, setNaming] = useState(false);
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

  function submit(event: React.FormEvent) {
    event.preventDefault();
    if (validation.validateAll([displayNameCheck, slugCheck]) > 0) return;
    setError(null);
    setNaming(true);
  }

  /** Create the tournament and apply what the settings panel was told, then
   *  hand it over. A failure returns to the naming panel with the input intact
   *  and the reason stated: a slug is only known to be taken when the server
   *  says so, and that answer now arrives after the second panel rather than
   *  before it. */
  async function create(chosen: {
    mode: RegistrationsKeptBy;
    flags: TournamentFlags;
  }): Promise<void> {
    setBusy(true);
    setError(null);
    try {
      let tournament = await api.createTournament({
        slug,
        display_name: displayName,
        date,
      });
      if (chosen.mode !== "squire") {
        tournament = await api.setRegistrationsKeptBy(slug, chosen.mode);
      }
      if (MODE_FLAG_KEYS.some((flag) => chosen.flags[flag])) {
        tournament = await api.setTournamentFlags(slug, chosen.flags);
      }
      onDone(tournament);
    } catch (err) {
      setNaming(false);
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
    <div className="modal-backdrop" onClick={naming ? () => setNaming(false) : onClose}>
      {naming ? (
        <div className="modal modal-wide" onClick={(event) => event.stopPropagation()}>
          <h2>{t("setup.settings.title")}</h2>
          <TournamentSettingsFields
            detail={DRAFT_SETTINGS}
            onApplied={onDone}
            /* cancelling makes no tournament and loses no typing: back to the
               naming panel, which still holds every field */
            onClose={() => setNaming(false)}
            onConfirm={create}
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
