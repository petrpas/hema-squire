import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import RatingsRefresh from "../../export/RatingsRefresh";
import { ratingsState } from "../../export/ratingsState";
import * as routes from "../../routes";
import type { DataSheet } from "../floorApi";

/** Data's operations panel: the chosen discipline's ratings refresh with its
 *  state line, taken over from the office's Export card, and the addition of
 *  an entrant or a team — or, once the
 *  discipline's check-in has closed, the one line saying the sheet is the
 *  snapshot — and the Import link of an organizer-kept tournament (spec
 *  floor-data, spec floor-console). */
export default function DataPanel({
  slug,
  sheet,
  keptByOrganizer,
  refreshing,
  message,
  onRefresh,
  add,
}: {
  slug: string;
  sheet: DataSheet | null;
  keptByOrganizer: boolean;
  refreshing: boolean;
  message: string | null;
  onRefresh: () => void;
  /** "Přidat účastníka" or "Přidat tým": a tab-level act, so it stands in
   *  the panel while check-in is open (spec floor-console). */
  add?: ReactNode;
}) {
  const { t, i18n } = useTranslation();
  const state =
    sheet === null ? null : ratingsState(t, i18n.language, sheet.fetched_at, sheet.missing);
  return (
    <>
      {sheet !== null && (
        <section className="rail-card">
          <h2>{sheet.discipline.name}</h2>
          {sheet.closed_at !== null ? (
            <p className="rail-hint">
              {t("floor.data.closed", { moment: moment(sheet.closed_at, i18n.language) })}
            </p>
          ) : (
            <>
              {add}
              <div className="export-actions">
                <RatingsRefresh onRefresh={onRefresh} refreshing={refreshing} />
              </div>
              {state && <p className="rail-hint">{state}</p>}
              {message && <p className="rail-hint">{message}</p>}
            </>
          )}
        </section>
      )}
      {keptByOrganizer && (
        <section className="rail-card">
          <p>{t("floor.data.fromImport")}</p>
          <Link to={routes.consolePath(slug, "import")}>{t("floor.data.toImport")}</Link>
        </section>
      )}
    </>
  );
}

function moment(value: string, language: string): string {
  const at = new Date(value);
  if (Number.isNaN(at.getTime())) return value;
  const clock = at.toLocaleTimeString(language, { hour: "2-digit", minute: "2-digit" });
  return `${at.toLocaleDateString(language)} ${clock}`;
}
