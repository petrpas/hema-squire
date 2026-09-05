import { useState } from "react";
import { useTranslation } from "react-i18next";

import {
  TOURNAMENT_FEATURES,
  type RegistrationsKeptBy,
  type TournamentDetail,
  type TournamentFlags,
  api,
} from "./api";
import HelpHint from "./HelpHint";

/** What each flag is called in the copy — the short key, so
 *  `setup.settings.feature.<name>` and the rest line up. Payments is here
 *  because the warnings still name it, not because it is one of the three. */
export const FEATURE_NAMES = {
  feature_schedule: "schedule",
  feature_payments: "payments",
  feature_teams: "teams",
  feature_extras: "extras",
} as const;

/** How much of each feature the tournament actually uses, derived from the
 *  payload Setup already holds rather than fetched: the surface opens
 *  instantly and stays right as the organizer's unsaved drafts change.
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

function inUse(usage: FeatureUsage, feature: keyof TournamentFlags): boolean {
  if (feature === "feature_payments") return usage.payments.length > 0;
  return usage[FEATURE_NAMES[feature] as "schedule" | "teams" | "extras"] > 0;
}

/** The tournament's whole configuration on one surface, with no modal shell of
 *  its own: used standalone by {@link TournamentSettingsDialog} below and
 *  embedded into the creation dialog's own shell, so creating a tournament
 *  never pops a second window over the first.
 *
 *  Three tiers, in the order the spec fixes (`setup-navigation`): the mode,
 *  the payments setting, then what the tournament includes. The first two are
 *  decisions about what Squire *does*; the third only about what Setup shows,
 *  and it carries no collective name — a tournament with none of the three
 *  ticked is a tournament with none of them ticked, and naming that condition
 *  is what this surface exists to stop doing. */
