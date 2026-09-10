import { useTranslation } from "react-i18next";

import type { IngestAndMatch } from "../api";

/** How many rows of the statement were money leaving the account.
 *
 *  Stated only when there were any. An organizer who can see fifteen rows in
 *  the file and reads a report of twelve is owed the number that closes the
 *  gap; one that reads "0 výdajů" on every ordinary import is noise about a
 *  thing that did not happen.
 *
 *  Not an error and not a warning: an outgoing transfer in a statement is
 *  entirely normal, and nothing about the import went wrong.
 */
export default function DroppedNote({ outcome }: { outcome: IngestAndMatch }) {
  const { t } = useTranslation();
  if (outcome.dropped <= 0) return null;
  return <p className="rail-hint">{t("payments.intake.dropped", { count: outcome.dropped })}</p>;
}
