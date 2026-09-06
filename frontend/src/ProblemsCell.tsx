import { useTranslation } from "react-i18next";

import NoteMarker from "./NoteMarker";

/** What the problems column states about a row.
 *
 *  The parser's report, and — since a row may now carry a problem that outlives
 *  parsing — whatever else about the row is wrong. A borrowed item the
 *  tournament lends nothing by is the first of those: it is billed nothing, so
 *  the total is short by exactly the amount nobody can see (owner decision,
 *  2026-09-06). The rentals cell marks the name for whoever is reading that
 *  column; this marker states it for whoever is reading the row, which is what
 *  an organizer looking for what is wrong with a roster actually does.
 *
 *  The row's own problem comes first and the parser's after it: the parser's
 *  is about the file, and the file is the older news.
 */
export default function ProblemsCell({
  text,
  unpriced,
}: {
  text: string | null | undefined;
  unpriced: string[];
}) {
  const { t } = useTranslation();
  const parts: string[] = [];
  if (unpriced.length > 0) {
    parts.push(t("console.unpriced_rental_problem", { items: unpriced.join(", ") }));
  }
  if (typeof text === "string" && text.trim() !== "") parts.push(text.trim());
  // nothing at all on a row that carries none: not a dash, not an empty marker
  if (parts.length === 0) return null;
  return <NoteMarker kind="problem" text={parts.join(" | ")} />;
}