export function TournamentSettingsFields({
  detail,
  onApplied,
  onClose,
  onConfirm,
}: {
  detail: TournamentDetail;
  /** The tournament as it stands after the settings were written, so the
   *  caller can refresh the tab bar and the sections around it without a
   *  reload. */
  onApplied: (updated: TournamentDetail) => void;
  onClose: () => void;
  /** Present when the tournament does not exist yet: the surface reports what
   *  was chosen instead of writing it, and the caller creates the tournament
   *  with it. There is nothing to confirm in that case — the warnings count
   *  what a change would hide, and a tournament that does not exist holds
   *  nothing and has taken no registrations. */
  onConfirm?: (chosen: { mode: RegistrationsKeptBy; flags: TournamentFlags }) => Promise<void>;
}) {
  const { t } = useTranslation();
  const usage = featuresInUse(detail);

  const [mode, setMode] = useState<RegistrationsKeptBy>(detail.registrations_kept_by);
  const [flags, setFlags] = useState<TournamentFlags>({
    feature_schedule: detail.feature_schedule,
    feature_payments: detail.feature_payments,
    feature_teams: detail.feature_teams,
    feature_extras: detail.feature_extras,
  });
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const modeChanged = mode !== detail.registrations_kept_by;
  // What the payments setting *does* depends on the mode above it, so the copy
  // does too. In automatic mode, payments on is the whole machinery: variable
  // symbols, instructions with a QR code, a window, reminders, expiry and
  // reconciliation. In manual mode the scheduler never sees the tournament and
  // the roster arrived by import, so all that is already suspended — what
  // payments on then adds is reconciliation and nothing else. One line true of
  // both would have to be vague about the only thing the organizer wants to
  // know (spec payments, tournament-mode).
  const modeKey = mode === "organizer" ? "manual" : "automatic";
  const held = detail.in_app_registrations ?? 0;
  // Turning a flag on is never warned — there is nothing to lose.
  const losing = (["feature_payments", ...TOURNAMENT_FEATURES] as const).filter(
    (flag) => detail[flag] && !flags[flag] && inUse(usage, flag),
  );

  async function apply() {
    setBusy(true);
    setError(null);
    try {
      if (onConfirm) {
        await onConfirm({ mode, flags });
        return;
      }
      // The mode first, deliberately: two writes stand behind one confirm, and
      // a failure on the second should leave the more consequential choice
      // recorded rather than the less.
      let updated = detail;
      if (modeChanged) updated = await api.setRegistrationsKeptBy(detail.slug, mode);
      updated = await api.setTournamentFlags(detail.slug, flags);
      onApplied(updated);
    } catch {
      setError(modeChanged ? t("setup.settings.failedAfterMode") : t("setup.settings.failed"));
      setConfirming(false);
    } finally {
      setBusy(false);
    }
  }

  function submit() {
    if (!onConfirm && (modeChanged || losing.length > 0) && !confirming) {
      setConfirming(true);
      return;
    }
    void apply();
  }

  return (
    <>
      {confirming ? (
        <>
          {modeChanged && (
            <>
              <p>
                {mode === "organizer"
                  ? t("setup.settings.mode.confirmToManual")
                  : t("setup.settings.mode.confirmToAutomatic")}
              </p>
              {mode === "organizer" && held > 0 && (
                <p className="rail-hint">
                  {t("setup.settings.mode.alreadyHeld", { count: held })}
                </p>
              )}
            </>
          )}
          {losing.length > 0 && (
            <>
              <p>{t("setup.settings.confirmIntro")}</p>
              <ul className="detail-list">
                {losing.map((flag) => (
                  <li key={flag}>
                    {flag === "feature_payments"
                      ? t("setup.settings.hiding.payments", {
                          settings: usage.payments
                            .map((key) => t(`setup.settings.setting.${key}`))
                            .join(", "),
                        })
                      : t(`setup.settings.hiding.${FEATURE_NAMES[flag]}`, {
                          count: usage[
                            FEATURE_NAMES[flag] as "schedule" | "teams" | "extras"
                          ],
                        })}
                  </li>
                ))}
              </ul>
              {/* the two consequences are different in kind and are stated
                  apart: the three inclusions hide settings the organizer is
                  finished with, payments stops Squire asking for money at all */}
              {losing.some((flag) => flag !== "feature_payments") && (
                <p className="rail-hint">{t("setup.settings.stillSold")}</p>
              )}
              {losing.includes("feature_payments") && (
                <p className="rail-hint">{t("setup.settings.paymentsConsequence")}</p>
              )}
            </>
          )}
          <p className="rail-hint">{t("setup.settings.nothingIsWritten")}</p>
        </>
      ) : (
        <>
          {/* Tier 1 — the mode. First because it is the most consequential
              choice on the surface: it decides whether Squire owns the roster
              at all (spec tournament-mode). */}
          <div className="settings-tier">
            <h3>{t("setup.settings.mode.title")}</h3>
            <div className="mode-options">
              {(["squire", "organizer"] as const).map((value) => (
                <div className="mode-option" key={value}>
                  <label className="qualification-option">
                    <input
                      type="radio"
                      name="tournament-mode"
                      checked={mode === value}
                      onChange={() => setMode(value)}
                    />
                    {t(`setup.settings.mode.${value}`)}
                    <HelpHint text={t(`setup.settings.mode.hint.${value}`)} />
                  </label>
                  <p className="rail-hint">{t(`setup.settings.mode.consequence.${value}`)}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Tier 2 — payments. Beside the mode rather than among the three
              below: it suspends machinery instead of hiding controls, so it
              is offered the way the mode is — two named answers, each stated
              by what it gives the organizer rather than by what it withholds.
              A checkbox would have made one of the two answers the absence of
              the other, which is the shape this surface stopped using. */}
          <div className="settings-tier">
            <h3>{t("setup.settings.payments.title")}</h3>
            <div className="mode-options">
              {([true, false] as const).map((value) => (
                <div className="mode-option" key={String(value)}>
                  <label className="qualification-option">
                    <input
                      type="radio"
                      name="tournament-payments"
                      checked={flags.feature_payments === value}
                      onChange={() => setFlags({ ...flags, feature_payments: value })}
                    />
                    {t(
                      `setup.settings.payments.label.${modeKey}.${value ? "squire" : "self"}`,
                    )}
                    <HelpHint
                      text={t(
                        `setup.settings.payments.hint.${modeKey}.${value ? "squire" : "self"}`,
                      )}
                    />
                  </label>
                  <p className="rail-hint">
                    {t(
                      `setup.settings.payments.consequence.${modeKey}.${
                        value ? "squire" : "self"
                      }`,
                    )}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Tier 3 — what the tournament includes. No collective name and no
              count: these change which controls Setup offers and nothing a
              fencer experiences (spec tournament-features). */}
          <div className="settings-tier">
            <h3>{t("setup.settings.includes.title")}</h3>
            <div className="mode-features">
              {TOURNAMENT_FEATURES.map((feature) => (
                <label className="qualification-option" key={feature}>
                  <input
                    type="checkbox"
                    checked={flags[feature]}
                    onChange={(event) =>
                      setFlags({ ...flags, [feature]: event.target.checked })
                    }
                  />
                  {t(`setup.settings.feature.${FEATURE_NAMES[feature]}`)}
                  <HelpHint text={t(`setup.settings.hint.${FEATURE_NAMES[feature]}`)} />
                </label>
              ))}
            </div>
          </div>
        </>
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
          {confirming ? t("setup.settings.confirm") : t("setup.settings.apply")}
        </button>
      </div>
    </>
  );
}

/** Standalone settings dialog, opened from Setup's `OTHER` tab once a
 *  tournament already exists. */
export default function TournamentSettingsDialog({
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
      <div className="modal modal-wide" onClick={(event) => event.stopPropagation()}>
        <h2>{t("setup.settings.title")}</h2>
        <TournamentSettingsFields detail={detail} onApplied={onApplied} onClose={onClose} />
      </div>
    </div>
  );
}
