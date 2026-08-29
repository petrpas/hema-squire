import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { TournamentDetail } from "../api";
import ManualEntryDialog from "./ManualEntryDialog";

/** The Fencers tab's own operation: adding a fencer the tournament knows by no
 *  other route (spec etl-console, Where the two source actions live). It is
 *  offered here and on no other phase. */
export default function ManualEntryPanel({
  detail,
  slug,
  onEntered,
}: {
  detail: TournamentDetail | null;
  slug: string;
  onEntered: () => void;
}) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);

  return (
    <>
      <section className="rail-card">
        <h2>{t("manualEntry.title")}</h2>
        <p className="rail-hint">{t("manualEntry.hint")}</p>
        {/* the dialog is built from the tournament's structure, so it opens
            only once that structure has arrived */}
        <button
          className="secondary param-save"
          disabled={detail === null}
          onClick={() => setOpen(true)}
        >
          {t("manualEntry.open")}
        </button>
      </section>

      {open && detail !== null && (
        <ManualEntryDialog
          detail={detail}
          slug={slug}
          onEntered={onEntered}
          onClose={() => setOpen(false)}
        />
      )}
    </>
  );
}
