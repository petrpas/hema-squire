import { useState } from "react";
import { useTranslation } from "react-i18next";

import { MODE_FEATURES, type TournamentDetail, isEasyMode } from "../api";
import TournamentModeDialog, { FEATURE_NAMES } from "../TournamentModeDialog";

/** The tournament's mode, stated in words, with the control that reopens the
 *  mode dialog. The statement is computed from the four features rather than
 *  echoing a stored label, so the name and the behaviour can never drift
 *  (design tournament-modes D2).
 *
 *  Carries no save control and registers no saver: like the rest of `OTHER`,
 *  its action is its own (spec: setup-navigation). It is shown in every mode,
 *  because it is the way back. */
export function ModeSection({
  detail,
  onApplied,
}: {
  detail: TournamentDetail;
  /** Refetches the tournament so the tab bar and the sections around this one
   *  follow the new mode, without leaving Setup. */
  onApplied: () => void;
}) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);

  const enabled = MODE_FEATURES.filter((feature) => detail[feature]).map((feature) =>
    t(`setup.mode.feature.${FEATURE_NAMES[feature]}`).toLocaleLowerCase(),
  );

  return (
    <section className="rail-card">
      <h2>{t("setup.mode.section.title")}</h2>
      <p>
        {isEasyMode(detail)
          ? t("setup.mode.section.easy")
          : t("setup.mode.section.advanced", { features: enabled.join(", ") })}
      </p>
      <button type="button" className="secondary" onClick={() => setOpen(true)}>
        {t("setup.mode.section.change")}
      </button>
      {open && (
        <TournamentModeDialog
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
