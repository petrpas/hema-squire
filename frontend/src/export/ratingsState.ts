import type { TFunction } from "i18next";

/** What a discipline tab's card states beside the ratings refresh (spec
 *  export-tables, A discipline tab states whose ratings are not fetched): when
 *  the ratings were last fetched, or that they never were, and how many of the
 *  tab's fighters bound to a profile have no fetched rating yet. Without it an
 *  empty rating cell reads as a fault, when it means the refresh has not been
 *  run since that fighter was bound. Null where there is nothing to say: no
 *  snapshot and nobody bound. */
export function ratingsState(
  t: TFunction,
  language: string,
  fetchedAt: string | null,
  missing: number,
): string | null {
  const parts: string[] = [];
  if (fetchedAt === null) {
    if (missing === 0) return null;
    parts.push(t("export.ratingsState.never"));
  } else {
    parts.push(t("export.ratingsState.fetched", { moment: moment(fetchedAt, language) }));
  }
  if (missing > 0) parts.push(t("export.ratingsState.missing", { count: missing }));
  return parts.join(" · ");
}

function moment(value: string, language: string): string {
  const at = new Date(value);
  if (Number.isNaN(at.getTime())) return value;
  const clock = at.toLocaleTimeString(language, { hour: "2-digit", minute: "2-digit" });
  return `${at.toLocaleDateString(language)} ${clock}`;
}
