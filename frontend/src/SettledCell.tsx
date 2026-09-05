import { useTranslation } from "react-i18next";

import type { SheetRow } from "./api";
import PaidStamp from "./PaidStamp";

/** Whether the organizer has said this registration is settled, and the control
 *  that says it.
 *
 *  The only place in Squire where a person asserts that money arrived. Every
 *  other route to the paid state stands on a credited bank transaction, which
 *  is right where Squire collects and useless where it does not (spec
 *  payments, "An organizer may mark a registration settled by hand").
 *
 *  A row with no registration behind it — an imported row not yet issued —
 *  cannot be settled, and offers nothing rather than an action that would
 *  answer a refusal. Asked of `registration_id` and never of the variable
 *  symbol: a registration on a tournament the organizer keeps has no variable
 *  symbol to carry — Squire never told anyone one — so reading its absence as
 *  "no registration" would take the mark away from exactly the tournaments it
 *  was built for. */
export default function SettledCell({
  row,
  onToggle,
  busy,
}: {
  row: SheetRow;
  onToggle: (row: SheetRow) => void;
  busy: boolean;
}) {
  const { t } = useTranslation();
  if (typeof row.registration_id !== "number") return <>—</>;
  return (
    <button
      type="button"
      className="settled-cell"
      disabled={busy}
      aria-pressed={row.paid}
      title={t(row.paid ? "console.settled.unset" : "console.settled.set")}
      onClick={() => onToggle(row)}
    >
      {row.paid ? (
        <PaidStamp id={row.id} label={t("registration.state.paid")} />
      ) : (
        <span className="settled-unset">{t("console.settled.no")}</span>
      )}
    </button>
  );
}
