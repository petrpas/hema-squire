import { useTranslation } from "react-i18next";

import type { SheetRow } from "./api";
import PaidStamp from "./PaidStamp";

/** Whether the organizer has said this registration is settled, and the control
 *  that says it — the boned-out Payments phase's whole content.
 *
 *  Only ever drawn where Squire handles no payments. There the mark is the one
 *  route to the paid state, so a paid row *is* a marked row — which is also how
 *  registrations marked before the mark was stored keep reading correctly — and
 *  no reason is asked for: where no ledger exists, every row is a hand-settled
 *  row and the phrase would be ceremony (spec payments).
 *
 *  Where Squire does collect, the same mark is a waiver and has no column of
 *  its own: it is offered on the state cell it changes (`StateCell`), because a
 *  column empty on almost every row would not earn its width in a table that is
 *  already wide.
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
  onToggle: (row: SheetRow, reason?: string | null) => Promise<void>;
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
      onClick={() => void onToggle(row)}
    >
      {row.paid ? (
        <PaidStamp id={row.id} label={t("registration.state.paid")} />
      ) : (
        <span className="settled-unset">{t("console.settled.no")}</span>
      )}
    </button>
  );
}
