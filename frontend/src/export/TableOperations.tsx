import { IconCopy, IconFileTypePdf, IconFileTypePng, IconRefresh } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";

import type { RosterFormat } from "../api";
import HintedAction from "./HintedAction";

const PRINT_ICONS = { pdf: IconFileTypePdf, png: IconFileTypePng } as const;

/** The rail card acting on the open export tab: its active-only switch (on
 *  every tab but the summary), the copy, and — on a discipline — the seeding
 *  order, the PDF and PNG of its roster, and the ratings refresh.
 *
 *  The copy, the ratings refresh and the printouts stand in one row of icons,
 *  each its own hint marker, as the export card's actions do.
 *
 *  Headed by the tab's name, so the organizer sees which table a switch or a
 *  copy acts on without looking back at the band. The outcome of either action
 *  is stated here, where it was asked for.
 */
export default function TableOperations({
  title,
  active,
  seeded,
  onCopy,
  print,
  onRefreshRatings,
  refreshing,
  ratingsMessage,
  message,
}: {
  title: string;
  /** The active-only switch — offered on every tab but the summary, whose
   *  columns already split the paid from the unpaid. */
  active?: { checked: boolean; onChange: (active: boolean) => void };
  /** The discipline's seeding order by rating — offered on a discipline tab
   *  only, and independent of the active-only switch. */
  seeded?: { checked: boolean; onChange: (seeded: boolean) => void };
  onCopy: () => void;
  /** Offered on a discipline tab only: the roster typeset to a file.
   *  `printing` is the format being typeset, whose button waits, with no
   *  spinner. */
  print?: { onPrint: (format: RosterFormat) => void; printing: RosterFormat | null };
  /** Offered on a discipline tab only, where the ratings being read are. */
  onRefreshRatings?: () => void;
  refreshing: boolean;
  /** What the last ratings fetch did — stated beside the fetch, so a tab
   *  that offers none does not carry it. */
  ratingsMessage: string | null;
  message: string | null;
}) {
  const { t } = useTranslation();
  return (
    <section className="rail-card">
      <h2>{title}</h2>
      {active && (
        <label className="rail-check">
          <input
            type="checkbox"
            checked={active.checked}
            onChange={(event) => active.onChange(event.currentTarget.checked)}
          />
          <span>{t("export.activeOnly")}</span>
        </label>
      )}
      {seeded && (
        <label className="rail-check">
          <input
            type="checkbox"
            checked={seeded.checked}
            onChange={(event) => seeded.onChange(event.currentTarget.checked)}
          />
          <span>{t("export.seedByRating")}</span>
        </label>
      )}
      <div className="export-actions">
        <HintedAction hint={t("export.hints.copy")}>
          {(hintId) => (
            <button
              type="button"
              className="icon-action"
              aria-describedby={hintId}
              onClick={onCopy}
            >
              <IconCopy size={18} stroke={1.5} />
              <span className="visually-hidden">{t("export.copy")}</span>
            </button>
          )}
        </HintedAction>
        {onRefreshRatings && (
          <HintedAction hint={t("export.hints.fetchRatings")}>
            {(hintId) => (
              <button
                type="button"
                className="icon-action"
                disabled={refreshing}
                aria-describedby={hintId}
                onClick={onRefreshRatings}
              >
                <IconRefresh size={18} stroke={1.5} />
                <span className="visually-hidden">{t("export.fetchRatings")}</span>
              </button>
            )}
          </HintedAction>
        )}
        {print &&
          (["pdf", "png"] as const).map((format) => {
            const Icon = PRINT_ICONS[format];
            return (
              <HintedAction key={format} hint={t(`export.hints.${format}`)}>
                {(hintId) => (
                  <button
                    type="button"
                    className="icon-action"
                    disabled={print.printing === format}
                    aria-describedby={hintId}
                    onClick={() => print.onPrint(format)}
                  >
                    <Icon size={18} stroke={1.5} />
                    <span className="visually-hidden">{t(`export.${format}`)}</span>
                  </button>
                )}
              </HintedAction>
            );
          })}
      </div>
      {ratingsMessage && onRefreshRatings && <p className="rail-hint">{ratingsMessage}</p>}
      {message && <p className="rail-hint">{message}</p>}
    </section>
  );
}
