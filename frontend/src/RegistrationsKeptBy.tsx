import { useState } from "react";
import { useTranslation } from "react-i18next";

import {
  type RegistrationsKeptBy,
  type TournamentDetail,
  api,
} from "./api";
import HelpHint from "./HelpHint";

/** The choice itself, with no modal shell of its own — used standalone by
 *  {@link RegistrationsKeptByDialog} and embedded into the tournament creation
 *  dialog's own shell, exactly as `TournamentModeFields` is.
 *
 *  Deliberately a component of its own rather than a fifth checkbox inside the
 *  mode fields. The mode dialog's whole explanation is that turning a feature
 *  off hides settings without changing what a fencer experiences; this closes
 *  the registration form and stops Squire writing to anyone, so putting it
 *  there would make the dialog's own copy untrue (design
 *  add-registrations-kept-by D5). */
export function RegistrationsKeptByFields({
  detail,
  onApplied,
  onClose,
}: {
  detail: TournamentDetail;
  onApplied: (updated: TournamentDetail) => void;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const [chosen, setChosen] = useState<RegistrationsKeptBy>(detail.registrations_kept_by);
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const changing = chosen !== detail.registrations_kept_by;
  // Both directions are confirmed, because both have consequences: one closes
  // registration and stops the clocks, the other opens registration and puts a
  // roster under clocks it has never been under (design D6).
  const held = detail.in_app_registrations ?? 0;

  async function apply() {
    setBusy(true);
    setError(null);
    try {
      onApplied(await api.setRegistrationsKeptBy(detail.slug, chosen));
    } catch {
      setError(t("setup.keptBy.failed"));
      setConfirming(false);
    } finally {
      setBusy(false);
    }
  }

  function submit() {
    if (!changing) {
      onClose();
      return;
    }
    if (!confirming) {
      setConfirming(true);
      return;
    }
    void apply();
  }

  return (
    <>
      {confirming ? (
        <>
          <p>
            {chosen === "organizer"
              ? t("setup.keptBy.confirmToOrganizer")
              : t("setup.keptBy.confirmToSquire")}
          </p>
          {chosen === "organizer" && held > 0 && (
            <p className="rail-hint">{t("setup.keptBy.alreadyHeld", { count: held })}</p>
          )}
          <p className="rail-hint">{t("setup.keptBy.nothingIsWritten")}</p>
        </>
      ) : (
        <div className="mode-options">
          {(["squire", "organizer"] as const).map((value) => (
            <div className="mode-option" key={value}>
              <label className="qualification-option">
                <input
                  type="radio"
                  name="registrations-kept-by"
                  checked={chosen === value}
                  onChange={() => setChosen(value)}
                />
                {t(`setup.keptBy.option.${value}`)}
                <HelpHint text={t(`setup.keptBy.hint.${value}`)} />
              </label>
              <p className="rail-hint">{t(`setup.keptBy.consequence.${value}`)}</p>
            </div>
          ))}
        </div>
      )}
      {error && <p className="login-error">{error}</p>}
      <div className="modal-actions">
        <button
          type="button"
          className="secondary"
          onClick={() => (confirming ? setConfirming(false) : onClose())}
        >
          {confirming ? t("common.back") : t("common.cancel")}
        </button>
        <button type="button" className="btn-primary" onClick={submit} disabled={busy}>
          {confirming ? t("setup.keptBy.confirm") : t("setup.keptBy.apply")}
        </button>
      </div>
    </>
  );
}

/** Standalone dialog, opened from Setup's `OTHER` tab once a tournament
 *  already exists. */
export default function RegistrationsKeptByDialog({
  detail,
  onApplied,
  onClose,
}: {
  detail: TournamentDetail;
  onApplied: (updated: TournamentDetail) => void;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(event) => event.stopPropagation()}>
        <h2>{t("setup.keptBy.title")}</h2>
        <RegistrationsKeptByFields detail={detail} onApplied={onApplied} onClose={onClose} />
      </div>
    </div>
  );
}
