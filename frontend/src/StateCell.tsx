import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { SheetRow } from "./api";
import { StateBadge } from "./Console";
import WaiverReasonDialog from "./WaiverReasonDialog";

/** The registration's state on the Payments phase of a tournament Squire
 *  collects for, and — on the one state where it means anything — the waiver.
 *
 *  The waiver has no column of its own here. It changes exactly this cell,
 *  from reserved to paid with no money behind it, and a column that would be
 *  empty on almost every row does not earn its width in a table already
 *  carrying seven. So the control is the state it sets.
 *
 *  Offered only on a **reserved** row, and only to unset on a row a person
 *  waived. A registration the money settled is not this cell's to touch:
 *  unsetting a mark nobody made would return it to reserved and strand its
 *  credit, and the endpoint refuses it. An expired or cancelled row is a state
 *  the lifecycle or the fencer chose, and this marks money, not membership.
 */
export default function StateCell({
  row,
  onToggle,
  busy,
}: {
  row: SheetRow;
  /** Rejects when the mark is refused, so the dialog can stay open and say so
   *  rather than closing on a row that did not change. */
  onToggle: (row: SheetRow, reason?: string | null) => Promise<void>;
  busy: boolean;
}) {
  const { t } = useTranslation();
  const [asking, setAsking] = useState(false);

  const waived = row.settled_by_hand === true;
  const offered = typeof row.registration_id === "number" && (waived || row.state === "reserved");

  if (!offered) return <StateBadge id={row.id} state={row.state} />;

  return (
    <>
      <button
        type="button"
        className="state-cell"
        disabled={busy}
        aria-pressed={waived}
        title={
          waived
            ? (row.settled_by_hand_reason ?? t("console.settled.unset"))
            : t("console.waiver.title")
        }
        onClick={() => {
          // a reason is asked for only when the waiver is being set; asking
          // why someone is being un-waived would be a question about nothing
          if (waived) void onToggle(row);
          else setAsking(true);
        }}
      >
        <StateBadge id={row.id} state={row.state} />
      </button>
      {asking && (
        <WaiverReasonDialog
          name={row.name}
          // closed only once the mark is written: a refusal keeps the dialog
          // open with the reason intact and states itself there
          onConfirm={async (reason) => {
            await onToggle(row, reason);
            setAsking(false);
          }}
          onClose={() => setAsking(false)}
        />
      )}
    </>
  );
}
