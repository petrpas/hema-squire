import { useState } from "react";
import { useTranslation } from "react-i18next";

import {
  EASY_MODE,
  MODE_FEATURES,
  type TournamentDetail,
  type TournamentMode,
  api,
  isEasyMode,
} from "./api";
import HelpHint from "./HelpHint";

/** What each feature is called in the dialog and in the warnings — the short
 *  key, so `setup.mode.feature.<name>` and the rest line up. */
export const FEATURE_NAMES = {
  feature_schedule: "schedule",
  feature_payments: "payments",
  feature_teams: "teams",
  feature_extras: "extras",
} as const;

/** How much of each feature the tournament actually uses, derived from the
 *  payload Setup already holds rather than fetched (design D10): the dialog
 *  opens instantly and stays right as the organizer's unsaved drafts change.
 *
 *  Payments is reported as the settings recorded rather than a count, because
 *  what the organizer needs to read is which of them are about to go out of
 *  sight — not how many. */
export interface FeatureUsage {
  schedule: number;
  teams: number;
  extras: number;
  payments: string[];
}

export function featuresInUse(detail: TournamentDetail): FeatureUsage {
  return {
    schedule: detail.disciplines.filter(
      (discipline) => discipline.schedule_when || discipline.schedule_where,
    ).length,
    teams: detail.disciplines.filter((discipline) => discipline.kind === "team").length,
    extras: detail.extra_items.length,
    payments: [
      detail.bank_account ? "bank_account" : null,
      detail.payment_mode !== "immediate" ? "payment_mode" : null,
      detail.deposit_amount ? "deposit_amount" : null,
    ].filter((key): key is string => key !== null),
  };
}

function inUse(usage: FeatureUsage, feature: keyof TournamentMode): boolean {
  if (feature === "feature_payments") return usage.payments.length > 0;
  return usage[FEATURE_NAMES[feature] as "schedule" | "teams" | "extras"] > 0;
}

/** The mode picker itself, with no modal shell of its own: used standalone
 *  by {@link TournamentModeDialog} below and embedded directly into the
 *  tournament creation dialog's own shell, so creating a tournament never
 *  pops a second window over the first (openspec/settings_modes.md). */
export function TournamentModeFields({
  detail,
  onApplied,
  onClose,
}: {
  detail: TournamentDetail;
  /** The tournament as it stands after the mode was written, so the caller
   *  can refresh the tab bar and the sections around it without a reload. */
  onApplied: (updated: TournamentDetail) => void;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const usage = featuresInUse(detail);
  // easy mode is preselected, which is both the stored state of a new
  // tournament and the recommendation (design D11)
  const [advanced, setAdvanced] = useState(!isEasyMode(detail));
  const [features, setFeatures] = useState<TournamentMode>({
    feature_schedule: detail.feature_schedule,
    feature_payments: detail.feature_payments,
    feature_teams: detail.feature_teams,
    feature_extras: detail.feature_extras,
  });
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Advanced with nothing ticked is easy mode, and is named as such: there is
  // no stored state where the label and the behaviour could drift (D2).
  const chosen: TournamentMode = advanced ? features : EASY_MODE;
  const resolved: TournamentMode = isEasyMode(chosen) ? EASY_MODE : chosen;

  // Turning a feature on is never warned — there is nothing to lose.
  const losing = MODE_FEATURES.filter(
    (feature) => detail[feature] && !resolved[feature] && inUse(usage, feature),
  );

  async function apply() {
    setBusy(true);
    setError(null);
    try {
      onApplied(await api.setTournamentMode(detail.slug, resolved));
    } catch {
      setError(t("setup.mode.failed"));
      setConfirming(false);
    } finally {
      setBusy(false);
    }
  }

  function submit() {
    if (losing.length > 0 && !confirming) {
      setConfirming(true);
      return;
    }
    void apply();
  }

  return (
    <>
      {confirming ? (
          <>
            <p>{t("setup.mode.confirmIntro")}</p>
            <ul className="detail-list">
              {losing.map((feature) => (
                <li key={feature}>
                  {feature === "feature_payments"
                    ? t("setup.mode.hiding.payments", {
                        settings: usage.payments
                          .map((key) => t(`setup.mode.setting.${key}`))
                          .join(", "),
                      })
                    : t(`setup.mode.hiding.${FEATURE_NAMES[feature]}`, {
                        count: usage[FEATURE_NAMES[feature] as "schedule" | "teams" | "extras"],
                      })}
                </li>
              ))}
            </ul>
            {/* the two consequences are different in kind and are stated
                apart: the three presentational features hide settings the
                organizer is finished with, payments stops Squire asking for
                money at all (design D5) */}
            {losing.some((feature) => feature !== "feature_payments") && (
              <p className="rail-hint">{t("setup.mode.stillSold")}</p>
            )}
            {losing.includes("feature_payments") && (
              <p className="rail-hint">{t("setup.mode.paymentsConsequence")}</p>
            )}
          </>
        ) : (
          <div className="mode-options">
            <div className="mode-option">
              <label className="qualification-option">
                <input
                  type="radio"
                  name="tournament-mode"
                  checked={!advanced}
                  onChange={() => setAdvanced(false)}
                />
                {t("setup.mode.easy")}
              </label>
              <p className="rail-hint">{t("setup.mode.easyHint")}</p>
            </div>
            <div className="mode-option">
              <label className="qualification-option">
                <input
                  type="radio"
                  name="tournament-mode"
                  checked={advanced}
                  onChange={() => setAdvanced(true)}
                />
                {t("setup.mode.advanced")}
              </label>
              <p className="rail-hint">{t("setup.mode.advancedHint")}</p>
              {advanced && (
                <div className="mode-features">
                  {MODE_FEATURES.map((feature) => (
                    <label className="qualification-option" key={feature}>
                      <input
                        type="checkbox"
                        checked={features[feature]}
                        onChange={(event) =>
                          setFeatures({ ...features, [feature]: event.target.checked })
                        }
                      />
                      {t(`setup.mode.feature.${FEATURE_NAMES[feature]}`)}
                      <HelpHint text={t(`setup.mode.hint.${FEATURE_NAMES[feature]}`)} />
                    </label>
                  ))}
                  {/* shown regardless of which boxes are ticked, not just when
                      none are: toggling it in and out with the selection
                      resized the modal on every click and read as flicker
                      (openspec/settings_modes.md) */}
                  <p className="rail-hint">{t("setup.mode.nothingChosen")}</p>
                </div>
              )}
            </div>
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
            {confirming ? t("setup.mode.confirm") : t("setup.mode.apply")}
          </button>
        </div>
    </>
  );
}

/** Standalone mode dialog, opened from Settings (`OTHER > TOURNAMENT SETTINGS
 *  MODE`) once a tournament already exists. */
export default function TournamentModeDialog({
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
        <h2>{t("setup.mode.title")}</h2>
        <TournamentModeFields detail={detail} onApplied={onApplied} onClose={onClose} />
      </div>
    </div>
  );
}
