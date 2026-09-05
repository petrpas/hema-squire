import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { TournamentDetail } from "../api";
import RegistrationsKeptByDialog from "../RegistrationsKeptBy";

/** Who keeps the tournament's registrations, stated in words, with the control
 *  that reopens the choice.
 *
 *  Sits beside `ModeSection` on `OTHER` rather than inside it: it is a
 *  different axis, and the mode section names the four features alone (design
 *  add-registrations-kept-by D1, D5). Carries no save control and registers no
 *  saver, like the rest of `OTHER`. */
export function RegistrationsKeptBySection({
  detail,
  onApplied,
}: {
  detail: TournamentDetail;
  /** Refetches the tournament so the sections around this one follow, without
   *  leaving Setup. */
  onApplied: () => void;
}) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);

  return (
    <section className="rail-card">
      <h2>{t("setup.keptBy.section.title")}</h2>
      <p>{t(`setup.keptBy.section.${detail.registrations_kept_by}`)}</p>
      <p className="rail-hint">
        {t(`setup.keptBy.consequence.${detail.registrations_kept_by}`)}
      </p>
      <button type="button" className="secondary" onClick={() => setOpen(true)}>
        {t("setup.keptBy.section.change")}
      </button>
      {open && (
        <RegistrationsKeptByDialog
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
