import { useState } from "react";
import { useTranslation } from "react-i18next";

import { TOURNAMENT_FEATURES, type TournamentDetail } from "../api";
import TournamentSettingsDialog, { FEATURE_NAMES } from "../TournamentSettingsDialog";

/** The tournament's whole configuration, stated in words, with the one control
 *  that reopens the settings surface.
 *
 *  One section, not three and not two: `OTHER` used to carry a mode section
 *  and, beside it, a registrations section, which described one configuration
 *  in parts. The statement is computed from the stored values rather than
 *  echoing a label, and no line names a tier — a tournament including none of
 *  the three is described by that (spec setup-navigation, tournament-features).
 *
 *  Carries no save control and registers no saver: like the rest of `OTHER`,
 *  its action is its own. */
export function SettingsSection({
  detail,
  onApplied,
}: {
  detail: TournamentDetail;
  /** Refetches the tournament so the tab bar and the sections around this one
   *  follow, without leaving Setup. */
  onApplied: () => void;
}) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);

  const included = TOURNAMENT_FEATURES.filter((feature) => detail[feature]).map((feature) =>
    t(`setup.settings.feature.${FEATURE_NAMES[feature]}`).toLocaleLowerCase(),
  );

  return (
    <section className="rail-card">
      <h2>{t("setup.settings.section.title")}</h2>
      <p>{t(`setup.settings.section.mode.${detail.registrations_kept_by}`)}</p>
      {/* what payments means depends on the mode above it: in manual mode the
          lifecycle is already suspended, so payments on adds reconciliation
          and nothing else */}
      <p>
        {t(
          `setup.settings.section.payments.${
            detail.registrations_kept_by === "organizer" ? "manual" : "automatic"
          }.${detail.feature_payments ? "on" : "off"}`,
        )}
      </p>
      <p>
        {included.length > 0
          ? t("setup.settings.section.includes", { features: included.join(", ") })
          : t("setup.settings.section.includesNothing")}
      </p>
      <button type="button" className="secondary" onClick={() => setOpen(true)}>
        {t("setup.settings.section.change")}
      </button>
      {open && (
        <TournamentSettingsDialog
          detail={detail}
          onClose={() => setOpen(false)}
          onApplied={() => {
            setOpen(false);
            onApplied();
          }}
        />
      )}
    </section>
  );
}
