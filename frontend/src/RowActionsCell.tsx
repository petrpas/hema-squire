import {
  IconArrowBackUp,
  IconCoins,
  IconMailForward,
  IconTrash,
  IconUserShare,
  IconUserX,
} from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import type { SheetRow } from "./api";
import { canSubstitute, type Phase, rowAction } from "./Console";

/** The end-of-row cell of the fencer table: whatever the phase offers to do to
 *  a row. Lifted out of `SheetArea` when the Payments phase's unfolding order
 *  lines took that file past the size it should be (design
 *  payments-roster-by-order D6); every decision is still the caller's. */
export default function RowActionsCell({
  row,
  phase,
  className,
  onRecordPayment,
  onSubstitute,
  onResendLink,
  onCancel,
  onRestore,
  onDelete,
}: {
  row: SheetRow;
  phase: Phase;
  className: string;
  onRecordPayment?: (row: SheetRow) => void;
  onSubstitute?: (row: SheetRow) => void;
  onResendLink?: (row: SheetRow) => void;
  onCancel: (row: SheetRow) => void;
  onRestore: (row: SheetRow) => void;
  onDelete: (row: SheetRow) => void;
}) {
  const { t } = useTranslation();
  return (
    <td className={className}>
      {/* Side by side and on one line: two actions at the end
      of a row are two decisions offered together, and
      stacked they read as one above the other. */}
      <div className="row-actions">
        {/* money that arrived where the feed does not reach.
      Sits with the row actions rather than in a column,
      because it is an action and not a value */}
        {onRecordPayment && typeof row.registration_id === "number" && (
          <button
            type="button"
            className="row-action"
            title={t("payments.record.action")}
            onClick={() => onRecordPayment(row)}
          >
            <IconCoins size={16} stroke={1.5} />
            <span className="visually-hidden">{t("payments.record.action")}</span>
          </button>
        )}
        {/* a seat handed on, beside the seat given up: two
      different decisions, both of them the roster's */}
        {onSubstitute && canSubstitute(row, phase) && (
          <button
            type="button"
            className="row-action"
            title={t("actions.substitute")}
            onClick={() => onSubstitute(row)}
          >
            <IconUserShare size={16} stroke={1.5} />
            <span className="visually-hidden">{t("actions.substitute")}</span>
          </button>
        )}
        {onResendLink && row.guest === true && (
          <button
            type="button"
            className="row-action"
            title={t("actions.resendLink")}
            onClick={() => onResendLink(row)}
          >
            <IconMailForward size={16} stroke={1.5} />
            <span className="visually-hidden">{t("actions.resendLink")}</span>
          </button>
        )}
        {rowAction(row, phase) === null ? null : rowAction(row, phase) === "cancel" ? (
          // a person holding a seat: cancelled, not tidied
          // away (spec etl-console, Reversible row deletion)
          <button
            type="button"
            className="row-action"
            title={t("actions.cancelRegistration")}
            onClick={() => onCancel(row)}
          >
            <IconUserX size={16} stroke={1.5} />
            <span className="visually-hidden">{t("actions.cancelRegistration")}</span>
          </button>
        ) : rowAction(row, phase) === "restore" ? (
          <button
            type="button"
            className="row-action"
            title={t("actions.restore")}
            onClick={() => onRestore(row)}
          >
            <IconArrowBackUp size={16} stroke={1.5} />
          </button>
        ) : (
          <button
            type="button"
            className="row-action"
            title={t("actions.delete")}
            onClick={() => onDelete(row)}
          >
            <IconTrash size={16} stroke={1.5} />
          </button>
        )}
      </div>
    </td>
  );
}
